# Learned Audit Index

> One line per completed audit. Each entry points to the distilled knowledge that enriched the skill.

## Format

```
- {DATE} | {CHAIN / CONTEST} | {N Mediums + N Highs + ... submitted} | {pointers to enriched files}
```

## Entries

- **2026-04-18** | XRPL Sherlock (C++/rippled) | **5 Mediums** (ESC-1/2/3 + CONF-1 + DEL-1) across **3 of 5 reward pools** (MPT DEX, Confidential MPT, Permission Delegation), remaining 2 pools cleared (Batch + Sponsored Fees) | Added **8 methodology templates** (M-03/04/07/08/09/10/11/12), **5 pattern case studies** in `patterns/xrpl-2026-04/`, full Sherlock contest template bundle in `contest/sherlock/`. XRPL-specific F-01..F-19, R-01..R-34, D-01..D-21, T-01..T-09, L-01..L-17 preserved in project-local manifest at `audit/2026-04-xrp-ledger-april-2026-BadGenius22/scratchpad/learned/00_MANIFEST.md`. Key new templates: **M-08** (5/5 — highest yield), **M-09 SYNC_GAP**, **M-11** (retired-amendment feasibility — saves from submitting PoC-blocked findings), **M-12 granular permission sandbox** (disproportionate pool-diversification value — unlocked 3rd reward pool via DEL-1).
- **2026-04-24** | XRPL Sherlock (C++/rippled) — Domain 19 full 8-agent breadth (time-based expiry cross-amendment attacks) | **0 new Medium+ submissions from Domain 19 directly**; 1 submittable Low candidate **MP-1** (`EscrowCreate.cpp:411` sponsor-reserve over-restriction, XLS-0068 Sponsored Fees, pending user decision — if submitted alongside L-32 would restore reward pool coverage from 2/5 → 3/5) | Added **M-15 Expiry Race Matrix** methodology template (first cross-language time-gated race methodology). Populated ~46 matrix cells across 9 XRPL SLE types (ltESCROW, ltOFFER, ltCHECK, ltNFTOKEN_OFFER, ltPAYCHAN, ltCREDENTIAL, ltDELEGATE, ltPERMISSIONED_DOMAIN, ltESCROW×Sponsored). Project-local manifest additions (XRPL-specific): F-36 (parentCloseTime per-view invariance), F-37 (CanonicalTXSet ordering), F-38 (trifurcated expiry-semantics taxonomy), R-69 (within-ledger time-gate drift REFUTED), R-70 (cancellable-escrow race reduces to ESC-1/2/3), R-71 (RPC read-only immunizes periphery), D-32 (sponsor-refund-before-erase canonical pattern), D-33 (`checkInsufficientReserve` usage discipline), D-34 (Batch `disabledTxTypes` asymmetric-defense surfaces), T-10 (cancellable-escrow exploits require careless issuer), L-33/L-34/L-35, M-13. Key insight validated: **negative-result methodologies still pay** — even with 0 submittable race findings, the M-15 template structure was validated and 3 new framework facts + 3 refuted classes + 3 defensive patterns tighten the next audit's attack surface map.

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

As of 2026-04-24:
- **M-03** inverse-trust: 5 validations (XRPL ESC-1/2/3 + CONF-1 + DEL-1)
- **M-04** feature-pool-coverage: 2 validations (XRPL ESC-1, ESC-3)
- **M-07** post-finding-sweep: 1 validation (XRPL L-14 → ESC-3)
- **M-08** holder-plants-trap: **5 of 5 Mediums — highest-yield template**
- **M-09** SYNC_GAP: 1 validation (XRPL CONF-1)
- **M-10** prior-audit-dedup: 1 validation (XRPL submission prep)
- **M-11** retired-amendment-feasibility: 1 save (XRPL SPON-M1 correctly NOT submitted)
- **M-12** granular-sandbox: 1 validation (XRPL DEL-1) — first Permission Delegation pool hit
- **M-15** Expiry Race Matrix: 1 structural validation (XRPL Domain 19; 46 cells populated, 0 Medium+ findings — template validated, adjacent Low MP-1 surfaced). Negative-result methodologies still tighten attack surface maps.

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
| M-15 expiry-race-matrix | block.timestamp + multicall + MEV-boost | Clock::slot + instruction array + Jito | Move time + PTB (Sui) | ledger.timestamp + TTL counters | parentCloseTime + Batch + CanonicalTXSet |
