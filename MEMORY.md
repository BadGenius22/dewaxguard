# DewaxGuard Metrics

> One line per post-mortem. No finding details. Max 50 rows before archival.

| Version | Date | Project Type | Language | Recall% | Precision% | RC-SCOPE | RC-METHOD | RC-DEPTH | RC-CONTEXT | RC-AGENT | RC-NOVEL | Reclassified |
|---------|------|-------------|----------|---------|------------|----------|-----------|----------|------------|----------|----------|-------------|
| 1.3.0 | 2026-04-12 | meta-tx forwarder | evm | TBD | TBD | 0 | 1 | 3 | 0 | 0 | 0 | 0 |
| 1.8.0 | 2026-05-05 | aave-v3 lending fork | stellar | TBD | TBD | 0 | 0 | 0 | 0 | 3 | 0 | 1 |

**1.8.0 audit summary** (K2 Code4rena Stellar Soroban): 8 passes / 108 hypotheses → 1 Medium + 9 Lows + 5 Info. 14 of 14 QA-Bundle entries followed consistency-class pattern → validated **M-23**. 2 novel findings via fresh-eyes sweep → validated **M-24**. Manual orchestrator fallback in Pass 7 produced 3 false negatives (HF44 reclassification, HF50 nuance miss, HF51 missed QA-05) → codified **rules/agent-failure-recovery.md**. Project-local realism filter reclassified ~40% of candidate findings → promoted to first-class **rules/realism-filter.md**. RC-AGENT count = 3 (manual orchestrator errors corrected by agent retry). Reclassified count = 1 (HF44 SAFE not unsafe). Yield knee at Pass 6; Pass 7-8 sub-source-level all REFUTED.
