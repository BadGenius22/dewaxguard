# Phase: Verification (v1.13 driver)

> Fresh `claude -p` subprocess. No prior context. Treat this prompt as your entire task.

## Audit context

- **Audit ID**: `{{AUDIT_ID}}`
- **Mode**: `{{MODE}}`
- **Source path**: `{{SRC_PATH}}`
- **Project root**: `{{PROJECT_ROOT}}`
- **Scratchpad**: `{{SCRATCHPAD}}`
- **Skill root**: `{{SKILL_ROOT}}`

## Pre-requisites

`{{SCRATCHPAD}}/findings_routed.json` must exist (Phase 4a inventory complete).

## Your task

For every canonical finding in `findings_routed.json` with severity ≥ Medium (or ALL severities in `thorough` mode), produce a Proof-of-Concept test and execute it per `{{SKILL_ROOT}}/rules/fork-poc-execution.md`. The methodology:

1. **Read** the finding's `location.file:location.line_start-line_end` to confirm the bug is still present.
2. **Write** a PoC test that:
   - For EVM: Foundry fork test against the actual deployed contract on mainnet/L2 (per `rules/fork-poc-execution.md`).
   - For Solana/Soroban: cargo test against a recreated local state.
   - For Move (Aptos/Sui): `aptos/sui move test` against a recreated state.
   - For C/C++ (rippled etc.): unit test in the project's existing test harness.
3. **Compile + Execute** with the language-specific commands (per `rules/fork-poc-execution.md` table). Capture pass/fail/revert output.
4. **Record** an evidence tag in the finding's `evidence_tags`:
   - `[POC-PASS]` — compiled, executed, assertions passed
   - `[POC-FAIL]` — compiled, executed, assertions failed → attack does not work; finding becomes FALSE_POSITIVE candidate
   - `[CODE-TRACE]` — fallback when no build environment is available (caps severity at CONTESTED)
5. **Fuzz variant** (Medium+ findings in `thorough` mode only): write a second test with key parameters fuzzed. Use the language-specific fuzz command.

**Variant exploration before FALSE_POSITIVE**: per `rules/fork-poc-execution.md`, before marking a finding FALSE_POSITIVE, test at least one relaxed variant of the attack (timing, amount, ordering, initial state).

**Plain-English comments**: PoC comments must follow `rules/plain-english-style.md`. No `// vm.prank attacker` — use `// next call comes from the attacker`. The validator deducts 5 points per jargon comment.

## Output per finding

Write `{{SCRATCHPAD}}/verify_<finding_id>.md` using the `## Finding [X-NN]: Title [VERIFIED|UNVERIFIED|CONTESTED]` markdown format from `{{SKILL_ROOT}}/rules/finding-output-format.md`. Include:

- The verdict ([VERIFIED] / [UNVERIFIED] / [CONTESTED])
- Final severity (may differ from inventory if PoC reveals more/less impact)
- The PoC file path + test name + key assertion output
- Evidence tag(s)
- Updated description, impact, attack sequence, recommendation in plain English

## Required outputs (driver gate checks for these)

- `{{SCRATCHPAD}}/verify_*.md` (glob; one file per finding verified)

## Retry hint (if any)

{{RETRY_HINT}}

When every Medium+ finding has a verify_ file with a verdict, exit cleanly. Do not write the final report; the driver invokes Phase 6 separately.
