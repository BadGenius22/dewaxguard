# DewaxGuard Changelog

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
