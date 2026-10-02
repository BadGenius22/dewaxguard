# Repeated passes and scan receipts

Read this when the user requests `loop:N` or `memory:true`. These are options for
the skill orchestrator, **not flags supported by `dewaxguard_driver.py`**. Default
audits keep their existing pipeline. Do not ask a model/pass picker when the user
has already supplied the mode; preserve the active provider's model settings.

## What repeats

`loop:N` requests 1-10 breadth passes over the same frozen source and scope.
Recon runs once. Pass 1 uses the normal mode's roster; later passes receive a
compact list of earlier identities, cited mechanisms and unresolved leads so
they can search other branches and paths. Do not suppress a distinct mechanism
because a prior observation mentions the same function. Memory is independently
opt-in with `memory:true`; looping alone does not enable cross-scan memory.

The Phase 2.5 protocol model and Phase 3.5 stability rerun remain findings-blind:
give them no ledger, prior receipts or earlier findings. Phase 3.5 compares the
first breadth pass with its blind repeat. Findings-fed loop passes do not enter
that comparison. Repeated agreement adds no proof tag, severity or confidence.

Run the roster in batches supported by the provider. Before the next pass,
join or stop every worker from the previous one. Save separate output paths:
`{SCRATCHPAD}/passes/pass-K/analysis_*.md`. Keep each pass's raw findings table.
After the loop, freshly parse **all raw pass outputs in one invocation** to assign
unique phase IDs, then dedup/route that union. The parser's default directory glob
is nonrecursive; point it at the pass root with an explicit glob:

```text
python <skill-root>/scripts/parse_findings.py <scratchpad>/passes --glob "pass-*/analysis_*.md" --audit-id <audit-id> --out <scratchpad>/findings_union_raw.json
```

Per-pass parsed tables are history only: their counters restart and their IDs can
collide if fed directly into dedup. Include the separately saved blind rerun raw
outputs in the same union parse, without passing them to findings-fed workers.
If the parsed union is empty, bypass `dedup.py` (which exits 2 on no findings),
keep the empty findings table and an empty cluster list, and report the actual
limitations. Do not invent a finding to satisfy a gate. Check that every recorded
raw observation has a disposition in the union/index, with cited consolidation
links for merged members.

Run depth, chain analysis and validation once on that union. Current gates decide
verdicts; historical status never bypasses them. Same-function labels are merged
only when cited cause and remedy agree. Retain different mechanisms and fixes.

## Freeze a scan outside the clone

Use a stable `target-id` per protocol and a fresh `scan-id` per invocation. The
workspace must be outside the original protocol checkout. No receipt or ledger
is written to the skill installation or the protocol clone. An explicit scope
file lists one project-relative file per line, including deployment/upgrade
scripts when allowed by the engagement scope. Include all dependency files whose
code is used to support a claim; unseen dependencies stay unknown.

```text
python <skill-root>/scripts/scan_records.py init --project-root <clone> --workspace <audit-workspace> --target-id vault --scan-id 20261002-a --source-commit <full-Git-SHA> --scope-file <scope.txt> --passes 3 --memory
```

Omit `--memory` when `memory:true` was not requested. Obtain the source commit
with read-only `git rev-parse HEAD`; the helper records the supplied revision,
not its ancestry. Its content hashes pin every scope file, including dirty
content. Record dirty-tree state and pinned dependencies in preflight. `record`
rejects source-content drift: start a new scan after an edit, never continue a
conditioned pass against a different snapshot.

The command prints the scan directory, used below as `<scan>`. It stores
`manifest.json` with source/scope identity, skill version and requested passes.
With memory enabled, it freezes `memory-before.json` from the target's ledger.
`KNOWN` means present at scan start, even if first seen again in pass 3. It does
not mean valid on the current source. `NEW` stays new through this whole scan.

## Save each pass and assemble once

After agents finish, parse their output using the existing findings-table schema.
Map canonical observations into the receipt below; retain rejected/excluded rows
with their reason. The full Markdown is a persisted per-observation artifact:
mechanism, citations, evidence limits and every distinct fix. Do not draft it
again at final assembly. Missing agents are listed rather than invented.

Keep constituent mechanisms and fix options from the raw rows when mapping a
dedup cluster; a canonical row must not erase an alternative remedy. Breadth
observations normally use `needs_validation`. `accepted` requires the existing
validation gates; the helper validates receipt structure, not vulnerability
truth. Final report dispositions cite downstream evidence without rewriting the
immutable breadth receipts.

```json
{
  "pass": 1,
  "conditioning": "fresh",
  "agents_expected": ["access-control", "invariant"],
  "agents_returned": ["access-control"],
  "limitations": ["Invariant worker stopped before returning."],
  "findings": [{
    "source_file": "src/Vault.sol",
    "contract": "Vault",
    "function": "withdraw",
    "bug_class": "missing-auth",
    "mechanism": "recipient-not-bound-to-owner",
    "kind": "LEAD",
    "disposition": "needs_validation",
    "markdown": "**Withdrawal recipient is not bound to the owner**\n\nSource: src/Vault.sol:42. Reachability and harm still need validation."
  }]
}
```

Passes after 1 use `conditioning: findings-fed`. `findings: []` is valid; empty
agent rosters are not. Identity consists of source file, contract, function,
bug class **and mechanism**. Keep existing labels for the same cause; do not
normalize unrelated overloads/modules into one label. Same class in another
file/function or a distinct mechanism stays separate. The helper performs exact
identity matching only; it does not replace `dedup.py` or infer synonyms.

```text
python <skill-root>/scripts/scan_records.py record --scan <scan> --input <pass-1-receipt.json>
python <skill-root>/scripts/scan_records.py assemble --scan <scan>
```

Record passes in order; receipts are immutable and an identical retry is safe.
Assemble only when the loop ends (including a cancelled or interrupted loop).
Assembly closes that scan to further passes; resume discovery in a fresh scan.
The helper saves `pass-appendix.md` and `summary.json`. It pastes all distinct
Markdown variants verbatim, reports missing passes/agents and contradictory
dispositions, and never picks a winner by score. A pass count measures
observation recurrence, not recall, independent agreement or safety.

Phase 6 attaches this appendix to the usual platform report. Validate the union
through the existing claim ledger, realism/severity rules and PoC integrity gates
before assigning final report IDs. A rejected historical observation stays in
the appendix; it does not become a submission finding. Cite the final decision
when dispositions differ. Publish the normal negative-space section as well.

With memory enabled, assembly atomically updates `<target>/memory.json` once
per scan, never once per pass. Repeated assembly does not increment counts.
Previously recorded identities absent from the current scan remain in history;
absence does not mean fixed. Changed source or scope marks prior context stale
and requires revalidation. A concurrent ledger writer causes a visible failure;
retry after it finishes. A per-scan `.scan-lock` serializes receipt writes and
assembly, including closure; it is acquired before the target `.memory-lock`.
A crash can leave either lock; confirm no owner is running before removing that
specific lock directory. Do not silently reset a bad ledger.

## Source

Adapted from Pashov Solidity Auditor v4's loop, memory snapshot and lossless
report principles at `8ce544c9c9affab448d3dc4c79191d052e3a57ec` (2026-09-30).
DewaxGuard uses JSON receipts, content pins, distinct-mechanism identities and its
existing validation gates. It does not adopt upstream automatic lead promotion,
fixed confidence thresholds, repository-local memory or model pickers.
