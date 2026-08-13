#!/usr/bin/env python3
"""coverage_check.py — Mechanical file-visit gate for the Codex driver.

Verifies that every in-scope source file appeared in a Codex tool invocation
during the phase. Reads the `codex exec --json` JSONL transcript under
`{SCRATCHPAD}/driver/transcript_{phase}_{retry}.jsonl`, extracts explicit file
paths from command/tool payloads, and compares them with the mechanically
enumerated scope.

Outputs a TARGETED retry hint when files are missed: instead of "try again",
the driver writes "you missed Vault.sol:120-180 — audit it with M-14".

This is the structural enforcement equivalent of the prose-only "don't skip
files" rule in shared-rules.md.

Exit codes:
  0 — all in-scope files were read by at least one agent
  1 — coverage gap; output names the missing files
  2 — invalid invocation
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


# Legacy structured Read/Grep/Glob patterns are retained as a fallback for
# transcripts emitted by older drivers.
TOOL_USE_RE = re.compile(
    r'"name"\s*:\s*"Read"[^}]*?"file_path"\s*:\s*"([^"]+)"',
    re.IGNORECASE,
)
# Fallback for grep/glob — track those as "visited" too even though they don't
# read full file contents
GREP_GLOB_RE = re.compile(
    r'"name"\s*:\s*"(?:Grep|Glob)"[^}]*?"(?:pattern|path)"\s*:\s*"([^"]+)"',
    re.IGNORECASE,
)


SOURCE_EXTENSIONS = {
    ".sol", ".vy", ".huff",          # EVM
    ".rs",                           # Rust (Solana, Soroban, native)
    ".move",                         # Move (Aptos, Sui)
    ".cpp", ".cc", ".hpp", ".h",     # C/C++
    ".go",                           # Go (L1)
    ".ts", ".tsx", ".js",            # JS/TS (mostly out of scope but tracked)
}


def enumerate_in_scope(src_root: Path, scope_file: Path | None = None,
                       project_root: Path | None = None) -> list[Path]:
    if scope_file and scope_file.exists():
        base = project_root or Path.cwd()
        out: list[Path] = []
        for line in scope_file.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            p = Path(line)
            out.append(p if p.is_absolute() else (base / p))
        return out
    out: list[Path] = []
    for p in src_root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in SOURCE_EXTENSIONS:
            continue
        # exclude common non-audit paths
        parts = set(p.parts)
        if any(seg in parts for seg in ("node_modules", "target", "dependencies", "lib", "vendor", "test", "tests", "__pycache__")):
            continue
        out.append(p.resolve())
    return out


def _tool_payloads(value: object) -> list[str]:
    """Collect strings only from command/tool-call objects, not assistant prose."""
    out: list[str] = []
    if isinstance(value, list):
        for item in value:
            out.extend(_tool_payloads(item))
        return out
    if not isinstance(value, dict):
        return out

    kind = " ".join(str(value.get(k, "")) for k in ("type", "name", "tool_name")).lower()
    is_tool = any(token in kind for token in (
        "command_execution", "tool_call", "function_call", "exec_command",
        "shell", "read", "grep", "glob",
    ))
    if is_tool:
        for key in ("command", "cmd", "input", "arguments", "path", "file_path"):
            payload = value.get(key)
            if isinstance(payload, str):
                out.append(payload)
            elif isinstance(payload, (dict, list)):
                out.append(json.dumps(payload, sort_keys=True))

    for nested in value.values():
        if isinstance(nested, (dict, list)):
            out.extend(_tool_payloads(nested))
    return out


def read_transcript_files(transcript_path: Path, project_root: Path,
                          in_scope: list[Path]) -> set[Path]:
    """Return paths explicitly present in Codex command/tool payloads."""
    if not transcript_path.exists():
        return set()
    text = transcript_path.read_text(encoding="utf-8", errors="replace")
    paths: set[Path] = set()

    payloads: list[str] = []
    for line in text.splitlines():
        try:
            payloads.extend(_tool_payloads(json.loads(line)))
        except json.JSONDecodeError:
            continue

    for candidate in in_scope:
        resolved = candidate.resolve()
        try:
            relative = resolved.relative_to(project_root).as_posix()
        except ValueError:
            relative = ""
        variants = {str(resolved), resolved.as_posix(), relative, f"./{relative}" if relative else ""}
        variants.discard("")
        if any(variant in payload for payload in payloads for variant in variants):
            paths.add(resolved)

    # Structured legacy fallback.
    for m in TOOL_USE_RE.finditer(text):
        raw = m.group(1)
        p = Path(raw)
        if not p.is_absolute():
            p = (project_root / p).resolve()
        paths.add(p)
    for m in GREP_GLOB_RE.finditer(text):
        raw = m.group(1)
        # Grep/Glob patterns are not file paths; check if it resolves
        p = Path(raw)
        if not p.is_absolute():
            p = (project_root / p).resolve()
        if p.exists() and p.is_file():
            paths.add(p)
    return paths


def find_all_phase_transcripts(scratchpad: Path, phase: str) -> list[Path]:
    driver_dir = scratchpad / "driver"
    if not driver_dir.exists():
        return []
    return sorted(driver_dir.glob(f"transcript_{phase}_*.jsonl"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True)
    ap.add_argument("--scratchpad", type=Path, required=True)
    ap.add_argument("--required", default="",
                    help="Required outputs; ignored by coverage gate but accepted for driver-uniform invocation.")
    ap.add_argument("--src", type=Path, default=None,
                    help="Source root to enumerate. Default: guessed under project root.")
    ap.add_argument("--project-root", type=Path, default=None,
                    help="Project root for resolving relative Read/scope paths. Default: scratchpad parent.")
    ap.add_argument("--scope-file", type=Path, default=None,
                    help="Explicit list of in-scope files (one path per line).")
    ap.add_argument("--max-misses", type=int, default=0,
                    help="Allowed number of unread files (default 0). Use >0 for soft-gate phases.")
    args = ap.parse_args(argv)

    project_root = (args.project_root or args.scratchpad.parent).resolve()

    # Resolve src: prefer the explicit --src the driver passes; otherwise guess
    # common source roots under the project root.
    src = args.src
    if src is None:
        src = project_root / "contracts"  # best guess
        if not src.exists():
            for cand in ("src", "programs", "modules", "sources"):
                if (project_root / cand).exists():
                    src = project_root / cand
                    break
    if not src.exists():
        print(f"FAIL phase={args.phase}: --src not found ({src}); cannot enumerate scope", file=sys.stderr)
        return 2

    in_scope = enumerate_in_scope(src, args.scope_file, project_root)
    if not in_scope:
        print(f"OK phase={args.phase}: no in-scope source files detected (empty scope is fine)")
        return 0

    transcripts = find_all_phase_transcripts(args.scratchpad, args.phase)
    if not transcripts:
        print(f"FAIL phase={args.phase}: no transcripts found under {args.scratchpad}/driver/")
        return 1

    visited: set[Path] = set()
    for t in transcripts:
        visited |= read_transcript_files(t, project_root, in_scope)

    in_scope_set = {p.resolve() for p in in_scope}
    missed = sorted(in_scope_set - visited)

    if len(missed) <= args.max_misses:
        msg = f"OK phase={args.phase}: read {len(in_scope_set & visited)}/{len(in_scope_set)} in-scope files"
        if missed:
            msg += f" (allowed {args.max_misses} misses)"
        print(msg)
        return 0

    # Generate targeted retry hint
    misses_file = args.scratchpad / "driver" / f"coverage_misses_{args.phase}.txt"
    lines = [f"FAIL phase={args.phase}: {len(missed)} in-scope file(s) not read by any agent."]
    lines.append("Retry hint — these files must be read in the next attempt:")
    for p in missed[:20]:
        rel = p.relative_to(project_root) if p.is_relative_to(project_root) else p
        lines.append(f"  - {rel}")
    if len(missed) > 20:
        lines.append(f"  ... and {len(missed) - 20} more (see {misses_file.name})")
        misses_file.write_text("\n".join(str(p) for p in missed))
    print("\n".join(lines))
    return 1


if __name__ == "__main__":
    sys.exit(main())
