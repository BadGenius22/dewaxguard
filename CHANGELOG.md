# DewaxGuard Changelog

## [1.8.0] - 2026-05-04

**Origin**: Cross-pollination from cosminmarian53/skills `soroban-auditor` (commit 2 of 2). Deterministic recon-artifact builder + Rust source squeezer. Builds on the v1.7.0 prompt-only guards by giving them concrete artifacts to consume.

### Added

- **`scripts/build_recon_maps.sh`** — multi-language deterministic recon preprocessor. Runs in Phase 1.0 (BEFORE recon agents spawn) and emits 11 stable greppable artifacts under `$SCRATCHPAD`:
  - `guard-map.md`, `state-flags.md`, `integration-map.md`, `math-map.md`, `unsafe-map.md`, `logic-anomaly-map.md`, `blackhat-maps.md`, `divergence-map.md` (curated near-twin pairs diffed via `difflib.unified_diff`), `invariant-extract.md` (harvested from `fuzz/invariants.*`).
  - `docs-intent-map.md` (consumed by Phase 5d Gate 1a — see `rules/docs-intent-map.md`).
  - `auth-critical-files.txt` (consumed by the squeezer and by every agent claiming missing-auth — see `rules/auth-critical-files.md`).

  Per-language pattern banks for `evm` / `solana` / `stellar` / `aptos` / `sui` / `cpp`. Curated divergence pairs per language (e.g. lending: `supply` vs `supply_on_behalf`, `liquidation_call` vs `internal_liquidation_call`, `flash_loan` vs `flash_loan_simple`). Repo-augmentable via `$OUT/divergence-pairs.txt`.

  **Validation**: smoke-tested against the K2 audit codebase (Stellar Soroban, ~15K SLoC). Produced 252 guard-map entries, 488 state-flags, 1005 integration sites, 351 math sites, 808 pub-fn signatures, 23 auth-critical files, and 921 invariant lines — empty unsafe-map (correctly, Soroban has no unsafe surface). Total recon-stage tokens emitted to disk in <1s.

- **`scripts/squeezers/squeezer_rust.py`** — Rust source minifier ported (with attribution) from cosminmarian53/skills `soroban_token_squeezer.py` (MIT). Generalizes from Soroban-only to Anchor and native Solana — the brace-counter/string-escape logic is language-feature-agnostic Rust. Modes: `--collapse-bodies` (replace each `fn ... { body }` with `{ ... }`, brace-counted, respects strings/chars/raw strings/comments), `--numbered` (line numbers post-minification), `--keep-full F,G` (substring allowlist that bypasses collapse for auth-critical files). Emits `[full-bodies]` / `[collapsed]` tags per file consumed by `rules/auth-critical-files.md`.

  **Validation**: smoke-tested on K2's `kinetic-router/src/admin.rs` (6,844 bytes uncollapsed → 2,167 bytes collapsed = ~68% reduction). Allowlist correctly preserves bodies of `admin.rs`, `access_control.rs`, `token/src/contract.rs`, etc.

### Changed

- **`SKILL.md` Phase 1** — split into Phase 1.0 (deterministic preprocessors, run BEFORE agents) + Phase 1.1 (4 recon agents, run AFTER preprocessors). Recon Agent 1B and Agent 3 now augment the pre-built artifacts rather than emitting them from scratch — same end state, much faster, deterministic.
- **`SKILL.md` file-structure listing** — adds the `scripts/` tree.
- **`README.md`** — adds a "Recon scripts (v1.7.0)" section showing the standard invocation; adds upstream attribution under "Methodology Sources".

### Why this release matters

The v1.7.0 prompt-only rules created mandatory validator fields (`docs_intent_check`, `auth_check`, `severity_check`) but agents had to re-grep the docs/auth surface every time. v1.8.0 ships the deterministic preprocessor that emits the source-of-truth artifacts ONCE, and every downstream agent reads from them.

Token budget impact (measured on K2 stellar smoke test):
- Without preprocessor: each of 8 breadth agents would re-grep `require_auth` across 95 `.rs` files = 8× the same work.
- With preprocessor: one bash pass produces `guard-map.md` (252 lines) consumed by all 8 agents.

False-positive impact: the squeezer's `[full-bodies]` / `[collapsed]` tags categorically prevent the body-collapse hallucination class. Findings alleging missing-auth on a `[collapsed]` file MUST Read the body or DOWNGRADE to LEAD per `rules/auth-critical-files.md`.

### Compatibility

The preprocessor is OPTIONAL — the skill works without it (agents fall back to direct grep). When run, it merely accelerates and stabilizes the recon stage. To skip, omit Phase 1.0; the validator falls back to grep-time docs-intent checks. To keep the FP guards but skip the squeezer, run only `build_recon_maps.sh` and let agents Read source files directly.

---

## [1.7.0] - 2026-05-04

**Origin**: Cross-pollination from cosminmarian53/skills `soroban-auditor` (commit 1 of 2). Prompt-only false-positive guards. Zero new agents, zero new scripts — pure rule additions and prompt edits.

### Added

- **`rules/docs-intent-map.md`** — pre-extracted "by design / intentional / accepted trade-off / out of scope / known limitation / expected behavior" signals from project docs, emitted by Recon Agent 1B. Phase 5d Gate 1a (Refutation) hard-fails any finding without a populated `docs_intent_check:` field. Prevents the entire FP class where agents file findings on documented behavior and the validator manually re-rejects them at submission time. Source artifact: `{SCRATCHPAD}/docs-intent-map.md`.
- **`rules/severity-decision-tree.md`** — 3-question ordered tree applied at Phase 5d Gate 4a. The first YES determines severity: (a) directly stolen/lost/locked → HIGH; (b) core function broken / liveness / compounding accounting drift → MEDIUM; (c) else → LOW/QA. Findings whose claimed severity exceeds the tree result get a 10-30 point deduction in the bug-validator score. Replaces ad-hoc severity reasoning with a defensible mechanical procedure.
- **`rules/auth-critical-files.md`** — allowlist of files (admin/access-control/auth/emergency/upgrade/governance/multisig substrings + per-language entry-point lists) whose bodies MUST be emitted in full by any future squeezed/skeleton bundle. Pairs with the new `auth_check:` field requirement: findings alleging missing auth must record whether they read the actual body (`SAW_FULL_BODY` / `SAW_GUARD` / `SKELETON_ONLY`). Prevents the high-volume "missing require_auth" hallucination produced when a body-collapsing preprocessor hides the guard. Recon Agent 3 emits `{SCRATCHPAD}/auth-critical-files.txt` per audit.
- **`rules/agent-tool-budgets.md`** — per-agent Read/Grep caps (e.g. vector-scan 4/6, access-control 5/6, depth-token-flow 8/6, bug-validator 12/8). Halved in `light` mode, +50% on depth/validator in `thorough` mode. Mandatory greps (e.g. access-control → `guard-map.md`, validator → `docs-intent-map.md`) count against budget but cannot be skipped. Agents end every output with a `budget:` receipt; over-budget hypotheses convert to LEADs flagged `tool_budget_exhausted: true` for follow-up by depth or validator phases.

### Changed

- **`rules/finding-output-format.md`** — `verified:` field is now MANDATORY for every FINDING (not LEADs). Must paste the actual ±2 lines from the source around the cited bug location. No paste = auto-reject by the validator harness. Three additional fields added that Phase 5d populates: `docs_intent_check:`, `severity_check:`, `auth_check:`.
- **`agents/hacking-agents/shared-rules.md`** — added the `verified:` requirement, the tool-budget rule, the auth-critical-file rule, and an extended FINDING/LEAD output template that includes `verified:`, `tool_budget_exhausted:`, and the `budget:` receipt line.
- **`SKILL.md`** Phase 1 Recon — Agent 1B now MUST emit `docs-intent-map.md`; Agent 3 now MUST emit `auth-critical-files.txt`. Phase 5d Validation Pipeline — Gate 1 split into 1a (docs-intent) + 1b (auth-check); Gate 4 gains 4a (severity decision tree). File-structure listing updated to reflect the four new rules files.

### Why this release matters

`soroban-auditor` (Pashov-fork by cosminmarian53) ships four mechanical FP guards that dewaxguard previously handled in prompt-space (variable, agent-by-agent). Codifying them as rules + mandatory validator fields means:

- Documented "by design" behavior is rejected at validation time, not at submission time — saves judging cycles.
- Severity reasoning produces an audit trail (`severity_check: a=NO, b=YES → MEDIUM`) instead of an opinion.
- Body-collapse hallucinations are categorically prevented for auth-critical files instead of relying on per-agent vigilance.
- Tool-budget receipts let the orchestrator detect both under-spending (cautious agents) and over-spending (loose prompts) systematically.

These are all prompt/rule changes. Commit 2 (next) ports the deterministic recon-map builder script and the Rust source squeezer that consume the artifacts.

---

## [1.6.0] - 2026-04-30

**Validated in**: Monetrix audit (Code4rena, April 24 – May 4, 2026)

### Added

- **M-22: Hypothesis Pre-Declaration with Falsifiable Verdict Tracking** (`methodology/M22-hypothesis-pre-declaration.md`). Per-domain pre-declared `H{domain}.{n}` hypotheses BEFORE breadth agents spawn. Agents verdict CONFIRMED/PARTIAL/REFUTED against a closed set instead of open-ended discovery. Validated across Domains 11/12/13/14 of the Monetrix audit: 2 breadth agents per domain achieved same coverage as 8-agent open-ended breadth (~75% budget reduction, no recall loss). Refutations flow systematically into R-N manifest deltas. Cross-language: EVM/Solana/Move/C++.
- **C4 Submission Format Rules** in `references/criteria/c4-competitive.md`. Codifies Code4rena's "one QA report per audit" + "all low-severity AND governance/centralization findings → QA-Bundle" rule as a mechanical routing matrix. Misrouting governance/centralization findings to separate Medium slots risks AI-4 invalidation; routing to QA-Bundle preserves QA points. Includes trigger heuristic for "governance/centralization-class" findings and pre-submission consolidation gate.
- **SKILL.md Phase 5d Gate 4.5 — Submission-Slot Routing**. New sub-step after the 4-gate validation pipeline. Applies platform-specific submission format rules before writing findings to their severity slots. For Code4rena: routes governance/centralization-class findings to QA-Bundle as L-N entries instead of separate Medium files.

### Validated outcomes (Monetrix April 2026)

- M-22 ran on Domains 11-14 → 0 false positives, all hypotheses verdicted, ~30-40% total audit-time savings vs open-ended discovery on prior domains
- C4 Submission Format Rules caught the `setRedeemEscrow` rotation routing risk before submission → finding folded into QA-Bundle as L-03 instead of submitted as borderline-AI-4 Medium
- Phase 5d Gate 4.5 + bug-validator integration produced final submission state aligned with Code4rena one-bundle rule

### Why this release matters

The M-22 + C4-format-rule pair fixes a class of audit bloat where multiple borderline-Medium governance findings get submitted as separate files, then collapse to QA at judging — losing per-finding judging cycles and risking sponsor-side dismissal as severity-inflation. The fix is mechanical (routing matrix) not judgmental.

---

## [1.5.0] - 2026-04-26
- **M-21 Cross-Agent Contradiction Protocol** (NEW, methodology/M21-...md): always-on merge-step protocol for multi-reviewer pipelines. When 2+ reviewers disagree on the same code surface, OR a lone-flagger surfaces a finding the others missed, mandatory source-code arbitration at the merge step (4-step protocol). Generalizes the M-18 Phase-3 sub-rule into a stand-alone always-on protocol independent of any matrix domain.
- **Validated origin**: XRPL Sherlock April 2026 audit. M-21 alone produced L-35 — the **3rd reward-pool hit (XLS-0075 Permission Delegation)** that all 7 other breadth agents missed. Without M-21 the audit would have shipped 2 of 5 reward pools instead of 3. Independently re-validated against majority-refute in Domain 18 ECS18-1.
- **M-19 Path-Selection Determinism × Economic-Asymmetry Matrix** (NEW): 35-cell breadth scaffold for path-finder / route-selection / DEX-aggregator audits. 7 determinism dimensions (D1-D7) × 10 economic-asymmetry dimensions (E1-E10). Cross-language: Uniswap V3 SmartOrderRouter, 1inch Pathfinder, Jupiter, Orca, DeepBook, PancakeSwap. Validated origin: XRPL Domain 21 (Pathfinder × MPT) — surfaced L-34.
- **M-20 Wire-Format Mature-Layer Audit Matrix** (NEW): 4-dimension verdict per type-codec cell (parse-time validation / template completeness / cross-codec consistency / fuzz-coverage). Includes orphan-public-API filter and convergence-on-informational handling. Cross-language: Bitcoin CTransaction consensus rules, Ethereum RLP, Solana borsh, Cosmos protobuf PROTO3 LAST-WINS, Sui/Aptos BCS. Validated origin: XRPL Domain 20 (Binary Serialization / Canonical-Form Attacks) — 35/35 NEW SFields PASS unanimously across 7 of 8 agents.
- **rules/cross-class-preflight-firewall.md** (NEW): defensive-pattern rule. When a system has multiple authority classes (delegate / sponsor / pseudo-account / admin / governance), each must be validated at preflight before reaching transactor-specific logic. Sibling-transactor cross-comparison test for finding-class detection.
- **platform-quirks/cpp.md** (UPDATED): new section "🚨 #12 — Delta-Scope Contest Validity Rules" capturing T-06 (pre-existing-with-unchanged-impact = OOS), T-13 (grief-floor cap at Low), and amendment-gating reachability. Cross-platform mapping for Cosmos SDK upgrades, EVM proxy upgrades, Solana program upgrades.
- **methodology/INDEX.md** (UPDATED): M-19/M-20/M-21 entries added; "How to use" extended with merge-step rule (apply M-21); "Per-audit high-yield template" extended with M-21/M-19/M-20 specific guidance.
- **Audit metrics from validation source**: XRPL April 2026 ran 12 of 21 domains via /dewaxguard thorough; surfaced 4 Medium + 5 Low submittables; covered 3 of 5 Sherlock reward pools (Sponsored Fees, MPT DEX, Confidential MPT + Permission Delegation via L-35).

## [1.4.0] - 2026-04-12
- Added Phase 4b.5 RAG Validation Sweep: every finding validated against Solodit database via unified-vuln-db MCP tools
- Primary tools: validate_hypothesis, search_solodit_live (historical precedent lookup)
- Fallback chain: get_similar_findings → get_common_vulnerabilities → WebSearch (site:solodit.xyz)
- RAG score feeds into bug validator (Phase 5d) confidence axis and Phase 5d.1 submission hardening
- Recon Agent 1A now probes MCP tool availability and sets RAG_TOOLS_AVAILABLE flag
- Floor score 0.3 if all tools fail — preserves pipeline progress on tool errors
- New file: rules/rag-validation-sweep.md (full spec)

## [1.3.0] - 2026-04-12
- Added Inconsistency Scanner: depth/breadth agents grep codebase for correct pattern used elsewhere (shared-rules.md)
- Added Platform Threshold Enforcement: mandatory quantification rules per platform in report-template.md
- Added Trust Boundary Mapping: meta-tx/relay role analysis in access-control-agent.md
- Added Caller-Controlled Callback Tracing: attacker-supplied target trace in execution-trace-agent.md
- Added Submission Hardening Pass (Phase 5d.1): feedback loop from bug validator to fix deductions before report
- First audit metrics: Superfluid ClearMacro (EVM), 2M found, both scored >90 after hardening

## [1.2.0] - 2026-04-12
- Added self-calibration: Phase 5e auto-analyzes agent FP rates, confidence accuracy after every audit
- Added batch import: `/dewaxguard batch-import` processes multiple public contest results in one session
- Added benchmark suite: `/dewaxguard benchmark` runs pipeline against known-vulnerable contracts for regression testing
- Added 6 starter benchmarks: EVM (reentrancy, share-inflation, unchecked-return), Solana (missing-signer, pda-substitution), Sui (shared-object-race)
- Each benchmark includes false-positive traps to test precision alongside recall

## [1.1.0] - 2026-04-12
- Added self-improvement system: `/dewaxguard improve` and `/dewaxguard consolidate`
- Added MEMORY.md metrics ledger
- Added CHANGELOG.md version history
- Added YAML frontmatter for Claude Code skill compatibility

## [1.0.0] - 2026-04-12
- Initial release: 8 hacking agents, Nemesis cross-feed, depth analysis, fork PoC, bug validator
- Multi-language support: EVM, Solana, Aptos, Sui
- Platform-specific validation: Code4rena, Sherlock, Cantina, Immunefi
