#!/usr/bin/env python3
"""severity_router.py — Mechanical severity assignment from Impact × Likelihood.

Implements the matrix from rules/report-template.md and the downgrade modifiers
from rules/realism-filter.md. Reads a findings_table.schema.json v1.0 document
(typically the dedup output) and:

  1. For each finding without an explicit `severity`, derive one from
     (impact_level, likelihood) using the matrix.
  2. Apply downgrade modifiers (on-chain-only, view-only, trusted-actor,
     unreachable-precondition) per realism-filter rules.
  3. Preserve `severity_pre_modifier` when a downgrade is applied so the
     report can show the original tier and the adjustment reason.
  4. Cap PROVEN_ONLY mode: when --proven-only, any finding whose evidence_tags
     contains only [CODE-TRACE] (no POC-PASS / MEDUSA-PASS / PROD-*) is
     capped at Low and tagged in `extra` with the original severity.

The matrix (Impact rows, Likelihood columns):

    Impact    | High      | Medium    | Low
    ----------|-----------|-----------|----------
    High      | Critical  | High      | Medium
    Medium    | High      | Medium    | Medium
    Low       | Medium    | Low       | Low
    Info      | Info      | Info      | Info

Downgrades (applied after matrix lookup, in this order):
    -1 tier if realism_filter == "admin-trust" (fully-trusted actor must
        violate trust assumption) — floor: Informational
    -1 tier if impact_scope tags include "ON_CHAIN_ONLY" AND no off-chain
        consequence noted
    cap at Medium if "VIEW_ONLY"
    cap at Informational if "DESIGN_CHOICE" or "UNREACHABLE_PRECONDITION"

Usage:
    ./severity_router.py merged.json -o routed.json
    ./severity_router.py merged.json --proven-only -o routed.json
    ./severity_router.py merged.json --report     # human-readable diff
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SEVERITIES = ["Informational", "Low", "Medium", "High", "Critical"]

# Matrix[impact][likelihood] → severity
MATRIX: dict[str, dict[str, str]] = {
    "High": {"High": "Critical", "Medium": "High", "Low": "Medium"},
    "Medium": {"High": "High", "Medium": "Medium", "Low": "Medium"},
    "Low": {"High": "Medium", "Medium": "Low", "Low": "Low"},
    "Informational": {"High": "Informational", "Medium": "Informational", "Low": "Informational"},
}

# Tags in evidence_tags that prove on-chain execution (not just compile-time)
PROOF_TAGS = {"POC-PASS", "MEDUSA-PASS", "PROD-ONCHAIN", "PROD-SOURCE", "PROD-FORK",
              "DIFF-PASS", "CONFORMANCE-PASS", "NON-DET-PASS", "FUZZ-PASS"}


def sev_index(s: str | None) -> int:
    if s is None:
        return -1
    return SEVERITIES.index(s) if s in SEVERITIES else -1


def downgrade(s: str, steps: int = 1, floor: str = "Informational") -> str:
    i = sev_index(s)
    if i < 0:
        return s
    fi = SEVERITIES.index(floor)
    return SEVERITIES[max(fi, i - steps)]


def cap(s: str, max_tier: str) -> str:
    i = sev_index(s)
    mi = SEVERITIES.index(max_tier)
    if i < 0:
        return s
    return SEVERITIES[min(i, mi)]


def derive_severity(finding: dict, proven_only: bool = False) -> tuple[str | None, str | None, list[str]]:
    """Return (final_severity, severity_pre_modifier, applied_modifiers).

    severity_pre_modifier is set only when at least one downgrade was applied.
    Returns (None, None, []) if neither severity nor impact+likelihood are present.
    """
    applied: list[str] = []
    explicit = finding.get("severity")
    impact = finding.get("impact_level")
    likelihood = finding.get("likelihood")

    # Step 1: derive base severity
    if explicit:
        base = explicit
    elif impact and likelihood:
        base = MATRIX.get(impact, {}).get(likelihood)
        if not base:
            return (None, None, [])
        applied.append(f"matrix({impact}/{likelihood})→{base}")
    else:
        return (None, None, [])

    severity = base
    pre = None

    # Step 2: realism filter downgrades
    realism = finding.get("realism_filter")
    if realism == "admin-trust":
        new = downgrade(severity, 1, floor="Informational")
        if new != severity:
            pre = pre or severity
            applied.append(f"-1 tier: admin-trust (was {severity})")
            severity = new
    elif realism == "design-choice":
        new = cap(severity, "Informational")
        if new != severity:
            pre = pre or severity
            applied.append(f"cap@Info: design-choice (was {severity})")
            severity = new
    elif realism == "unreachable-precondition":
        new = cap(severity, "Informational")
        if new != severity:
            pre = pre or severity
            applied.append(f"cap@Info: unreachable-precondition (was {severity})")
            severity = new

    # Step 3: scope-based modifiers
    extra = finding.get("extra") or {}
    flags = {k.upper(): v for k, v in extra.items()}
    if flags.get("VIEW_ONLY") in (True, "true", "True", 1, "1"):
        new = cap(severity, "Medium")
        if new != severity:
            pre = pre or severity
            applied.append(f"cap@Medium: view-only (was {severity})")
            severity = new
    if flags.get("ON_CHAIN_ONLY") in (True, "true", "True", 1, "1") and not flags.get("OFF_CHAIN_IMPACT"):
        new = downgrade(severity, 1, floor="Informational")
        if new != severity:
            pre = pre or severity
            applied.append(f"-1 tier: on-chain-only (was {severity})")
            severity = new

    # Step 4: proven-only mode cap
    if proven_only:
        tags = set(finding.get("evidence_tags") or [])
        has_proof = bool(tags & PROOF_TAGS)
        if not has_proof:
            new = cap(severity, "Low")
            if new != severity:
                pre = pre or severity
                applied.append(f"cap@Low: proven-only (no proof tag, was {severity})")
                severity = new

    return (severity, pre, applied)


def route(data: dict, proven_only: bool = False) -> tuple[dict, list[dict]]:
    """Walk data['findings'], assign severities, return (data, diff_records)."""
    diff: list[dict] = []
    for f in data.get("findings") or []:
        if f.get("canonical_id"):
            # duplicates inherit; severity-router runs on canonicals only.
            continue
        old_sev = f.get("severity")
        old_pre = f.get("severity_pre_modifier")
        sev, pre, applied = derive_severity(f, proven_only=proven_only)
        if sev is None:
            continue
        if sev != old_sev or pre != old_pre:
            diff.append({
                "id": f["id"],
                "old_severity": old_sev,
                "new_severity": sev,
                "pre_modifier": pre,
                "applied": applied,
            })
        f["severity"] = sev
        f["severity_pre_modifier"] = pre

    # propagate canonical severity to duplicates
    canon_map = {f["id"]: f for f in (data.get("findings") or []) if not f.get("canonical_id")}
    for f in data.get("findings") or []:
        cid = f.get("canonical_id")
        if cid and cid in canon_map:
            f["severity"] = canon_map[cid].get("severity")
            f["severity_pre_modifier"] = canon_map[cid].get("severity_pre_modifier")
    return data, diff


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Assign severities via Impact×Likelihood matrix + realism downgrades."
    )
    ap.add_argument("input", help="findings_table JSON (typically dedup output).")
    ap.add_argument("-o", "--out", default="-", help="Output JSON (- for stdout).")
    ap.add_argument("--proven-only", action="store_true",
                    help="Cap findings with no proof tag at Low. Implements PROVEN_ONLY mode.")
    ap.add_argument("--diff-out", default=None, help="Write a per-finding diff log to this path.")
    ap.add_argument("--report", action="store_true", help="Print human-readable change report to stderr.")
    args = ap.parse_args(argv)

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    routed, diff = route(data, proven_only=args.proven_only)

    out_text = json.dumps(routed, indent=2, ensure_ascii=False)
    if args.out == "-":
        sys.stdout.write(out_text + "\n")
    else:
        Path(args.out).write_text(out_text, encoding="utf-8")
    if args.diff_out:
        Path(args.diff_out).write_text(json.dumps({"diff": diff}, indent=2), encoding="utf-8")

    print(f"[severity_router] routed {len(diff)} findings (proven_only={args.proven_only})", file=sys.stderr)
    if args.report:
        for d in diff:
            steps = ", ".join(d["applied"])
            old = d["old_severity"] or "—"
            print(f"  {d['id']:12s} {old:14s} → {d['new_severity']:14s}  [{steps}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
