#!/usr/bin/env python3
"""dewaxguard_driver.py — Deterministic phase orchestrator for dewaxguard v1.13+.

Replaces the prompt-only LLM orchestrator (SKILL.md) with a Python driver that
spawns `claude -p` subprocesses per phase. Benefits over the prompt-only flow:

  * Each phase runs in a fresh context window — no context-saturation drift
  * Gates after every phase check for required outputs, real content,
    coverage of in-scope files; failures trigger TARGETED retry prompts
  * Crash-resumable via per-phase checkpoint sentinels
  * Backend-agnostic — switch `claude` for `codex` via --backend
  * Opt-in: legacy SKILL.md prompt-only flow remains the default when
    /dewaxguard is invoked without --driver

Layout:

  prompts/phases/{NN}_{name}.md   — per-phase prompt template (instantiated by
                                    driver with project state placeholders)
  scripts/gates/*.py              — content/coverage gates the driver invokes
                                    between phases
  scratchpad/checkpoints/         — driver-managed checkpoint sentinels
  scratchpad/driver/              — driver-managed transcripts/state
  scratchpad/driver/manifest.json — driver-managed phase state

Invocation:

  python3 scripts/dewaxguard_driver.py \
      --mode core \
      --src ./contracts \
      --audit-id myproj-2026-05 \
      [--backend claude|codex] \
      [--resume] [--phase recon|breadth|...] [--retry-budget 2]

The driver itself does NOT spawn agents directly via the Task tool — only the
phase subprocesses do. The driver is a control-plane process: it orchestrates,
gates, and checkpoints. Phase subprocesses are the data-plane: they read source,
write findings, and call MCP/tools.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path


# ── phase registry ───────────────────────────────────────────────────────────
@dataclass
class Phase:
    """One phase in the pipeline."""
    name: str
    template: str  # filename under prompts/phases/, e.g. "10_recon.md"
    required_outputs: list[str] = field(default_factory=list)  # paths under scratchpad
    timeout_seconds: int = 1800  # 30min default; recon/breadth/depth get 2x in v2
    gates: list[str] = field(default_factory=list)  # script names under scripts/gates/
    mode_min: str = "light"  # smallest mode that runs this phase
    l1_only: bool = False  # if True, this phase runs ONLY when --l1 is set
    sc_only: bool = False  # if True, this phase runs ONLY when --l1 is NOT set
    l1_template: str | None = None  # override template path when --l1 is set

# Order matters: the driver runs phases in registry order.
PHASES: list[Phase] = [
    Phase(
        name="preflight",
        template="00_preflight.md",
        required_outputs=["scratchpad/preflight.md"],
        timeout_seconds=900,
        gates=["content_check"],
    ),
    Phase(
        name="recon",
        template="10_recon.md",
        required_outputs=[
            "scratchpad/build_status.md",
            "scratchpad/design_context.md",
            "scratchpad/attack_surface.md",
            "scratchpad/contract_inventory.md",
        ],
        timeout_seconds=3600,
        gates=["content_check"],
    ),
    Phase(
        name="bake",
        template="05_bake.md",
        required_outputs=[
            "scratchpad/bake_summary.md",
            "scratchpad/bake/_bake_summary.md",
        ],
        timeout_seconds=900,
        gates=["content_check"],
        l1_only=True,  # L1 mode only — runs between recon and breadth
    ),
    Phase(
        name="breadth",
        template="30_breadth.md",
        required_outputs=["scratchpad/analysis_*.md"],  # glob
        timeout_seconds=3600,
        gates=["content_check", "coverage_check"],
    ),
    Phase(
        name="inventory",
        template="40_inventory.md",
        required_outputs=[
            "scratchpad/findings_routed.json",
            "scratchpad/dedup_clusters.json",
        ],
        timeout_seconds=600,
        gates=["content_check"],
    ),
    Phase(
        name="niche",
        template="42_niche.md",
        required_outputs=["scratchpad/niche_summary.md"],
        timeout_seconds=3600,
        gates=["content_check"],
    ),
    Phase(
        name="depth",
        template="45_depth.md",
        l1_template="45_depth_l1.md",  # L1 mode swaps in the L1 depth dispatcher
        required_outputs=["scratchpad/depth_*_findings.md"],  # glob; ≥1 required
        timeout_seconds=5400,  # 90min — 6 parallel agents
        gates=["content_check"],
    ),
    Phase(
        name="nemesis",
        template="46_nemesis.md",
        required_outputs=["scratchpad/nemesis_summary.md"],
        timeout_seconds=7200,  # 2hr — up to 6 sequential cross-feed passes
        gates=["content_check"],
        mode_min="thorough",
    ),
    Phase(
        name="chain",
        template="47_chain.md",
        required_outputs=[
            "scratchpad/hypotheses.md",
            "scratchpad/chain_hypotheses.md",
        ],
        timeout_seconds=2400,  # 40min — 2 sequential agents
        gates=["content_check"],
    ),
    Phase(
        name="verify",
        template="50_verify.md",
        required_outputs=["scratchpad/verify_*.md"],
        timeout_seconds=3600,
        gates=["content_check"],
        mode_min="core",
    ),
    Phase(
        name="validator",
        template="55_validator.md",
        required_outputs=[
            "scratchpad/validation_results.json",
            "scratchpad/validation_summary.md",
        ],
        timeout_seconds=1800,
        gates=["content_check"],
        mode_min="core",
    ),
    Phase(
        name="report",
        template="60_report.md",
        required_outputs=["AUDIT_REPORT.md"],
        timeout_seconds=1800,
        gates=["content_check"],
    ),
]


MODE_ORDER = {"light": 0, "core": 1, "thorough": 2}


# ── driver state ─────────────────────────────────────────────────────────────
@dataclass
class DriverState:
    mode: str
    src: Path
    project_root: Path
    audit_id: str
    backend: str
    skill_root: Path
    scratchpad: Path
    driver_dir: Path
    checkpoint_dir: Path
    retry_budget: int
    dry_run: bool
    skip_gates: bool = False
    l1: bool = False  # L1 mode — adds Bake phase, swaps depth template for L1 dispatcher

    @property
    def manifest_path(self) -> Path:
        return self.driver_dir / "manifest.json"

    def load_manifest(self) -> dict:
        if self.manifest_path.exists():
            return json.loads(self.manifest_path.read_text())
        return {"audit_id": self.audit_id, "mode": self.mode, "phases": {}}

    def save_manifest(self, m: dict) -> None:
        self.manifest_path.write_text(json.dumps(m, indent=2))

    def checkpoint(self, phase: str) -> Path:
        return self.checkpoint_dir / f"{phase}.done"

    def is_complete(self, phase: str) -> bool:
        return self.checkpoint(phase).exists()

    def mark_complete(self, phase: str, payload: dict | None = None) -> None:
        self.checkpoint(phase).write_text(json.dumps(payload or {"at": _now_iso()}, indent=2))


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


# ── template instantiation ───────────────────────────────────────────────────
def instantiate_template(template_path: Path, state: DriverState, phase: Phase, extra: dict | None = None) -> str:
    text = template_path.read_text(encoding="utf-8")
    extra = extra or {}
    placeholders = {
        "MODE": state.mode,
        "SRC_PATH": str(state.src),
        "PROJECT_ROOT": str(state.project_root),
        "AUDIT_ID": state.audit_id,
        "SCRATCHPAD": str(state.scratchpad),
        "SKILL_ROOT": str(state.skill_root),
        "DRIVER_DIR": str(state.driver_dir),
        "PHASE_NAME": phase.name,
        "TIMEOUT_SECONDS": str(phase.timeout_seconds),
        "ISO_NOW": _now_iso(),
        "L1_MODE": "true" if state.l1 else "false",
        **extra,
    }
    for k, v in placeholders.items():
        text = text.replace(f"{{{{{k}}}}}", v)
    return text


# ── gate execution ───────────────────────────────────────────────────────────
def run_gates(state: DriverState, phase: Phase) -> tuple[bool, list[str]]:
    """Returns (passed, failure_messages)."""
    if state.skip_gates:
        return (True, [])
    failures: list[str] = []
    for gate in phase.gates:
        gate_path = state.skill_root / "scripts" / "gates" / f"{gate}.py"
        if not gate_path.exists():
            failures.append(f"gate script missing: {gate_path}")
            continue
        # gates receive: phase name, scratchpad, list of required outputs (glob-expanded)
        outputs_arg = ",".join(phase.required_outputs)
        cmd = [
            sys.executable, str(gate_path),
            "--phase", phase.name,
            "--scratchpad", str(state.scratchpad),
            "--required", outputs_arg,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            failures.append(f"gate timeout: {gate}")
            continue
        if result.returncode != 0:
            failures.append(f"{gate}: {result.stdout.strip()} | {result.stderr.strip()}")
    return (not failures, failures)


# ── subprocess invocation ────────────────────────────────────────────────────
def invoke_phase(state: DriverState, phase: Phase, retry_n: int = 0, retry_hint: str | None = None) -> dict:
    """Spawn `claude -p` (or `codex exec`) for one phase. Returns transcript record."""
    # In L1 mode, use the L1 variant template if the phase defines one.
    template_name = phase.l1_template if (state.l1 and phase.l1_template) else phase.template
    template_path = state.skill_root / "prompts" / "phases" / template_name
    if not template_path.exists():
        return {"phase": phase.name, "status": "error", "error": f"template not found: {template_path}"}

    prompt = instantiate_template(template_path, state, phase, extra={"RETRY_HINT": retry_hint or ""})

    transcript_path = state.driver_dir / f"transcript_{phase.name}_{retry_n}.md"
    transcript_path.write_text(f"# Phase: {phase.name} (retry {retry_n})\n\n## Prompt\n\n{prompt}\n\n## Output\n\n")

    backend_bin = shutil.which(state.backend)
    if not backend_bin:
        return {"phase": phase.name, "status": "error", "error": f"{state.backend} not on PATH"}

    # Backend dispatch — for v1.13 we support claude and codex
    if state.backend == "claude":
        cmd = [backend_bin, "-p", prompt, "--output-format", "stream-json", "--verbose"]
    elif state.backend == "codex":
        cmd = [backend_bin, "exec", prompt]
    else:
        return {"phase": phase.name, "status": "error", "error": f"unsupported backend: {state.backend}"}

    if state.dry_run:
        # store a stable cmd summary, not the literal prompt (which is already
        # in transcript_path)
        cmd_summary = f"{state.backend} -p [{len(prompt)} bytes prompt at {transcript_path}]"
        rec = {
            "phase": phase.name,
            "retry": retry_n,
            "status": "dry_run",
            "cmd": cmd_summary,
            "prompt_bytes": len(prompt),
            "started_at": _now_iso(),
        }
        with transcript_path.open("a") as f:
            f.write("DRY RUN — subprocess not executed.\n")
        return rec

    start = time.monotonic()
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=phase.timeout_seconds, cwd=state.project_root,
        )
        elapsed = time.monotonic() - start
        with transcript_path.open("a") as f:
            f.write(result.stdout)
            if result.stderr:
                f.write("\n\n## STDERR\n\n")
                f.write(result.stderr)
        return {
            "phase": phase.name,
            "retry": retry_n,
            "status": "ok" if result.returncode == 0 else "exit_nonzero",
            "exit_code": result.returncode,
            "elapsed_s": round(elapsed, 1),
            "transcript": str(transcript_path),
            "started_at": _now_iso(),
        }
    except subprocess.TimeoutExpired:
        with transcript_path.open("a") as f:
            f.write(f"\n\n## TIMEOUT after {phase.timeout_seconds}s\n")
        return {
            "phase": phase.name,
            "retry": retry_n,
            "status": "timeout",
            "elapsed_s": phase.timeout_seconds,
            "transcript": str(transcript_path),
        }


# ── pipeline driver ──────────────────────────────────────────────────────────
def select_phases(mode: str, only: list[str] | None, l1: bool = False) -> list[Phase]:
    threshold = MODE_ORDER.get(mode, 0)
    out: list[Phase] = []
    for p in PHASES:
        if MODE_ORDER.get(p.mode_min, 0) > threshold:
            continue
        if p.l1_only and not l1:
            continue
        if p.sc_only and l1:
            continue
        out.append(p)
    if only:
        out = [p for p in out if p.name in only]
    return out


def run_pipeline(state: DriverState, only: list[str] | None = None, resume: bool = False) -> int:
    state.scratchpad.mkdir(parents=True, exist_ok=True)
    state.driver_dir.mkdir(parents=True, exist_ok=True)
    state.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    manifest = state.load_manifest()
    manifest.setdefault("phases", {})
    manifest["audit_id"] = state.audit_id
    manifest["mode"] = state.mode
    manifest["last_run_at"] = _now_iso()
    state.save_manifest(manifest)

    phases = select_phases(state.mode, only, l1=state.l1)
    l1_tag = " [L1]" if state.l1 else ""
    print(f"[driver]{l1_tag} audit_id={state.audit_id} mode={state.mode} backend={state.backend} phases={[p.name for p in phases]}", file=sys.stderr)

    overall = 0
    for phase in phases:
        if resume and state.is_complete(phase.name):
            print(f"[driver] {phase.name}: SKIP (checkpoint exists)", file=sys.stderr)
            continue

        for retry_n in range(state.retry_budget + 1):
            hint = None
            if retry_n > 0:
                # Build retry hint from prior failure messages
                last = manifest["phases"].get(phase.name, {}).get("last_failure_msgs", [])
                hint = "\n".join(f"- {m}" for m in last)
                print(f"[driver] {phase.name}: retry {retry_n} with hint: {hint!r}", file=sys.stderr)

            rec = invoke_phase(state, phase, retry_n=retry_n, retry_hint=hint)
            passed, failures = run_gates(state, phase)
            rec["gates_passed"] = passed
            rec["gate_failures"] = failures

            manifest["phases"][phase.name] = rec
            state.save_manifest(manifest)

            if rec["status"] not in ("ok", "dry_run"):
                print(f"[driver] {phase.name}: subprocess {rec['status']}; gates={passed}", file=sys.stderr)
            else:
                print(f"[driver] {phase.name}: subprocess ok in {rec.get('elapsed_s','?')}s; gates={passed}", file=sys.stderr)

            if passed and rec["status"] in ("ok", "dry_run"):
                state.mark_complete(phase.name, {"retry_n": retry_n, "at": _now_iso()})
                break
            else:
                manifest["phases"][phase.name]["last_failure_msgs"] = failures
                state.save_manifest(manifest)
        else:
            # exhausted retries
            print(f"[driver] {phase.name}: FAILED after {state.retry_budget} retries; aborting pipeline", file=sys.stderr)
            overall = 1
            break

    return overall


# ── CLI ──────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    skill_root_default = Path(__file__).resolve().parent.parent  # scripts/ -> dewaxguard/
    ap = argparse.ArgumentParser(
        description="dewaxguard v1.13 deterministic phase orchestrator.",
    )
    ap.add_argument("--mode", choices=["light", "core", "thorough"], default="core")
    ap.add_argument("--src", type=Path, required=True, help="Path to source code under audit.")
    ap.add_argument("--project-root", type=Path, default=None, help="Project root (default: --src parent).")
    ap.add_argument("--audit-id", default=None, help="Stable audit identifier (default: derived from src+date).")
    ap.add_argument("--backend", choices=["claude", "codex"], default="claude")
    ap.add_argument("--skill-root", type=Path, default=skill_root_default)
    ap.add_argument("--scratchpad", type=Path, default=None,
                    help="Scratchpad dir (default: <project_root>/scratchpad).")
    ap.add_argument("--phase", action="append", default=None,
                    help="Only run these phases (can repeat).")
    ap.add_argument("--resume", action="store_true",
                    help="Skip phases with existing checkpoints.")
    ap.add_argument("--retry-budget", type=int, default=2)
    ap.add_argument("--dry-run", action="store_true",
                    help="Print what would be invoked, don't spawn subprocesses.")
    ap.add_argument("--skip-gates", action="store_true",
                    help="Skip content/coverage gate checks (smoke tests + emergency bypass).")
    ap.add_argument("--l1", action="store_true",
                    help="L1 mode: audit a Go/Rust node client. Adds Phase 0.5 Bake; "
                         "swaps depth-state-trace + depth-external for depth-consensus-invariant + "
                         "depth-network-surface; applies L1 severity matrix and evidence floors. "
                         "Use for Geth/Reth/Lighthouse/Cosmos-SDK/CometBFT-class targets.")
    args = ap.parse_args(argv)

    src = args.src.resolve()
    if not src.exists():
        print(f"[driver] --src not found: {src}", file=sys.stderr)
        return 2
    project_root = (args.project_root or src.parent).resolve()
    audit_id = args.audit_id or f"{project_root.name}-{_dt.date.today().isoformat()}"
    scratchpad = (args.scratchpad or (project_root / "scratchpad")).resolve()

    state = DriverState(
        mode=args.mode,
        src=src,
        project_root=project_root,
        audit_id=audit_id,
        backend=args.backend,
        skill_root=args.skill_root.resolve(),
        scratchpad=scratchpad,
        driver_dir=scratchpad / "driver",
        checkpoint_dir=scratchpad / "checkpoints",
        retry_budget=args.retry_budget,
        dry_run=args.dry_run,
        skip_gates=args.skip_gates,
        l1=args.l1,
    )
    return run_pipeline(state, only=args.phase, resume=args.resume)


if __name__ == "__main__":
    sys.exit(main())
