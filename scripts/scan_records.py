#!/usr/bin/env python3
"""Record audit passes and assemble a lossless appendix; never execute target code.

This is an opt-in artifact helper, not an audit launcher or a finding validator.
See references/scan-workflow.md for the receipt contract and orchestration.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile


IDENTITY_FIELDS = ("source_file", "contract", "function", "bug_class", "mechanism")
DISPOSITIONS = {"accepted", "needs_validation", "rejected", "excluded"}


def read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def write_json(path: Path, data: dict) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def write_text(path: Path, text: str) -> None:
    """Replace a complete artifact atomically; no partially written JSON/Markdown."""
    fd, name = tempfile.mkstemp(prefix=".scan-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def relative_source(value: str) -> str:
    value = value.replace("\\", "/")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or ":" in value or not path.parts:
        raise ValueError(f"source path must be relative without traversal: {value!r}")
    return path.as_posix()


def source_hash(root: Path, name: str) -> str:
    path = (root / name).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f"source escapes project or is not a file: {name}")
    return digest(path.read_bytes())


def scope_hash(scope: dict) -> str:
    return digest(json.dumps(scope, sort_keys=True).encode())


def check_sources(manifest: dict) -> None:
    root = Path(manifest["project_root"])
    current = {name: source_hash(root, name) for name in manifest["scope"]}
    if current != manifest["scope"]:
        raise ValueError("source content changed during scan; start a new scan")


def empty_memory() -> dict:
    return {"schema_version": 1, "scans": [], "records": {}}


@contextmanager
def scan_lock(scan: Path):
    lock = scan / ".scan-lock"
    lock.mkdir()  # Serialize receipt creation against assembly/closure.
    try:
        yield
    finally:
        lock.rmdir()


def load_memory(path: Path) -> dict:
    if not path.exists():
        return empty_memory()
    data = read_json(path)
    if data.get("schema_version") != 1 or not isinstance(data.get("records"), dict):
        raise ValueError(f"unsupported memory ledger: {path}")
    if not isinstance(data.get("scans"), list):
        raise ValueError(f"invalid scan history: {path}")
    return data


def init_scan(args) -> Path:
    root = args.project_root.resolve(strict=True)
    workspace = args.workspace.resolve()
    if workspace.is_relative_to(root):
        raise ValueError("workspace must be outside the protocol checkout")
    for value in (args.target_id, args.scan_id):
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}", value):
            raise ValueError("target and scan IDs must be 1-80 letters/digits/_/-")
    if not re.fullmatch(r"[0-9a-fA-F]{40}", args.source_commit):
        raise ValueError("source commit must be a full 40-character Git SHA")
    if not 1 <= args.passes <= 10:
        raise ValueError("passes must be between 1 and 10")
    names = [relative_source(s.strip()) for s in args.scope_file.read_text(encoding="utf-8").splitlines()
             if s.strip() and not s.lstrip().startswith("#")]
    if not names or len(names) != len(set(names)):
        raise ValueError("scope must contain unique, nonempty source paths")
    scope = {name: source_hash(root, name) for name in names}
    if len({(root / name).resolve() for name in names}) != len(names):
        raise ValueError("scope contains aliases for the same source file")
    target = workspace / "dewaxguard-scans" / args.target_id
    scan = target / args.scan_id
    if scan.resolve().is_relative_to(root):
        raise ValueError("resolved scan directory must be outside the protocol checkout")
    # Read/validate memory before creating an immutable scan directory.
    before = load_memory(target / "memory.json") if args.memory else None
    scan.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema_version": 1, "target_id": args.target_id, "scan_id": args.scan_id,
        "source_commit": args.source_commit.lower(), "project_root": str(root),
        "scope": scope, "scope_sha256": scope_hash(scope),
        "skill_version": (Path(__file__).resolve().parent.parent / "VERSION").read_text().strip(),
        "passes_requested": args.passes, "memory_enabled": args.memory,
    }
    if before is not None:
        write_json(scan / "memory-before.json", before)
    write_json(scan / "manifest.json", manifest)
    return scan


def string_list(data: dict, field: str) -> list[str]:
    values = data.get(field)
    if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError(f"{field} must be a list of nonempty strings")
    if len(set(values)) != len(values):
        raise ValueError(f"{field} contains duplicates")
    return values


def finding_key(row: dict, manifest: dict) -> str:
    for field in IDENTITY_FIELDS:
        if not isinstance(row.get(field), str) or not row[field].strip():
            raise ValueError(f"finding requires nonempty {field}")
    row["source_file"] = relative_source(row["source_file"])
    if row["source_file"] not in manifest["scope"]:
        raise ValueError(f"finding source is outside frozen scope: {row['source_file']}")
    identity = [row[field] for field in IDENTITY_FIELDS]
    return digest(json.dumps(identity, ensure_ascii=False).encode())


def validate_receipt(receipt: dict, manifest: dict) -> None:
    number = receipt.get("pass")
    if type(number) is not int or not 1 <= number <= manifest["passes_requested"]:
        raise ValueError("pass number outside requested range")
    conditioning = "fresh" if number == 1 else "findings-fed"
    if receipt.get("conditioning") != conditioning:
        raise ValueError(f"pass {number} must be labelled {conditioning}")
    expected = string_list(receipt, "agents_expected")
    returned = string_list(receipt, "agents_returned")
    string_list(receipt, "limitations")
    if not expected or not set(returned) <= set(expected):
        raise ValueError("expected agents must be nonempty; returned must be their subset")
    rows = receipt.get("findings")
    if not isinstance(rows, list):
        raise ValueError("findings must be a list (empty is allowed)")
    keys = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("finding must be an object")
        key = finding_key(row, manifest)
        if key in keys:
            raise ValueError("duplicate identity within pass; split distinct mechanisms")
        keys.add(key)
        if row.get("key", key) != key:
            raise ValueError("stored finding key does not match its identity")
        row["key"] = key
        if row.get("kind") not in {"FINDING", "LEAD"} or row.get("disposition") not in DISPOSITIONS:
            raise ValueError("invalid kind or disposition")
        if row["kind"] == "LEAD" and row["disposition"] == "accepted":
            raise ValueError("a LEAD cannot be accepted as a validated finding")
        if not isinstance(row.get("markdown"), str) or not row["markdown"].strip():
            raise ValueError("finding requires its complete Markdown block")


def record_pass(args) -> None:
    with scan_lock(args.scan.resolve(strict=True)):
        _record_pass(args)


def _record_pass(args) -> None:
    scan = args.scan.resolve(strict=True)
    manifest = read_json(scan / "manifest.json")
    check_sources(manifest)
    receipt = read_json(args.input)
    validate_receipt(receipt, manifest)
    number = receipt["pass"]
    if number > 1 and not (scan / f"pass-{number - 1}.json").is_file():
        raise ValueError("record passes sequentially after all prior agents stop")
    receipt["source_commit"] = manifest["source_commit"]
    receipt["scope_sha256"] = manifest["scope_sha256"]
    out = scan / f"pass-{number}.json"
    if out.exists():
        if read_json(out) != receipt:
            raise ValueError("pass receipt is immutable; start a new scan for corrections")
        return  # Idempotent retry, never double count.
    if (scan / "summary.json").exists():
        raise ValueError("scan already assembled; record further work in a new scan")
    write_json(out, receipt)


def assemble(args) -> None:
    # Always acquire scan lock before target memory lock; never reverse order.
    with scan_lock(args.scan.resolve(strict=True)):
        _assemble(args)


def _assemble(args) -> None:
    scan = args.scan.resolve(strict=True)
    manifest = read_json(scan / "manifest.json")
    receipts = []
    for number in range(1, manifest["passes_requested"] + 1):
        path = scan / f"pass-{number}.json"
        if path.is_file():
            receipt = read_json(path)
            if receipt.get("pass") != number:
                raise ValueError("receipt pass number differs from its filename")
            receipts.append(receipt)
    if not receipts:
        raise ValueError("no completed pass receipt; cannot assemble a report")
    for receipt in receipts:
        validate_receipt(receipt, manifest)
        if (receipt.get("source_commit") != manifest["source_commit"]
                or receipt.get("scope_sha256") != manifest["scope_sha256"]):
            raise ValueError("receipt source/scope identity differs from its manifest")
    before = load_memory(scan / "memory-before.json") if manifest["memory_enabled"] else empty_memory()
    groups: dict[str, list[tuple[int, dict]]] = {}
    lines = ["# Audit pass appendix", "", f"Source revision: `{manifest['source_commit']}`",
             f"Scope content SHA256: `{manifest['scope_sha256']}`",
             f"DewaxGuard: {manifest['skill_version']}", "",
             "Pass counts describe repeated observations, not proof or independent stability.", "",
             "| Pass | Conditioning | Agents returned | Missing agents |",
             "| --- | --- | --- | --- |"]
    for receipt in receipts:
        missing = sorted(set(receipt["agents_expected"]) - set(receipt["agents_returned"]))
        lines.append(f"| {receipt['pass']} | {receipt['conditioning']} | "
                     f"{len(receipt['agents_returned'])}/{len(receipt['agents_expected'])} | "
                     f"{', '.join(missing) or 'none'} |")
        for row in receipt["findings"]:
            groups.setdefault(row["key"], []).append((receipt["pass"], row))
    recorded = {r["pass"] for r in receipts}
    missing_passes = sorted(set(range(1, manifest["passes_requested"] + 1)) - recorded)
    lines += ["", f"Requested passes without receipts: {missing_passes or 'none'}.",
              "", "## Observations (all dispositions retained)", ""]
    summary = {"schema_version": 1, "passes_requested": manifest["passes_requested"],
               "passes_recorded": sorted(recorded), "passes_missing": missing_passes, "observations": []}
    for key, occurrences in groups.items():
        prior = before["records"].get(key)
        history = (f"KNOWN: {len(prior['scans'])} earlier scan(s) at snapshot time"
                   if prior else "NEW at scan start") if manifest["memory_enabled"] else "Memory disabled"
        stale = bool(prior and (prior["last_source_commit"] != manifest["source_commit"]
                              or prior["last_scope_sha256"] != manifest["scope_sha256"]))
        variants = []
        for number, row in occurrences:
            variant = (row["kind"], row["disposition"], row["markdown"])
            if variant not in variants:
                variants.append(variant)
        dispositions = sorted({row["disposition"] for _, row in occurrences})
        summary["observations"].append({"key": key, "passes_seen": [n for n, _ in occurrences],
                                        "history": history, "prior_context_changed": stale,
                                        "dispositions": dispositions, "variants": len(variants)})
        lines += [f"### {occurrences[0][1]['contract']}.{occurrences[0][1]['function']}", "",
                  f"Identity: `{key}`. {history}. Seen in {len(occurrences)}/{len(receipts)} recorded passes.", ""]
        if stale:
            lines += ["Prior source or scope differs; historical evidence needs revalidation.", ""]
        if len(dispositions) > 1:
            lines += ["Dispositions conflict across passes; resolve with source evidence before final promotion.", ""]
        for kind, disposition, markdown in variants:
            lines += [f"Recorded as {kind} / {disposition}:", "", markdown, ""]
    lines += ["## Limitations", ""]
    for receipt in receipts:
        lines += [f"- Pass {receipt['pass']}: {value}" for value in receipt["limitations"]]
    lines += ["", "A prior finding absent here is not proved fixed. A quiet pass is not a safety verdict.", ""]
    # Persist the appendix before the ledger; failure cannot leave history without artifacts.
    write_text(scan / "pass-appendix.md", "\n".join(lines))
    write_json(scan / "summary.json", summary)
    if manifest["memory_enabled"]:
        lock = scan.parent / ".memory-lock"
        lock.mkdir()  # Fail closed on concurrent ledger writers; retry after owner finishes.
        try:
            ledger_path = scan.parent / "memory.json"
            ledger = load_memory(ledger_path)
            scan_id = manifest["scan_id"]
            if scan_id not in ledger["scans"]:
                for key, occurrences in groups.items():
                    row = occurrences[-1][1]
                    item = ledger["records"].setdefault(key, {"identity": {f: row[f] for f in IDENTITY_FIELDS}, "scans": []})
                    item["scans"].append(scan_id)
                    item["last_source_commit"] = manifest["source_commit"]
                    item["last_scope_sha256"] = manifest["scope_sha256"]
                ledger["scans"].append(scan_id)
                write_json(ledger_path, ledger)
        finally:
            lock.rmdir()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="freeze source/scope and optional prior memory")
    init.add_argument("--project-root", type=Path, required=True)
    init.add_argument("--workspace", type=Path, required=True)
    init.add_argument("--target-id", required=True)
    init.add_argument("--scan-id", required=True)
    init.add_argument("--source-commit", required=True)
    init.add_argument("--scope-file", type=Path, required=True)
    init.add_argument("--passes", type=int, default=1)
    init.add_argument("--memory", action="store_true")
    record = commands.add_parser("record", help="persist an immutable completed-pass receipt")
    record.add_argument("--scan", type=Path, required=True)
    record.add_argument("--input", type=Path, required=True)
    report = commands.add_parser("assemble", help="assemble saved observations without rewriting them")
    report.add_argument("--scan", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "init":
            print(init_scan(args))
        elif args.command == "record":
            record_pass(args)
        else:
            assemble(args)
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"scan_records: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
