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
import re
import sys
from pathlib import Path

SEVERITIES = ["Informational", "Low", "Medium", "High", "Critical"]

# ── Grief / DoS economic gates (rules/severity-matrix.md) ────────────────────
# Origin: DRE Sherlock audit (2026-07). A real wrong-list DoS defect shipped as
# Medium and was rejected: the attacker's cost was unrecoverable dust while the
# victims only suffered delay the TREASURY could manually clear. dewaxguard
# already had the attacker-cost dimension in the L1 matrix, the Immunefi criteria
# and M-16 — but never in the smart-contract severity path. These three gates
# generalize it. All are MECHANICAL: they compare declared fields or detect the
# finding's own admission, never re-judge the vulnerability.

# The finding's own text conceding that a privileged-but-routine operation
# restores service ("the TREASURY can still recover funds", "manual fills").
RECOVERY_ADMISSION_RE = re.compile(
    r"\b(treasury|admin|owner|operator|governance|keeper|multisig)\b[^.\n]{0,90}?"
    r"\b(can|could|may|is able to)\b[^.\n]{0,90}?"
    r"\b(recover|restore|unblock|resolve|re-?fill|fill around|skip|work[- ]around|manually)\b"
    r"|\bmanual(?:ly)?\s+(?:treasury\s+)?(?:fill|fills|intervention|recovery|work[- ]around)"
    r"|\bcan still (?:recover|be recovered|operate|be filled)",
    re.IGNORECASE,
)

# Grief/DoS-shaped findings — the class where attacker cost must be weighed.
GRIEF_CLASS_RE = re.compile(
    r"\b(do[s5]|denial[- ]of[- ]service|grief(?:ing)?|liveness|block(?:s|ed|ing)?\s+"
    r"(?:the\s+)?(?:queue|batch|withdrawals?)|bricks?|stuck|permanently\s+block)\b",
    re.IGNORECASE,
)

TRUTHY = (True, "true", "True", "TRUE", "yes", "YES", 1, "1")
FALSEY = (False, "false", "False", "FALSE", "no", "NO", 0, "0")

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

# L1 evidence-floor rules (per rules/l1-severity-matrix.md).
# These tags imply a minimum severity floor regardless of Impact x Likelihood matrix.
L1_EVIDENCE_FLOORS = {
    "DIFF-PASS": "High",        # two implementations disagree on same input -> consensus risk
    "NON-DET-PASS": "High",     # same input -> different state across validators
    "FUZZ-PASS": "Medium",      # fuzz counterexample; impact then determines higher tier
    "CONFORMANCE-PASS": None,   # severity matches the violated invariant; no fixed floor
}


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


def _finding_text(finding: dict) -> str:
    """All prose the finding carries — used only for self-admission detection.

    Scans every string value rather than a fixed field list: the prose that
    concedes a recovery path lands in different fields depending on the emitting
    phase (`description`/`proof`/`path` from breadth, `impact`/`recommendation`
    from verify, free-form keys in `extra`). Axis fields like `impact: High` are
    harmless noise here — they never match the recovery pattern.
    """
    parts: list[str] = []

    def walk(v, depth: int = 0) -> None:
        if depth > 3:
            return
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, dict):
            for x in v.values():
                walk(x, depth + 1)
        elif isinstance(v, (list, tuple)):
            for x in v:
                walk(x, depth + 1)

    walk(finding)
    return "\n".join(parts)


def apply_grief_economics(severity: str, finding: dict) -> tuple[str, list[str]]:
    """Cap grief/DoS severity when the attacker pays more than the victim loses,
    when a routine operator action restores service, or when neither side of that
    trade has been quantified. See rules/severity-matrix.md → Grief economics.

    Returns (new_severity, applied_modifiers). Never raises severity.
    """
    applied: list[str] = []
    if sev_index(severity) <= sev_index("Low"):
        return (severity, applied)  # already at/below the cap — nothing to do

    extra = finding.get("extra") or {}
    flags = {str(k).upper(): v for k, v in extra.items()}
    text = _finding_text(finding)

    # (a) Explicit uneconomic-grief tag from the realism filter.
    if finding.get("realism_filter") == "uneconomic-grief":
        applied.append(f"cap@Low: uneconomic-grief (was {severity})")
        return (cap(severity, "Low"), applied)

    # (b) Operator-recoverable — declared, or admitted by the finding's own text.
    recoverable = flags.get("OPERATOR_RECOVERABLE")
    if recoverable in TRUTHY:
        applied.append(f"cap@Low: operator-recoverable (declared; was {severity})")
        return (cap(severity, "Low"), applied)
    if recoverable not in FALSEY and RECOVERY_ADMISSION_RE.search(text):
        # The writeup concedes a recovery path but never answered the question.
        # An author who disagrees sets `operator_recoverable: false` explicitly.
        applied.append(
            f"cap@Low: operator-recoverable admitted in the finding's own text and not "
            f"rebutted via `operator_recoverable: false` (was {severity})")
        return (cap(severity, "Low"), applied)

    # (c) Grief/DoS above Low must quantify BOTH sides of the trade.
    is_grief = bool(GRIEF_CLASS_RE.search(text))
    if is_grief:
        has_cost = str(flags.get("ATTACKER_COST") or "").strip() != ""
        has_harm = str(flags.get("VICTIM_HARM") or "").strip() != ""
        if not (has_cost and has_harm):
            missing = ", ".join(
                n for n, ok in (("attacker_cost", has_cost), ("victim_harm", has_harm)) if not ok)
            applied.append(
                f"cap@Low: unquantified grief — missing {missing} (was {severity})")
            return (cap(severity, "Low"), applied)

    return (severity, applied)


def apply_l1_evidence_floor(severity: str, evidence_tags: list[str]) -> tuple[str, list[str]]:
    """If any L1 evidence tag implies a higher severity floor, raise severity to it.
    Returns (new_severity, applied_modifiers)."""
    applied: list[str] = []
    for tag in evidence_tags or []:
        floor = L1_EVIDENCE_FLOORS.get(tag)
        if floor is None:
            continue
        if sev_index(floor) > sev_index(severity):
            applied.append(f"+evidence floor: [{tag}] raises to {floor} (was {severity})")
            severity = floor
    return severity, applied


def derive_severity(finding: dict, proven_only: bool = False, l1_mode: bool = False) -> tuple[str | None, str | None, list[str]]:
    """Return (final_severity, severity_pre_modifier, applied_modifiers).

    severity_pre_modifier is set only when at least one downgrade was applied.
    Returns (None, None, []) if neither severity nor impact+likelihood are present.
    When l1_mode=True, applies L1 evidence-floor logic from rules/l1-severity-matrix.md.
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

    # Step 3b: grief/DoS economic gates (rules/severity-matrix.md).
    # Runs before proven-only so a passing PoC cannot rescue an uneconomic grief:
    # the DRE rejection had an end-to-end PoC and was still invalid.
    new, grief_applied = apply_grief_economics(severity, finding)
    if new != severity:
        pre = pre or severity
        applied.extend(grief_applied)
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

    # Step 5: L1 evidence-floor (raises severity if a high-floor tag is present)
    # Applied LAST so the floor wins over downgrades — per rules/l1-severity-matrix.md
    # "If the matrix says Low but the evidence is [DIFF-PASS], the FINAL severity is High".
    if l1_mode:
        new_sev, l1_applied = apply_l1_evidence_floor(severity, finding.get("evidence_tags") or [])
        if new_sev != severity:
            applied.extend(l1_applied)
            severity = new_sev

    return (severity, pre, applied)


def route(data: dict, proven_only: bool = False, l1_mode: bool = False) -> tuple[dict, list[dict]]:
    """Walk data['findings'], assign severities, return (data, diff_records)."""
    diff: list[dict] = []
    for f in data.get("findings") or []:
        if f.get("canonical_id"):
            # duplicates inherit; severity-router runs on canonicals only.
            continue
        old_sev = f.get("severity")
        old_pre = f.get("severity_pre_modifier")
        sev, pre, applied = derive_severity(f, proven_only=proven_only, l1_mode=l1_mode)
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
    ap.add_argument("--l1", action="store_true",
                    help="Apply L1 evidence-floor logic per rules/l1-severity-matrix.md "
                         "(DIFF-PASS / NON-DET-PASS -> High floor; FUZZ-PASS -> Medium floor).")
    ap.add_argument("--diff-out", default=None, help="Write a per-finding diff log to this path.")
    ap.add_argument("--report", action="store_true", help="Print human-readable change report to stderr.")
    args = ap.parse_args(argv)

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    routed, diff = route(data, proven_only=args.proven_only, l1_mode=args.l1)

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
