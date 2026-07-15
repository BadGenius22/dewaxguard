# Failure-Mode Database

> **Ships**: Tier 3.9 of `improve/SELF-IMPROVEMENT-PLAN-2026-04.md`.
> **Populated by**: `/dewaxguard improve` Phase E, for every MISSED finding that passes the RC-AGENT Exclusion Test as a fix-eligible root cause (RC-SCOPE / RC-METHOD / RC-DEPTH / RC-CONTEXT).
> **Read at**: session-start preflight (after `refuted/INDEX.md`) — but as a *gap map*, not a hypothesis list.

## What this is and is NOT

This is the **class-level miss ledger**: when a real bug got past the pipeline and the post-mortem proved a methodology/scope/depth/context gap (not an agent reasoning error), one row lands here. Aggregating rows answers the only question that should drive new methodology: *"what class do we systematically miss, in what language, and what fix closed it?"*

It is NOT:
- a finding archive (no titles, no locations, no protocol names that could anchor the next audit — only the generic class + language + root cause + the fix that shipped)
- a place for RC-AGENT or RC-NOVEL misses (those produce no pipeline change; RC-AGENT goes nowhere, RC-NOVEL goes to RAG)
- ever read as "look for THIS bug" — it is read as "this language tree has historically been thin on THIS analysis class; weight it"

## Entry format

One row per fix-eligible miss class. Merge into an existing row when the class+language already exists (bump `count`, append `source`); do not create near-duplicates.

| FM-ID | Vuln class (generic) | Language | Root cause | Fix that shipped | Count | Last seen |
|-------|---------------------|----------|-----------|------------------|-------|-----------|

## Entries

| FM-ID | Vuln class (generic) | Language | Root cause | Fix that shipped | Count | Last seen |
|-------|---------------------|----------|-----------|------------------|-------|-----------|
| FM-01 | signature/auth artifact not bound to the context it authorizes (replay across envelope / on-behalf account) | cpp (consensus node) | RC-METHOD — no template covered signature-binding/domain-separation; attack class absent from a smart-contract-oriented vector library | M-30 (signature-binding/replay audit) + recon detector wired auto-fire on EVM + non-EVM | 1 | 2026-06-04 (Sherlock 1260) |
| FM-02 | composition-correct ZK bundle still forgery-permitting (sound proofs, drainable shared backing) | cpp / zk | RC-DEPTH — M-16 concluded "sound" from composition analysis without an adversarial forgery-construction pass | M-16 Phase 2.7 (adversarial forgery construction: composition-correct ≠ forgery-resistant) | 1 | 2026-06-04 (Sherlock 1260) |
| FM-03 | object/contract teardown grief on shared multi-party state (block AMM/Vault/LoanBroker close) | cpp / cross-lang | RC-DEPTH — M-18 scoped to single-owner AccountDelete only; missed shared-object teardown variant | M-18 broadened to all object-teardown ops + shared-object grief variant | 1 | 2026-06-04 (Sherlock 1260) |
| FM-04 | transfer/CLOB fee rounds to zero → value-escape on small-unit trades | cpp / cross-lang | RC-DEPTH — path-selection matrix lacked a round-to-zero economic-escape dimension | M-19 dimension E11 (round-to-zero fee value-escape) | 1 | 2026-06-04 (Sherlock 1260) |
| FM-05 | breadth layer over-escalates severity +1 tier (auto-Critical on any drainable function) | all | RC-METHOD — no breadth-layer self-calibration; severity set by reflex, corrected only at Phase 5d | shared-rules.md "Severity self-calibration" (derive impact×likelihood, no pre-applied modifiers, sandbag on tie) | 1 | 2026-06-12 (benchmark v1.21.0) |
| FM-06 | audited source not verified against DEPLOYED bytecode; a propagated liveness/scope/guard claim trusted as fact and relayed to a verdict unverified | evm / cross-lang | RC-METHOD — no gate verified in-scope code == deployed code, nor treated a subagent/recon factual claim as a hypothesis to check against the primary source | preflight §1a "Provenance & claim-verification" + fork-poc-execution "Deployed-code provenance" (impl-slot → selector-membership) | 1 | 2026-07-15 (session-lesson) |
| FM-07 | expect-revert PoC artifact: a misplaced `vm.expectRevert` catches a harmless setup call and is read as a live guard-defeat (false POSITIVE; exploit path never ran) | evm | RC-METHOD — variant-relaxation existed for false negatives, but no anti-FP hygiene for misplaced expect-revert | fork-poc-execution §6 arm-then-observe (wrap ONLY the exploit call in try/catch; trace -vvvv) | 1 | 2026-07-15 (session-lesson) |
| FM-08 | share/price-manipulation PoC fails only because the CURRENT economic regime clamps it (single-regime PoC too shallow; attack live in another regime) | evm | RC-DEPTH — PoC methodology tested one regime; clamp-neutralized attacks live in the other | fork-poc-execution §6 both-regime `vm.store` sweep (clamped vs unclamped) | 1 | 2026-07-15 (session-lesson) |
| FM-09 | L2 block-number semantics mismodeled — Arbitrum `block.number` returns the L1 block; timing logic (or the PoC harness via `vm.roll`) reads the wrong clock | evm (L2) | RC-METHOD — no L2 execution-quirk coverage in solidity platform-quirks | platform-quirks/solidity.md §8 (`ArbSys(0x64).arbBlockNumber()` vs `block.number`) | 1 | 2026-07-15 (session-lesson) |

## How aggregation drives the next template

Read this table top-down before deciding "what M-template should I write next?":
- **A class with count ≥ 3 across distinct audits in the same language** → strong RC-METHOD signal; a dedicated template/skill is justified (overrides the RC-NOVEL "wait for 3 occurrences" gate).
- **A class with count ≥ 2 spanning languages** → generalize the fix cross-language (add a cross-language section to the owning M-template; never duplicate per-tree).
- **A language tree with many rows but no benchmark** → that tree is unmeasured AND historically thin; prioritize a `benchmarks/{lang}/` seed (closes the loop with `scripts/run_benchmarks.sh`).
- **A single-count row that has not recurred in 3+ later audits of the same language** → candidate for archival; the fix held, the gap closed.

## Anti-bloat

Cap: 40 rows. When full, archive rows whose fix has held across ≥3 subsequent same-language audits (the gap is closed; the row is history). The database measures *open* systematic gaps, not a permanent monument to every past miss.
