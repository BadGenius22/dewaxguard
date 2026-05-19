#!/usr/bin/env python3
"""dedup.py — Mechanical dedup of findings tables.

Reads one or more findings_table.schema.json v1.0 documents (produced by
parse_findings.py), groups findings that share the same root cause, and emits:

  1. A merged table where each canonical finding aggregates all duplicate
     rows under `agent_source_paths` and `extra_locations`. Duplicate rows
     keep a `canonical_id` pointer back to the survivor.
  2. A `clusters.json` audit trail with per-cluster reasoning (which rows
     joined, what score they had, why).
  3. An `ambiguous.json` file listing borderline clusters (score in the
     fuzzy band) that should be routed to an LLM tie-breaker.

Three-stage matching, fastest → slowest:

  Stage A — exact group_key:           same Contract|function|bug_class
  Stage B — same file + line ±5:       location proximity (same root cause site)
  Stage C — title/description similar: Jaro-Winkler on (title + bug_class)

Stage A is always-merge. Stage B is always-merge when bug_class also overlaps
(jaccard ≥ 0.6 on the kebab tokens). Stage C is merge when score ≥ 0.85, or
flag-as-ambiguous when 0.70 ≤ score < 0.85.

The "fuzzy band" (0.70–0.85) is the only place that escalates to an LLM
tie-breaker. In practice it covers ≤ 5% of clusters on real audits.

Usage:
  ./dedup.py findings.json [more.json...] -o merged.json
  ./dedup.py --report findings.json   # human-readable summary, no write
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# ── Jaro-Winkler (no external deps) ──────────────────────────────────────────
def jaro(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    la, lb = len(a), len(b)
    match_distance = max(la, lb) // 2 - 1
    if match_distance < 0:
        match_distance = 0
    a_matches = [False] * la
    b_matches = [False] * lb
    matches = 0
    for i in range(la):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, lb)
        for j in range(start, end):
            if b_matches[j]:
                continue
            if a[i] != b[j]:
                continue
            a_matches[i] = True
            b_matches[j] = True
            matches += 1
            break
    if matches == 0:
        return 0.0
    transpositions = 0
    k = 0
    for i in range(la):
        if not a_matches[i]:
            continue
        while not b_matches[k]:
            k += 1
        if a[i] != b[k]:
            transpositions += 1
        k += 1
    transpositions //= 2
    return (matches / la + matches / lb + (matches - transpositions) / matches) / 3.0


def jaro_winkler(a: str, b: str, p: float = 0.1) -> float:
    j = jaro(a, b)
    if j < 0.7:
        return j
    prefix = 0
    for x, y in zip(a, b):
        if x != y:
            break
        prefix += 1
        if prefix == 4:
            break
    return j + prefix * p * (1 - j)


# ── token helpers ────────────────────────────────────────────────────────────
TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(s: str) -> list[str]:
    return TOKEN_RE.findall(s.lower())


def jaccard(a: list[str] | set[str], b: list[str] | set[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def kebab_tokens(s: str) -> list[str]:
    return [t for t in s.lower().replace("_", "-").split("-") if t]


# ── clustering ───────────────────────────────────────────────────────────────
def normalize_path(p: str) -> str:
    """Strip leading ./, leading slashes, trailing slashes, normalize separators."""
    if not p:
        return ""
    p = p.replace("\\", "/")
    while p.startswith("./") or p.startswith("/"):
        p = p[2:] if p.startswith("./") else p[1:]
    return p.rstrip("/")


def location_overlap(a: dict, b: dict, line_tol: int = 5) -> bool:
    fa = normalize_path(a.get("file") or "")
    fb = normalize_path(b.get("file") or "")
    if not fa or not fb:
        return False
    if fa != fb and not (fa.endswith("/" + fb) or fb.endswith("/" + fa)):
        return False
    sa, sb = a.get("line_start"), b.get("line_start")
    ea, eb = a.get("line_end") or sa, b.get("line_end") or sb
    if sa is None or sb is None:
        return True  # same file, no line info — treat as overlap
    # extend each range by tolerance, check intersection
    return not (ea + line_tol < sb or eb + line_tol < sa)


def title_similarity(a: dict, b: dict) -> float:
    ta = (a.get("title") or a.get("description") or "")[:200].lower()
    tb = (b.get("title") or b.get("description") or "")[:200].lower()
    if not ta or not tb:
        return 0.0
    # combine token-jaccard and Jaro-Winkler on the joined title+bug_class
    sa = ta + " " + (a.get("bug_class") or "")
    sb = tb + " " + (b.get("bug_class") or "")
    jw = jaro_winkler(sa, sb)
    jc = jaccard(tokenize(sa), tokenize(sb))
    # weighted average — character-level (jw) and token-level (jc)
    return 0.6 * jw + 0.4 * jc


# ── stage scoring ────────────────────────────────────────────────────────────
MERGE_SCORE = 0.85
FUZZY_LOW = 0.70


def stage_score(a: dict, b: dict) -> tuple[float, str]:
    """Return (score, reason) for merging a and b.

    Score scale:
      ≥ MERGE_SCORE  → automatic merge
      ≥ FUZZY_LOW    → flag as ambiguous for LLM tie-break
      < FUZZY_LOW    → not the same finding (no flag)
    """
    # Stage A — exact group_key match
    if a.get("group_key") and a["group_key"] == b.get("group_key"):
        return (1.0, "group_key exact match")

    # Compute signal features once
    same_contract = bool(a.get("contract")) and a["contract"] == b.get("contract")
    same_function = bool(a.get("function")) and a["function"] == b.get("function")
    bc_overlap = jaccard(
        kebab_tokens(a.get("bug_class") or ""),
        kebab_tokens(b.get("bug_class") or ""),
    )
    title_sim = title_similarity(a, b)
    loc_overlap = location_overlap(a.get("location") or {}, b.get("location") or {})

    # Stage A2 — same contract + same function (strong but not exact)
    if same_contract and same_function:
        if bc_overlap >= 0.3:
            return (0.92, f"same contract+function + bug_class jaccard {bc_overlap:.2f}")
        if title_sim >= 0.55:
            return (0.88, f"same contract+function + title sim {title_sim:.2f}")
        # Ambiguous only when BOTH signals show partial alignment.
        # Pure same-function with no other overlap = likely distinct bugs; suppress.
        if bc_overlap >= 0.2 and title_sim >= 0.35:
            return (0.78, f"same contract+function + partial class+title (bc {bc_overlap:.2f}, title {title_sim:.2f})")
        if title_sim >= 0.45:
            return (0.74, f"same contract+function + moderate title sim {title_sim:.2f}")
        return (0.0, f"same contract+function but different bug topics (bc {bc_overlap:.2f}, title {title_sim:.2f})")

    # Stage B — same file + line proximity + bug_class overlap
    if loc_overlap:
        if bc_overlap >= 0.6:
            return (0.95, f"location overlap + bug_class jaccard {bc_overlap:.2f}")
        if bc_overlap >= 0.3:
            return (max(0.70, title_sim), f"location overlap, bug_class partial {bc_overlap:.2f}, title sim {title_sim:.2f}")

    # Stage C — title/description similarity only
    if title_sim >= 0.85:
        return (title_sim, f"title similarity {title_sim:.2f}")
    if title_sim >= FUZZY_LOW:
        return (title_sim, f"title similarity {title_sim:.2f}")
    return (0.0, f"below threshold (title {title_sim:.2f}, bc {bc_overlap:.2f})")


def cluster(findings: list[dict]) -> tuple[list[list[int]], list[dict]]:
    """Union-find clustering.

    Returns:
        clusters: list of [index, ...]
        decisions: list of {a, b, score, reason, action} for audit trail
    """
    n = len(findings)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    decisions: list[dict] = []
    evaluated: set[tuple[int, int]] = set()

    def evaluate(a: int, b: int, stage: str) -> None:
        if a == b:
            return
        pair = (min(a, b), max(a, b))
        if pair in evaluated:
            return
        if find(a) == find(b):
            evaluated.add(pair)
            return
        score, reason = stage_score(findings[a], findings[b])
        if score >= MERGE_SCORE:
            union(a, b)
            decisions.append({
                "a": findings[a]["id"],
                "b": findings[b]["id"],
                "score": score,
                "reason": f"[{stage}] {reason}",
                "action": "MERGE",
            })
        elif score >= FUZZY_LOW:
            decisions.append({
                "a": findings[a]["id"],
                "b": findings[b]["id"],
                "score": score,
                "reason": f"[{stage}] {reason}",
                "action": "AMBIGUOUS",
            })
        evaluated.add(pair)

    # Indexes for each stage
    gk_index: dict[str, list[int]] = defaultdict(list)
    cf_index: dict[tuple[str, str], list[int]] = defaultdict(list)
    file_index: dict[str, list[int]] = defaultdict(list)
    by_bug_token: dict[str, list[int]] = defaultdict(list)
    for i, f in enumerate(findings):
        if f.get("group_key"):
            gk_index[f["group_key"]].append(i)
        if f.get("contract") and f.get("function"):
            cf_index[(f["contract"], f["function"])].append(i)
        fp = normalize_path((f.get("location") or {}).get("file") or "")
        if fp:
            file_index[fp].append(i)
        for tok in kebab_tokens(f.get("bug_class") or ""):
            by_bug_token[tok].append(i)

    # Stage A — exact group_key (always merge, no evaluation needed)
    for gk, idxs in gk_index.items():
        if len(idxs) < 2:
            continue
        for j in idxs[1:]:
            if find(idxs[0]) != find(j):
                union(idxs[0], j)
                decisions.append({
                    "a": findings[idxs[0]]["id"],
                    "b": findings[j]["id"],
                    "score": 1.0,
                    "reason": f"[A] group_key exact match: {gk}",
                    "action": "MERGE",
                })
            evaluated.add((min(idxs[0], j), max(idxs[0], j)))

    # Stage A2 — same contract + same function
    for idxs in cf_index.values():
        if len(idxs) < 2:
            continue
        for i in range(len(idxs)):
            for j in range(i + 1, len(idxs)):
                evaluate(idxs[i], idxs[j], "A2")

    # Stage B — same file + proximity
    for idxs in file_index.values():
        if len(idxs) < 2:
            continue
        for i in range(len(idxs)):
            for j in range(i + 1, len(idxs)):
                evaluate(idxs[i], idxs[j], "B")

    # Stage C — pre-filter by bug_class token overlap (skips full pairwise)
    for idxs in by_bug_token.values():
        if len(idxs) < 2:
            continue
        for i in range(len(idxs)):
            for j in range(i + 1, len(idxs)):
                evaluate(idxs[i], idxs[j], "C")

    # collect clusters
    clusters_map: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        clusters_map[find(i)].append(i)
    clusters = list(clusters_map.values())
    return clusters, decisions


# ── merge logic ──────────────────────────────────────────────────────────────
SEVERITY_RANK = {"Critical": 5, "High": 4, "Medium": 3, "Low": 2, "Informational": 1, None: 0}


def pick_canonical(cluster_findings: list[dict]) -> dict:
    """Pick the row with: highest severity → FINDING over LEAD → most evidence tags → first seen."""
    def key(f: dict) -> tuple[int, int, int]:
        sev = SEVERITY_RANK.get(f.get("severity"), 0)
        kind = 1 if f.get("kind") == "FINDING" else 0
        evidence = len(f.get("evidence_tags") or [])
        return (sev, kind, evidence)
    return max(cluster_findings, key=key)


def merge_cluster(cluster_findings: list[dict]) -> tuple[dict, list[dict]]:
    """Return (canonical, [duplicate rows with canonical_id set])."""
    canonical = pick_canonical(cluster_findings)
    canonical_copy = json.loads(json.dumps(canonical))  # deep copy
    duplicates: list[dict] = []
    extra_locations: list[dict] = list(
        canonical_copy.get("location", {}).get("extra_locations") or []
    )
    agent_paths: list[str] = list(canonical_copy.get("agent_source_paths") or [])
    evidence: list[str] = list(canonical_copy.get("evidence_tags") or [])
    realisms: list[str] = []
    if canonical_copy.get("realism_filter"):
        realisms.append(canonical_copy["realism_filter"])

    for f in cluster_findings:
        if f is canonical:
            continue
        dup = json.loads(json.dumps(f))
        dup["canonical_id"] = canonical_copy["id"]
        duplicates.append(dup)

        # absorb extra location
        loc = f.get("location") or {}
        if loc.get("file") and (
            loc.get("file") != canonical_copy.get("location", {}).get("file")
            or loc.get("line_start") != canonical_copy.get("location", {}).get("line_start")
        ):
            extra_locations.append({
                "file": loc.get("file"),
                "line_start": loc.get("line_start"),
                "line_end": loc.get("line_end"),
                "note": f"from {f['id']} ({f.get('agent', '?')})",
            })
        # absorb agent paths
        for p in f.get("agent_source_paths") or []:
            if p not in agent_paths:
                agent_paths.append(p)
        # absorb evidence tags
        for t in f.get("evidence_tags") or []:
            if t not in evidence:
                evidence.append(t)
        # collect realism filters for tie-break
        if f.get("realism_filter"):
            realisms.append(f["realism_filter"])

    if extra_locations:
        canonical_copy.setdefault("location", {})["extra_locations"] = extra_locations
    canonical_copy["agent_source_paths"] = agent_paths
    canonical_copy["evidence_tags"] = evidence
    # realism: keep the most-restrictive non-permissionless tag if present
    realism_priority = {
        "permissionless": 5,
        "semi-trusted-role": 4,
        "admin-trust": 3,
        "design-choice": 2,
        "unreachable-precondition": 1,
    }
    if realisms:
        canonical_copy["realism_filter"] = max(
            realisms, key=lambda r: realism_priority.get(r, 0)
        )
    return canonical_copy, duplicates


# ── IO ───────────────────────────────────────────────────────────────────────
def load_tables(paths: list[Path]) -> tuple[list[dict], dict]:
    findings: list[dict] = []
    meta: dict[str, Any] = {}
    for p in paths:
        data = json.loads(p.read_text(encoding="utf-8"))
        if "findings" not in data:
            print(f"[dedup] WARN: {p} has no 'findings' key, skipping", file=sys.stderr)
            continue
        if not meta:
            meta = {k: v for k, v in data.items() if k != "findings"}
        findings.extend(data["findings"])
    return findings, meta


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Deterministic dedup of findings_table.schema.json v1.0 documents."
    )
    ap.add_argument("inputs", nargs="+", help="One or more findings JSON files (from parse_findings.py).")
    ap.add_argument("-o", "--out", default="-", help="Output merged JSON (- for stdout, default).")
    ap.add_argument("--clusters-out", default=None, help="Optional: write per-cluster audit trail JSON.")
    ap.add_argument("--ambiguous-out", default=None, help="Optional: write ambiguous-cluster JSON for LLM tie-break.")
    ap.add_argument("--report", action="store_true", help="Print human-readable summary to stderr.")
    args = ap.parse_args(argv)

    paths = [Path(p) for p in args.inputs]
    findings, meta = load_tables(paths)
    if not findings:
        print("[dedup] no findings to dedup", file=sys.stderr)
        return 2

    clusters, decisions = cluster(findings)
    merged_findings: list[dict] = []
    cluster_audit: list[dict] = []
    ambiguous_clusters: list[dict] = []
    for c in clusters:
        cluster_rows = [findings[i] for i in c]
        if len(cluster_rows) == 1:
            merged_findings.append(cluster_rows[0])
            cluster_audit.append({
                "size": 1,
                "canonical": cluster_rows[0]["id"],
                "members": [cluster_rows[0]["id"]],
            })
            continue
        canonical, dups = merge_cluster(cluster_rows)
        merged_findings.append(canonical)
        merged_findings.extend(dups)
        cluster_audit.append({
            "size": len(cluster_rows),
            "canonical": canonical["id"],
            "members": [r["id"] for r in cluster_rows],
        })

    # collect ambiguous edges
    for d in decisions:
        if d["action"] == "AMBIGUOUS":
            ambiguous_clusters.append(d)

    out = {
        **meta,
        "phase": meta.get("phase", "inventory"),
        "findings": merged_findings,
        "dedup_stats": {
            "input_count": len(findings),
            "output_count": len([f for f in merged_findings if not f.get("canonical_id")]),
            "duplicates_absorbed": len([f for f in merged_findings if f.get("canonical_id")]),
            "clusters": len(clusters),
            "ambiguous_pairs": len(ambiguous_clusters),
        },
    }

    out_text = json.dumps(out, indent=2, ensure_ascii=False)
    if args.out == "-":
        sys.stdout.write(out_text + "\n")
    else:
        Path(args.out).write_text(out_text, encoding="utf-8")

    if args.clusters_out:
        Path(args.clusters_out).write_text(json.dumps({"clusters": cluster_audit, "decisions": decisions}, indent=2), encoding="utf-8")
    if args.ambiguous_out:
        Path(args.ambiguous_out).write_text(json.dumps({"ambiguous": ambiguous_clusters}, indent=2), encoding="utf-8")

    stats = out["dedup_stats"]
    print(
        f"[dedup] input={stats['input_count']} → output={stats['output_count']} "
        f"(absorbed={stats['duplicates_absorbed']}, clusters={stats['clusters']}, "
        f"ambiguous={stats['ambiguous_pairs']})",
        file=sys.stderr,
    )
    if args.report:
        print("\n=== Cluster Report ===", file=sys.stderr)
        for c in cluster_audit:
            if c["size"] > 1:
                print(f"  [{c['size']}] canonical={c['canonical']} members={c['members']}", file=sys.stderr)
        if ambiguous_clusters:
            print(f"\n=== Ambiguous Pairs (need LLM tie-break) ===", file=sys.stderr)
            for d in ambiguous_clusters:
                print(f"  {d['a']} <-> {d['b']} score={d['score']:.2f}  {d['reason']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
