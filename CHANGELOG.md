# DewaxGuard Changelog

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
