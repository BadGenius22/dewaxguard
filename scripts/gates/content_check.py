#!/usr/bin/env python3
"""content_check.py — Phase-output content gate for the v1.13 driver.

Verifies that the files a phase declared as required_outputs:

  1. exist (or matched ≥ 1 file when the entry is a glob like `analysis_*.md`)
  2. are non-empty (above MIN_BYTES)
  3. are not stub placeholders (don't consist only of phrases like
     "I will analyse...", "TODO", "TBD", or just whitespace + a header)
  4. contain at least one of the required section markers when the file's
     name matches a known phase output pattern (e.g., `findings_routed.json`
     must be valid JSON with a `findings` array; `analysis_*.md` must
     contain ≥ 1 `FINDING |` or `LEAD |` header).

Exit codes:
  0 — all checks pass
  1 — any required output missing/empty/stub/malformed
  2 — invalid invocation
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


MIN_BYTES = 200  # absolute minimum file size to count as "real content"
STUB_PHRASES = [
    "i will analyse",
    "i will analyze",
    "to be filled",
    "tbd",
    "todo",
    "placeholder",
    "no findings yet",
    "pending",
]
HEADER_ONLY_RE = re.compile(r"^[\s#*_>=-]*[\w \-:,]{0,80}[\s#*_>=-]*$", re.MULTILINE)


# Per-output-pattern requirements
def is_findings_json(path: Path) -> tuple[bool, str]:
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return (False, f"invalid JSON: {e}")
    if not isinstance(d, dict):
        return (False, "top-level not an object")
    if "findings" not in d:
        return (False, "missing 'findings' key")
    if not isinstance(d["findings"], list):
        return (False, "'findings' not a list")
    return (True, f"{len(d['findings'])} findings")


def is_analysis_md(path: Path) -> tuple[bool, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    has_pipe = bool(re.search(r"^\s*(FINDING|LEAD)\s*\|", text, re.MULTILINE))
    has_md = bool(re.search(r"^##\s+Finding\s+\[", text, re.MULTILINE))
    if not (has_pipe or has_md):
        return (False, "no FINDING/LEAD headers found")
    n_pipe = len(re.findall(r"^\s*(FINDING|LEAD)\s*\|", text, re.MULTILINE))
    n_md = len(re.findall(r"^##\s+Finding\s+\[", text, re.MULTILINE))
    return (True, f"pipe={n_pipe}, md={n_md}")


def is_report_md(path: Path) -> tuple[bool, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    required_sections = ["executive summary", "summary", "critical", "high", "medium", "low"]
    found = sum(1 for s in required_sections if s in text.lower())
    if found < 3:
        return (False, f"only {found}/{len(required_sections)} expected sections present")
    return (True, f"{found}/{len(required_sections)} sections")


def is_generic_md(path: Path) -> tuple[bool, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    body = text.strip()
    if len(body) < MIN_BYTES:
        return (False, f"too short ({len(body)} bytes)")
    lower = body.lower()
    for phrase in STUB_PHRASES:
        # stub phrase dominates if it appears in the first 200 bytes AND no other content follows
        if phrase in lower[:300] and len(body) < 800:
            return (False, f"stub phrase found: {phrase!r}")
    # check it's not just a header
    non_header_lines = [
        line for line in body.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if len(non_header_lines) < 3:
        return (False, "fewer than 3 non-header lines")
    return (True, f"{len(body)} bytes, {len(non_header_lines)} non-header lines")


def classify(path: Path) -> tuple[bool, str]:
    """Pick the right validator for this file."""
    name = path.name
    if name.endswith(".json") and "findings" in name:
        return is_findings_json(path)
    if name.endswith(".json"):
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
            if not d:
                return (False, "empty JSON")
            return (True, f"JSON ({len(json.dumps(d))} bytes)")
        except json.JSONDecodeError as e:
            return (False, f"invalid JSON: {e}")
    if name.startswith("analysis_") or name.startswith("depth_") or name.startswith("blind_") \
       or name.startswith("verify_"):
        return is_analysis_md(path)
    if name == "AUDIT_REPORT.md":
        return is_report_md(path)
    return is_generic_md(path)


def expand_required(required: list[str], scratchpad: Path) -> list[tuple[str, list[Path]]]:
    """Expand glob entries to actual paths; return list of (spec, [matches])."""
    out: list[tuple[str, list[Path]]] = []
    for spec in required:
        spec = spec.strip()
        if not spec:
            continue
        # interpret relative to scratchpad if it starts with "scratchpad/",
        # or relative to scratchpad's parent otherwise (e.g. AUDIT_REPORT.md)
        if spec.startswith("scratchpad/"):
            spec_rel = spec[len("scratchpad/"):]
            base = scratchpad
        elif spec.startswith("/") or spec.startswith("./"):
            base = Path(".")
            spec_rel = spec
        else:
            base = scratchpad.parent
            spec_rel = spec
        if any(ch in spec_rel for ch in "*?["):
            matches = sorted(base.glob(spec_rel))
        else:
            matches = [base / spec_rel] if (base / spec_rel).exists() else []
        out.append((spec, matches))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True)
    ap.add_argument("--scratchpad", type=Path, required=True)
    ap.add_argument("--required", required=True,
                    help="Comma-separated list of required output paths/globs.")
    args = ap.parse_args(argv)

    required = [s for s in args.required.split(",") if s.strip()]
    expanded = expand_required(required, args.scratchpad)

    failures: list[str] = []
    okays: list[str] = []
    for spec, matches in expanded:
        if not matches:
            failures.append(f"missing: {spec}")
            continue
        for m in matches:
            if not m.exists():
                failures.append(f"missing: {m}")
                continue
            try:
                size = m.stat().st_size
            except OSError as e:
                failures.append(f"unreadable {m}: {e}")
                continue
            if size == 0:
                failures.append(f"empty: {m}")
                continue
            ok, msg = classify(m)
            if ok:
                okays.append(f"{m.name}: {msg}")
            else:
                failures.append(f"bad content {m}: {msg}")

    if failures:
        print(f"FAIL phase={args.phase}: " + "; ".join(failures))
        return 1
    print(f"OK phase={args.phase}: " + "; ".join(okays))
    return 0


if __name__ == "__main__":
    sys.exit(main())
