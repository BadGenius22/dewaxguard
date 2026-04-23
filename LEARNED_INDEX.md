# Learned Audit Index

> One line per completed audit. Each entry points to the distilled knowledge that enriched the skill.

## Format

```
- {DATE} | {CHAIN / CONTEST} | {N Mediums + N Highs + ... submitted} | {pointers to enriched files}
```

## Entries

- **2026-04-18** | XRPL Sherlock (C++/rippled) — initial 7-domain sweep | **5 Mediums drafted** (ESC-1/2/3 + CONF-1 + DEL-1) across **3 of 5 reward pools** | Added **8 methodology templates** (M-03/04/07/08/09/10/11/12), **5 pattern case studies** in `patterns/xrpl-2026-04/`, full Sherlock contest template bundle in `contest/sherlock/`. ⚠️ SEE 2026-04-23 ENTRY for DEL-1 OOS correction.
- **2026-04-23** | XRPL Sherlock (C++/rippled) — Domains 8-14 complete + kuprum dedup | **4 Mediums submission-ready** (ESC-1/2/3 + CONF-1) across **2 of 5 reward pools** (MPT DEX + Confidential MPT) after **DEL-1 reclassified OOS as duplicate of public issue #6890** (created 22.5h before contest start, discovered via M-13 kuprum index ingestion). Remaining pools: Batch + Sponsored Fees cleared; Permission Delegation lost (DEL-1 was the hit). **2 Low findings drafted** (L-30 PathRequest missing-else, L-31 accountDestAssets MPT asymmetry — both XLS-0082 / MPT DEX, unique vs kuprum). **1 Low candidate held** (L-32 account_objects sponsored pagination — XLS-0068, risky per M-14 unchanged-legacy). Added **2 new methodology templates** (M-13 kuprum-ingestion, M-14 elevated-impact-vs-unchanged-legacy), **3 new pattern case studies** (L-30/L-31/L-32), **OOS annotation** on DEL-1 pattern. XRPL-specific manifest grew to F-01..F-35, R-01..R-68, D-01..D-30, L-01..L-32, M-01..M-14. Key new insight: **ingest kuprum-style 3rd-party known-issue indices in the first 48h of ANY competitive audit** — M-13 saves weeks of wasted work.

## Growth protocol

After every audit:
1. **Promote generalizable methodology** to `methodology/` — anything M-xx that applies cross-language.
2. **Archive per-finding case studies** to `patterns/{chain}-{date}/` — one file per submitted finding.
3. **Enrich platform-quirks** for the audited language.
4. **Add contest-specific templates** to `contest/{platform}/` if the audit revealed new rules.
5. **Append one line here** summarizing what was added.
6. **Commit + push** the skill repo to `BadGenius22/dewaxguard` GitHub for cross-machine portability.

## Methodology maturity tracking

Each methodology template in `methodology/` should list its validated findings in its "Validated findings" section. Re-validation across multiple audits strengthens confidence.

As of 2026-04-23:
- **M-03** inverse-trust: **4 validations** (XRPL ESC-1/2/3 + CONF-1; DEL-1 was validation #5 but reclassified OOS)
- **M-04** feature-pool-coverage: 2 validations (XRPL ESC-1, ESC-3)
- **M-07** post-finding-sweep: 1 validation (XRPL L-14 → ESC-3)
- **M-08** holder-plants-trap: **4 of 4 submittable Mediums — still highest-yield template** (DEL-1 was M-08-adjacent; M-12 is the true DEL-1 template)
- **M-09** SYNC_GAP: 1 validation (XRPL CONF-1)
- **M-10** prior-audit-dedup: 1 validation (XRPL submission prep) + now **extended** to kuprum-style indices per M-13
- **M-11** retired-amendment-feasibility: 1 save (XRPL SPON-M1 correctly NOT submitted)
- **M-12** granular-sandbox: 1 validation (XRPL DEL-1) — template still validated even though DEL-1 was OOS'd by kuprum dedup (another researcher reached the same conclusion)
- **M-13** kuprum-index-ingestion: **1 major save** (XRPL DEL-1 OOS caught before submission — without M-13, would have been a rejected Sherlock submission)
- **M-14** elevated-impact-vs-unchanged-legacy: 1 contested case (XRPL L-32 held pending user decision)

## High-yield summary (for first-pass audits)

Start with M-08 on every privileged operation. Follow with M-09 on every aggregate counter. If the contest has per-feature reward pools, run M-12 on granular permissions. Pre-submission: M-04 + M-10 + M-11.

## Cross-language applicability

All 8 methodology templates are chain-agnostic in the abstract pattern; only the syntactic triggers change. Primary mappings:

| Template | EVM | Solana | Move | Soroban | XRPL |
|----------|-----|--------|------|---------|------|
| M-03 inverse-trust | compliance roles | authority-gated ops | capability issuers | admin/authority | issuer compliance |
| M-08 holder-plants-trap | wrapper contracts | PDA escrows | coin wrappers | claimable balances | uncancellable escrows |
| M-09 SYNC_GAP | totalSupply vs balanceOf | mint.supply vs ATAs | aggregator vs resources | TTL counters | MPT counters vs fields |
| M-11 retired-feasibility | post-hardfork | retired instructions | deprecated modules | — | retired amendments |
| M-12 granular-sandbox | AccessControl + hooks | Anchor access_control | Capability types | fine-grained auth | checkGranularSemantics |
