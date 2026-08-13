#!/usr/bin/env python3
"""parse_findings.py — Parse agent prose output into findings_table.schema.json rows.

Reads one or more agent scratchpad files (analysis_*.md, depth_*_findings.md, etc.),
extracts FINDING / LEAD blocks in the pipe-delimited format from
agents/hacking-agents/shared-rules.md, and emits a JSON document conforming to
findings_table.schema.json v1.0.

The grammar tolerated is intentionally loose:

    FINDING | contract: Name | function: func | bug_class: kebab-tag | group_key: A|B|c
    path: caller -> ... -> impact
    proof: <free text, may span lines>
    verified: |
      L120:   if (foo) revert();
      L121:   ...
    description: one sentence (may span lines)
    fix: one-sentence suggestion
    severity: High           # optional, may be absent
    impact: Medium           # optional axis input
    likelihood: High         # optional axis input
    realism_filter: permissionless  # optional
    evidence: [CODE, POC-PASS]      # optional, comma list, brackets optional
    location: path/to/File.sol:L120-L145  # optional explicit, overrides parsed
    extra: any key: value pair preserved into metadata

Lines starting with `LEAD |` use the same field syntax. Blocks are separated by a
blank line followed by another `FINDING |` / `LEAD |` header or by EOF.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ── header regex ─────────────────────────────────────────────────────────────
HEADER_RE = re.compile(
    r"^\s*(?P<kind>FINDING|LEAD)\s*\|\s*(?P<rest>.+?)\s*$",
    re.IGNORECASE,
)

# group_key is special: it contains pipes inside its own value
# After splitting the header on `|`, fields with names "group_key" absorb the
# remainder. We parse the header in two passes.

LOC_RE = re.compile(
    r"(?P<file>[A-Za-z0-9_./\-]+\.(?:sol|vy|huff|rs|move|cpp|cc|hpp|h|go|py|ts|tsx|js))"
    r"(?::L?(?P<start>\d+)(?:[-–]L?(?P<end>\d+))?)?"
)
VERIFIED_LINE_RE = re.compile(r"^\s*L(?P<ln>\d+)\s*:\s*(?P<src>.*)$")
EVIDENCE_TAG_RE = re.compile(r"\[?\b([A-Z][A-Z0-9_-]{1,30})\b\]?")
KNOWN_EVIDENCE_TAGS = {
    "POC-PASS", "POC-FAIL", "CODE-TRACE", "MEDUSA-PASS",
    "PROD-ONCHAIN", "PROD-SOURCE", "PROD-FORK",
    "CODE", "DOC", "MOCK", "EXT-UNV",
    "BOUNDARY", "VARIATION", "TRACE",
    "DIFF-PASS", "CONFORMANCE-PASS", "NON-DET-PASS", "FUZZ-PASS",
}

SEVERITY_NORMALIZE = {
    "critical": "Critical", "crit": "Critical", "c": "Critical",
    "high": "High", "h": "High",
    "medium": "Medium", "med": "Medium", "m": "Medium",
    "low": "Low", "l": "Low",
    "info": "Informational", "informational": "Informational", "i": "Informational",
}
IMPACT_NORMALIZE = {
    "high": "High", "medium": "Medium", "med": "Medium",
    "low": "Low", "info": "Informational", "informational": "Informational",
}
LIKELIHOOD_NORMALIZE = {
    "high": "High", "medium": "Medium", "med": "Medium", "low": "Low",
}
REALISM_NORMALIZE = {
    "permissionless": "permissionless",
    "semi-trusted-role": "semi-trusted-role", "semi_trusted_role": "semi-trusted-role",
    "admin-trust": "admin-trust", "admin_trust": "admin-trust",
    "design-choice": "design-choice", "design_choice": "design-choice",
    "unreachable-precondition": "unreachable-precondition",
    "unreachable_precondition": "unreachable-precondition",
    "uneconomic-grief": "uneconomic-grief", "uneconomic_grief": "uneconomic-grief",
    "uneconomic grief": "uneconomic-grief",
}


# ── data class ───────────────────────────────────────────────────────────────
@dataclass
class Finding:
    kind: str
    contract: str = ""
    function: str = ""
    bug_class: str = ""
    group_key: str = ""
    severity: str | None = None
    severity_pre_modifier: str | None = None
    impact_level: str | None = None
    likelihood: str | None = None
    realism_filter: str | None = None
    title: str = ""
    description: str = ""
    path: str | None = None
    proof: str | None = None
    verified: str | None = None
    fix: str | None = None
    evidence_tags: list[str] = field(default_factory=list)
    location_file: str | None = None
    location_line_start: int | None = None
    location_line_end: int | None = None
    extra: dict[str, str] = field(default_factory=dict)
    tool_budget_exhausted: bool | None = None
    source_path: str = ""
    source_line: int = 0
    agent: str = ""
    report_id_explicit: str | None = None  # from `## Finding [X-NN]` headers
    verdict_explicit: str | None = None  # from `[VERIFIED]` / `[UNVERIFIED]` tags

    def as_schema_row(self, finding_id: str) -> dict:
        report_id = None
        if self.report_id_explicit:
            # honor only well-formed C/H/M/L/I-NN; otherwise stash in extra
            if re.match(r"^[CHMLI]-\d{2}$", self.report_id_explicit):
                report_id = self.report_id_explicit
            else:
                self.extra.setdefault("report_id_raw", self.report_id_explicit)
        verdict = None
        if self.verdict_explicit:
            vmap = {
                "VERIFIED": "CONFIRMED",
                "CONFIRMED": "CONFIRMED",
                "UNVERIFIED": "PARTIAL",
                "PARTIAL": "PARTIAL",
                "REFUTED": "REFUTED",
                "CONTESTED": "CONTESTED",
                "FALSE_POSITIVE": "FALSE_POSITIVE",
            }
            verdict = vmap.get(self.verdict_explicit.upper())
        row = {
            "id": finding_id,
            "canonical_id": None,
            "report_id": report_id,
            "kind": self.kind.upper(),
            "agent": self.agent,
            "contract": self.contract,
            "function": self.function,
            "bug_class": self.bug_class,
            "group_key": self.group_key or f"{self.contract} | {self.function} | {self.bug_class}",
            "severity": self.severity,
            "severity_pre_modifier": self.severity_pre_modifier,
            "impact_level": self.impact_level,
            "likelihood": self.likelihood,
            "realism_filter": self.realism_filter,
            "location": {
                "file": self.location_file or "",
                "line_start": self.location_line_start,
                "line_end": self.location_line_end,
            },
            "title": self.title or _derive_title(self.description),
            "description": self.description,
            "path": self.path,
            "proof": self.proof,
            "verified": self.verified,
            "fix": self.fix,
            "evidence_tags": self.evidence_tags,
            "verdict": verdict,
            "verifier_notes": None,
            "confidence": {
                "evidence": None,
                "consensus": None,
                "analysis_quality": None,
                "rag_match": None,
                "composite": None,
            },
            "rules_applied": [],
            "preconditions": [],
            "postconditions": [],
            "chain_id": None,
            "platform_status": {},
            "agent_source_paths": [self.source_path] if self.source_path else [],
            "tool_budget_exhausted": self.tool_budget_exhausted,
            "duplicate_of_v12": None,
        }
        return row


# ── helpers ──────────────────────────────────────────────────────────────────
def _derive_title(desc: str) -> str:
    if not desc:
        return ""
    first = desc.strip().split("\n", 1)[0].strip()
    return first[:80].rstrip(".") if first else ""


def _split_header_fields(rest: str) -> list[tuple[str, str]]:
    """Split the header after `FINDING |` into [(key, value)] tuples.

    The header uses ` | ` separators except inside the `group_key` value, which
    embeds pipes by convention (Contract | function | bug-class). We treat the
    last `key: ` we see whose key is `group_key` as absorbing the rest of the
    line.
    """
    out: list[tuple[str, str]] = []
    parts = [p.strip() for p in rest.split("|")]
    # walk, joining group_key with subsequent parts
    i = 0
    while i < len(parts):
        p = parts[i]
        if ":" not in p:
            i += 1
            continue
        key, val = p.split(":", 1)
        key = key.strip().lower()
        val = val.strip()
        if key == "group_key":
            # absorb the remaining parts joined back with pipes
            remainder = parts[i + 1:]
            if remainder:
                val = " | ".join([val] + remainder)
            out.append((key, val))
            break
        out.append((key, val))
        i += 1
    return out


def _normalize_severity(raw: str) -> str | None:
    return SEVERITY_NORMALIZE.get(raw.strip().lower())


def _normalize_impact(raw: str) -> str | None:
    return IMPACT_NORMALIZE.get(raw.strip().lower())


def _normalize_likelihood(raw: str) -> str | None:
    return LIKELIHOOD_NORMALIZE.get(raw.strip().lower())


def _normalize_realism(raw: str) -> str | None:
    return REALISM_NORMALIZE.get(raw.strip().lower().replace(" ", "-"))


def _parse_evidence_tags(raw: str) -> list[str]:
    tags = []
    for m in EVIDENCE_TAG_RE.finditer(raw):
        tag = m.group(1)
        # exact-match against known tags (case-sensitive after upper)
        if tag in KNOWN_EVIDENCE_TAGS:
            if tag not in tags:
                tags.append(tag)
    return tags


def _parse_location(raw: str, finding: Finding) -> None:
    m = LOC_RE.search(raw)
    if not m:
        return
    finding.location_file = m.group("file")
    if m.group("start"):
        finding.location_line_start = int(m.group("start"))
    if m.group("end"):
        finding.location_line_end = int(m.group("end"))


# ── markdown finding parser (## Finding [PREFIX-N]: Title) ────────────────────
MD_HEADER_RE = re.compile(
    r"^##\s+Finding\s+\[(?P<pid>[A-Z0-9_-]+)\]\s*:\s*(?P<title>.+?)\s*(?:\[(?P<verdict>[A-Z_]+)\])?\s*$",
    re.IGNORECASE,
)
MD_FIELD_RE = re.compile(r"^\*\*(?P<key>[A-Za-z][A-Za-z0-9 _-]*)\*\*\s*:\s*(?P<val>.*?)\s*$")


def parse_markdown_blocks(text: str, source_path: str, agent: str) -> list[Finding]:
    """Parse the rules/finding-output-format.md style: `## Finding [X-N]: Title` blocks.

    Used after dedup/severity routing when findings carry the formal report-tier
    layout. Different from the breadth-agent `FINDING |` pipe format.
    """
    findings: list[Finding] = []
    lines = text.splitlines()
    n = len(lines)
    i = 0
    while i < n:
        m = MD_HEADER_RE.match(lines[i])
        if not m:
            i += 1
            continue
        header_line = i
        finding = Finding(
            kind="FINDING",
            source_path=source_path,
            source_line=header_line + 1,
            agent=agent,
            title=m.group("title").strip(),
            report_id_explicit=m.group("pid"),
            verdict_explicit=m.group("verdict"),
        )
        i += 1
        current_key: str | None = None
        buf: list[str] = []

        def _flush_md():
            nonlocal current_key, buf
            if current_key is None:
                buf = []
                return
            joined = "\n".join(buf).strip()
            kn = current_key.lower().replace(" ", "_")
            if kn == "severity":
                finding.severity = _normalize_severity(joined) or finding.severity
            elif kn == "location":
                _parse_location(joined, finding)
            elif kn == "evidence":
                finding.evidence_tags = _parse_evidence_tags(joined)
            elif kn == "description":
                finding.description = joined
            elif kn == "impact":
                # markdown "Impact:" is usually a sentence, not the matrix axis;
                # try to detect a 1-word axis value first
                axis = _normalize_impact(joined.split()[0]) if joined.split() else None
                if axis and len(joined.split()) <= 2:
                    finding.impact_level = axis
                else:
                    finding.extra["impact_text"] = joined
            elif kn == "likelihood":
                axis = _normalize_likelihood(joined.split()[0]) if joined.split() else None
                if axis:
                    finding.likelihood = axis
                else:
                    finding.extra["likelihood_text"] = joined
            elif kn == "recommendation":
                finding.fix = joined
            elif kn == "verified":
                finding.verified = joined
            elif kn == "attack_sequence":
                finding.path = joined
            elif kn == "poc_result":
                finding.extra["poc_result"] = joined
            elif kn == "verdict":
                finding.extra["verdict_tag"] = joined
            else:
                finding.extra[kn] = joined
            current_key = None
            buf = []

        while i < n:
            line = lines[i]
            # next finding header → stop
            if MD_HEADER_RE.match(line):
                break
            # section header at depth 1 (## ...) terminates this block
            if line.startswith("## ") and not MD_HEADER_RE.match(line):
                break
            fm = MD_FIELD_RE.match(line)
            if fm:
                _flush_md()
                current_key = fm.group("key")
                if fm.group("val"):
                    buf.append(fm.group("val"))
                i += 1
                # consume continuation lines (indented or non-field blank-then-text)
                while i < n:
                    nxt = lines[i]
                    if MD_HEADER_RE.match(nxt) or nxt.startswith("## "):
                        break
                    if MD_FIELD_RE.match(nxt):
                        break
                    if not nxt.strip() and buf and buf[-1].strip():
                        # one blank line is allowed inside a field
                        i += 1
                        continue
                    buf.append(nxt)
                    i += 1
                _flush_md()
                continue
            i += 1
        _flush_md()
        # title fallback from first sentence of description
        if not finding.title:
            finding.title = _derive_title(finding.description)
        findings.append(finding)
    return findings


# ── parser ───────────────────────────────────────────────────────────────────
def parse_blocks(text: str, source_path: str, agent: str) -> list[Finding]:
    """Walk the file, emitting one Finding per FINDING/LEAD block."""
    findings: list[Finding] = []
    lines = text.splitlines()
    n = len(lines)
    i = 0
    while i < n:
        m = HEADER_RE.match(lines[i])
        if not m:
            i += 1
            continue
        # found a header — start a block
        header_line = i
        kind = m.group("kind").upper()
        fields = _split_header_fields(m.group("rest"))
        finding = Finding(kind=kind, source_path=source_path, source_line=header_line + 1, agent=agent)
        for key, val in fields:
            if key == "contract":
                finding.contract = val
            elif key == "function":
                finding.function = val
            elif key == "bug_class":
                finding.bug_class = val
            elif key == "group_key":
                finding.group_key = val
            else:
                finding.extra[key] = val

        # consume body lines until next header or blank-then-non-body or EOF
        i += 1
        current_key: str | None = None
        buf: list[str] = []
        verified_buf: list[str] = []
        in_verified_block = False

        def _flush():
            nonlocal current_key, buf, verified_buf, in_verified_block
            if current_key is None:
                buf = []
                return
            joined = "\n".join(buf).strip()
            if current_key == "path":
                finding.path = joined or finding.path
            elif current_key == "proof":
                finding.proof = joined or finding.proof
            elif current_key == "verified":
                if verified_buf:
                    finding.verified = "\n".join(verified_buf).strip()
                else:
                    finding.verified = joined or finding.verified
            elif current_key == "description":
                finding.description = joined or finding.description
            elif current_key == "fix":
                finding.fix = joined or finding.fix
            elif current_key == "title":
                finding.title = joined or finding.title
            elif current_key == "severity":
                finding.severity = _normalize_severity(joined) or finding.severity
            elif current_key in ("impact", "impact_level"):
                finding.impact_level = _normalize_impact(joined) or finding.impact_level
            elif current_key == "likelihood":
                finding.likelihood = _normalize_likelihood(joined) or finding.likelihood
            elif current_key == "realism_filter":
                finding.realism_filter = _normalize_realism(joined) or finding.realism_filter
            elif current_key == "evidence" or current_key == "evidence_tags":
                finding.evidence_tags = _parse_evidence_tags(joined)
            elif current_key == "location":
                _parse_location(joined, finding)
            elif current_key == "tool_budget_exhausted":
                finding.tool_budget_exhausted = joined.strip().lower() in ("true", "yes", "1")
            else:
                finding.extra[current_key] = joined
            current_key = None
            buf = []
            verified_buf = []
            in_verified_block = False

        while i < n:
            line = lines[i]
            # stop on next header (FINDING|LEAD) at column 0/whitespace
            if HEADER_RE.match(line):
                break

            # parse `key: value` or `key: |` continuation lines
            key_match = re.match(r"^\s*([a-z_][a-z0-9_]*)\s*:\s*(.*?)\s*$", line)
            if key_match and not in_verified_block:
                kname = key_match.group(1).lower()
                kval = key_match.group(2)
                # detect heredoc-style `key: |`
                if kval == "|":
                    _flush()
                    current_key = kname
                    in_verified_block = (kname == "verified")
                    i += 1
                    # consume indented continuation
                    while i < n and (lines[i].startswith("  ") or lines[i].startswith("\t") or lines[i].strip() == ""):
                        if HEADER_RE.match(lines[i]):
                            break
                        if in_verified_block:
                            m_v = VERIFIED_LINE_RE.match(lines[i])
                            if m_v:
                                verified_buf.append(f"L{m_v.group('ln')}: {m_v.group('src')}")
                            elif lines[i].strip():
                                verified_buf.append(lines[i].strip())
                        else:
                            buf.append(lines[i])
                        i += 1
                    _flush()
                    continue
                else:
                    _flush()
                    current_key = kname
                    if kval:
                        buf.append(kval)
                    # peek to see if next line is a continuation
                    i += 1
                    while i < n and lines[i].startswith("  ") and not HEADER_RE.match(lines[i]):
                        # only treat as continuation if line doesn't look like a new key:
                        if re.match(r"^\s*[a-z_][a-z0-9_]*\s*:", lines[i]):
                            break
                        buf.append(lines[i].strip())
                        i += 1
                    _flush()
                    continue

            # blank line — terminates a value
            if not line.strip():
                _flush()
                i += 1
                continue
            # otherwise buffer
            if current_key is not None:
                buf.append(line)
            i += 1

        _flush()
        findings.append(finding)
    return findings


def infer_agent(filename: str) -> str:
    """Infer agent name from the scratchpad filename."""
    base = Path(filename).stem.lower()
    # common patterns: analysis_access_control, depth_state_trace_findings,
    # blind_spot_X, niche_event_completeness_findings, analysis_rescan_2,
    # analysis_percontract_3, depth_lowlevel_findings, validation_sweep_findings
    if base.startswith("analysis_rescan"):
        return "rescan"
    if base.startswith("analysis_percontract"):
        return "percontract"
    for prefix, agent in (
        ("analysis_access_control", "access-control"),
        ("analysis_economic_security", "economic-security"),
        ("analysis_execution_trace", "execution-trace"),
        ("analysis_periphery", "periphery"),
        ("analysis_math_precision", "math-precision"),
        ("analysis_invariant", "invariant"),
        ("analysis_vector_scan", "vector-scan"),
        ("analysis_first_principles", "first-principles"),
        ("analysis_feynman", "feynman"),
        ("analysis_state_inconsistency", "state-inconsistency"),
        ("depth_lowlevel", "depth-lowlevel"),
        ("depth_runtime", "depth-runtime"),
        ("depth_state_trace", "depth-state-trace"),
        ("depth_token_flow", "depth-token-flow"),
        ("depth_external", "depth-external"),
        ("depth_edge_case", "depth-edge-case"),
        ("depth_consensus_invariant", "depth-consensus-invariant"),
        ("depth_network_surface", "depth-network-surface"),
        ("validation_sweep", "validation-sweep"),
        ("blind_spot", "blind-spot"),
        ("design_stress", "design-stress"),
    ):
        if base.startswith(prefix):
            return agent
    if "niche" in base:
        # niche_event_completeness_findings → niche-event-completeness
        clean = base.replace("_findings", "").replace("niche_", "niche-").replace("_", "-")
        return clean
    return base.replace("_", "-")


def assign_ids(findings: list[Finding]) -> list[dict]:
    """Stable ID assignment per agent: AGENT-1, AGENT-2..."""
    counters: dict[str, int] = {}
    rows: list[dict] = []
    for f in findings:
        prefix = (f.agent or "agent").upper().replace("-", "")[:6]
        counters[prefix] = counters.get(prefix, 0) + 1
        fid = f"{prefix}-{counters[prefix]}"
        rows.append(f.as_schema_row(fid))
    return rows


def parse_files(paths: list[Path]) -> list[Finding]:
    out: list[Finding] = []
    for p in paths:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"[parse_findings] WARN: cannot read {p}: {e}", file=sys.stderr)
            continue
        agent = infer_agent(p.name)
        # parse both formats from the same file; they don't conflict because
        # the regexes target distinct headers (`FINDING|LEAD |` vs `## Finding [..]`)
        pipe = parse_blocks(text, str(p), agent)
        md = parse_markdown_blocks(text, str(p), agent)
        out.extend(pipe)
        out.extend(md)
    return out


def build_table(findings: list[Finding], audit_id: str, phase: str) -> dict:
    rows = assign_ids(findings)
    return {
        "version": "1.0",
        "audit_id": audit_id,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "phase": phase,
        "findings": rows,
    }


# ── CLI ──────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Parse agent FINDING/LEAD blocks into findings_table.schema.json v1.0."
    )
    ap.add_argument(
        "inputs",
        nargs="+",
        help="One or more scratchpad files (analysis_*.md, depth_*_findings.md, etc.) or directories.",
    )
    ap.add_argument(
        "--out", "-o",
        default="-",
        help="Output JSON file path. '-' for stdout (default).",
    )
    ap.add_argument(
        "--audit-id",
        default=os.environ.get("DEWAXGUARD_AUDIT_ID", "unknown-audit"),
        help="Audit identifier (defaults to $DEWAXGUARD_AUDIT_ID or 'unknown-audit').",
    )
    ap.add_argument(
        "--phase",
        default="breadth",
        choices=["breadth", "inventory", "depth", "chain", "verify", "report"],
        help="Phase tag for this table snapshot (default breadth).",
    )
    ap.add_argument(
        "--glob",
        default="*.md",
        help="When an input is a directory, this glob is applied (default *.md).",
    )
    args = ap.parse_args(argv)

    paths: list[Path] = []
    for inp in args.inputs:
        p = Path(inp)
        if p.is_dir():
            paths.extend(sorted(p.glob(args.glob)))
        elif p.exists():
            paths.append(p)
        else:
            print(f"[parse_findings] WARN: input not found: {inp}", file=sys.stderr)

    if not paths:
        print("[parse_findings] no inputs to parse", file=sys.stderr)
        return 2

    findings = parse_files(paths)
    table = build_table(findings, args.audit_id, args.phase)

    out_text = json.dumps(table, indent=2, ensure_ascii=False)
    if args.out == "-":
        sys.stdout.write(out_text + "\n")
    else:
        Path(args.out).write_text(out_text, encoding="utf-8")
        print(
            f"[parse_findings] wrote {len(findings)} findings to {args.out}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
