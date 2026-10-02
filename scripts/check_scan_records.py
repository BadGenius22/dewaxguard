#!/usr/bin/env python3
"""Synthetic artifact integration checks; no protocol build or target execution."""
from copy import deepcopy
import importlib.util
import io
from contextlib import redirect_stderr
import json
from pathlib import Path
import subprocess
import sys
import tempfile


HELPER = Path(__file__).with_name("scan_records.py")


def run(*args, success=True):
    result = subprocess.run([sys.executable, str(HELPER), *map(str, args)], capture_output=True, text=True)
    if (result.returncode == 0) != success:
        raise AssertionError(f"unexpected status {result.returncode}: {result.stderr}")
    return result


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def check_driver(root, base):
    """Verify template policy/report gate contract without launching a backend."""
    skill = HELPER.parent.parent
    driver = load_module("receipt_check_driver", skill / "scripts/dewaxguard_driver.py")
    gate = load_module("receipt_check_content", skill / "scripts/gates/content_check.py")
    captured = []
    driver.run_pipeline = lambda state, **kwargs: captured.append(state) or 0
    assert driver.main(["--src", str(root / "src"), "--project-root", str(root), "--backend", "codex"]) == 0
    state = captured[0]
    assert state.scratchpad == base / "protocol-audit/scratchpad"
    assert not state.scratchpad.is_relative_to(root)
    with redirect_stderr(io.StringIO()):
        assert driver.main(["--src", str(root / "src"), "--project-root", str(root),
                            "--scratchpad", str(root / "scratchpad")]) == 2
    policy = (skill / "rules/execution-policy.md").read_text(encoding="utf-8")
    for phase in driver.PHASES:
        prompt = driver.instantiate_template(skill / "prompts/phases" / phase.template, state, phase)
        assert policy in prompt
    report = next(phase for phase in driver.PHASES if phase.name == "report")
    prompt = driver.instantiate_template(skill / "prompts/phases" / report.template, state, report)
    assert str(root) + "/AUDIT_REPORT.md" not in prompt
    state.scratchpad.mkdir(parents=True)
    output = state.scratchpad / "AUDIT_REPORT.md"
    output.write_text("Synthetic report artifact", encoding="utf-8")
    assert gate.expand_required(report.required_outputs, state.scratchpad, root)[0][1] == [output]

    # Parse nested same-agent pass outputs together: counters must not collide.
    parse = load_module("receipt_check_parser", skill / "scripts/parse_findings.py")
    raw_paths = []
    for number in (1, 2):
        raw = base / f"passes/pass-{number}/analysis_access_control.md"
        raw.parent.mkdir(parents=True)
        raw.write_text("LEAD | contract: Vault | function: withdraw | bug_class: missing-auth\n"
                       "description: Synthetic lead, requires validation.\n", encoding="utf-8")
        raw_paths.append(raw)
    assert sorted((base / "passes").glob("pass-*/analysis_*.md")) == raw_paths
    union = parse.build_table(parse.parse_files(raw_paths), "synthetic", "breadth")
    assert len(union["findings"]) == 2 and len({row["id"] for row in union["findings"]}) == 2


def main():
    with tempfile.TemporaryDirectory(prefix="dewaxguard-receipts-") as temporary:
        base = Path(temporary)
        root = base / "protocol"
        (root / "src").mkdir(parents=True)
        (root / "script").mkdir()
        (root / "src/Vault.sol").write_text("// synthetic source, never compiled\n", encoding="utf-8")
        (root / "script/Deploy.s.sol").write_text("// synthetic deployment\n", encoding="utf-8")
        check_driver(root, base)
        scope = base / "scope.txt"
        scope.write_text("src/Vault.sol\nscript/Deploy.s.sol\n", encoding="utf-8")
        workspace = base / "evidence"

        def init(scan_id, memory=False, passes=3, scope_file=scope, work=workspace, success=True):
            return run("init", "--project-root", root, "--workspace", work,
                       "--target-id", "synthetic", "--scan-id", scan_id,
                       "--source-commit", "a" * 40, "--scope-file", scope_file,
                       "--passes", passes, *(["--memory"] if memory else []), success=success)

        def record(scan, receipt, success=True):
            source = base / "input.json"
            source.write_text(json.dumps(receipt), encoding="utf-8")
            return run("record", "--scan", scan, "--input", source, success=success)

        def row(mechanism="recipient", function="withdraw", file="src/Vault.sol", markdown=None):
            return {"source_file": file, "contract": "Vault", "function": function,
                    "bug_class": "missing-auth", "mechanism": mechanism, "kind": "LEAD",
                    "disposition": "needs_validation", "markdown": markdown or
                    "**Synthetic lead**\n\nSource: src/Vault.sol:1\n```diff\n--- a/Vault.sol\n+++ b/Vault.sol\n+ check_owner();\n```"}

        def receipt(number=1, rows=None):
            return {"pass": number, "conditioning": "fresh" if number == 1 else "findings-fed",
                    "agents_expected": ["access-control", "invariant"],
                    "agents_returned": ["access-control"], "limitations": ["One worker did not return."],
                    "findings": [row()] if rows is None else rows}

        init("inside", work=root / "scratchpad", success=False)
        bad_scope = base / "bad-scope.txt"
        bad_scope.write_text("../scope.txt\n", encoding="utf-8")
        init("traversal", scope_file=bad_scope, success=False)
        scan = Path(init("first", memory=True).stdout.strip())
        init("first", memory=True, success=False)  # Never overwrite an existing scan.
        record(scan, receipt(2), success=False)  # Barrier: no pass 2 before pass 1.
        first = receipt()
        (scan / ".scan-lock").mkdir()
        record(scan, first, success=False)
        run("assemble", "--scan", scan, success=False)
        assert not (scan / "pass-1.json").exists()
        (scan / ".scan-lock").rmdir()
        record(scan, first)
        record(scan, first)  # Identical receipt retry is safe.
        altered = deepcopy(first)
        altered["findings"][0]["markdown"] += " altered"
        record(scan, altered, success=False)
        same = deepcopy(first)
        same["findings"].append(deepcopy(same["findings"][0]))
        other = Path(init("collision").stdout.strip())
        record(other, same, success=False)
        outside = receipt(rows=[row(file="src/Unknown.sol")])
        record(other, outside, success=False)
        invalid = receipt()
        invalid["findings"][0]["disposition"] = "accepted"
        record(other, invalid, success=False)  # Leads cannot be accepted.
        second_row = row(markdown="**Same cause, second fix**\n```diff\n+ bind_recipient();\n```")
        second_row["kind"] = "FINDING"
        second_row["disposition"] = "rejected"
        second = receipt(2, [second_row, row(mechanism="nonce"), row(function="deposit"),
                             row(file="script/Deploy.s.sol")])
        record(scan, second)
        (scan.parent / ".memory-lock").mkdir()
        run("assemble", "--scan", scan, success=False)
        assert not (scan.parent / "memory.json").exists()
        (scan.parent / ".memory-lock").rmdir()
        run("assemble", "--scan", scan)
        appendix = (scan / "pass-appendix.md").read_text(encoding="utf-8")
        summary = read(scan / "summary.json")
        assert summary["passes_missing"] == [3] and len(summary["observations"]) == 4
        assert "Dispositions conflict" in appendix and "invariant" in appendix
        assert first["findings"][0]["markdown"] in appendix and second_row["markdown"] in appendix
        ledger_path = scan.parent / "memory.json"
        ledger = read(ledger_path)
        assert len(ledger["scans"]) == 1
        assert all(item["scans"] == ["first"] for item in ledger["records"].values())
        run("assemble", "--scan", scan)
        assert read(ledger_path) == ledger
        record(scan, receipt(3), success=False)  # Assembly closes the interrupted loop.

        # The baseline remains frozen, even after another completed scan writes history.
        next_scan = Path(init("next", memory=True, passes=1).stdout.strip())
        record(next_scan, receipt())
        run("assemble", "--scan", next_scan)
        next_summary = read(next_scan / "summary.json")
        assert next_summary["observations"][0]["history"].startswith("KNOWN: 1")
        assert len(read(ledger_path)["records"]) == 4  # Absence never prunes prior identities.

        plain = Path(init("plain", passes=1).stdout.strip())
        assert not (plain / "memory-before.json").exists()
        record(plain, receipt(rows=[]))
        before_plain = read(ledger_path)
        run("assemble", "--scan", plain)
        assert read(ledger_path) == before_plain and read(plain / "summary.json")["observations"] == []

        drift = Path(init("drift", passes=1).stdout.strip())
        (root / "src/Vault.sol").write_text("// changed synthetic source\n", encoding="utf-8")
        record(drift, receipt(), success=False)
        stale = Path(init("stale", memory=True, passes=1).stdout.strip())
        record(stale, receipt())
        run("assemble", "--scan", stale)
        assert read(stale / "summary.json")["observations"][0]["prior_context_changed"]
        # Detect corrupted on-disk identity/pass metadata instead of silently merging.
        corrupt = read(stale / "pass-1.json")
        corrupt["findings"][0]["key"] = "wrong"
        (stale / "pass-1.json").write_text(json.dumps(corrupt), encoding="utf-8")
        run("assemble", "--scan", stale, success=False)
    print("scan-record checks passed: isolation, locking, identities, lossless partial assembly, memory, source drift")


if __name__ == "__main__":
    main()
