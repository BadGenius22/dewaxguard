# XRPL Sherlock April 2026 — Finding Pattern Index

**Audit summary (final, post-kuprum-dedup 2026-04-23)**: **4 Mediums submission-ready** (ESC-1/2/3 + CONF-1) across **2 of 5 reward pools with submittable findings**; **2 Low findings drafted** (L-30, L-31); **1 Low candidate held** (L-32). **DEL-1 reclassified OOS** as duplicate of public issue #6890 (created 22.5h before contest start).

## Submittable findings

| File | Finding | Attack template | Reward pool | Severity |
|------|---------|-----------------|-------------|----------|
| [esc1-clawback-shield.md](esc1-clawback-shield.md) | ESC-1 | M-08 holder-plants-trap | MPT DEX (XLS-0082) | Medium |
| [esc2-dust-destroy.md](esc2-dust-destroy.md) | ESC-2 | M-08 (issuance lifecycle variant) | MPT DEX | Medium |
| [esc3-vault-share.md](esc3-vault-share.md) | ESC-3 | M-08 + M-07 sweep | MPT DEX | Medium |
| [conf1-flag-clear-brick.md](conf1-flag-clear-brick.md) | CONF-1 | M-08 + M-09 SYNC_GAP | Confidential MPT (XLS-0096) | Medium |
| [l30-pathrequest-missing-else.md](l30-pathrequest-missing-else.md) | L-30 | Variant-refactor regression (new class) | MPT DEX | Low |
| [l31-accountdestassets-mpt-asymmetry.md](l31-accountdestassets-mpt-asymmetry.md) | L-31 | Parallel-branch asymmetry (new class) | MPT DEX | Low |
| [l33-escrowcreate-sponsor-reserve-over-restriction.md](l33-escrowcreate-sponsor-reserve-over-restriction.md) | L-33 | Silent-default-arg sponsor elision (new class — paired-transactor asymmetry) | Sponsored Fees (XLS-0068) | Low |

## Held / OOS

| File | Finding | Reason |
|------|---------|--------|
| [del1-granular-sponsor-scope-creep.md](del1-granular-sponsor-scope-creep.md) | DEL-1 | **OOS** — duplicate of public #6890 (2026-04-12 16:27 UTC). Template (M-12) still valid. |
| [l32-account-objects-sponsored-pagination.md](l32-account-objects-sponsored-pagination.md) | L-32 | **Held** — M-14 unchanged-legacy risk. Submission-worthiness depends on judge interpretation. |

## Attack mechanism breakdown

- **F-13 (accountHolds blind spot)**: ESC-1, ESC-2, ESC-3 — same root cause, 3 different admin ops
- **SYNC_GAP (aggregate vs per-entity)**: CONF-1 — distinct root cause, same M-08 class
- **Granular scope creep (missing semantic override)**: DEL-1 — first validation of M-12; finding OOS but template reusable
- **Variant-refactor regression**: L-30 — MPT-aware refactor lost an `else` keyword inside a new lambda
- **Parallel-branch asymmetry**: L-31 — new MPT branch in dest-asset helper used inconsistent condition vs parallel IOU branch
- **Filter-counter ordering (M-14)**: L-32 — pagination counter increments pre-filter, drained by new sponsored filter (contested)
- **Silent-default-arg sponsor elision**: L-33 — `EscrowCreate.cpp:410-414` passes `{}` for `sponsorSle` to `checkInsufficientReserve` (cf. `PaymentChannelCreate.cpp:73-74` which passes `sponsor`); over-counts `ownerReserveUnits` by 1 `incrementReserve` for sponsored XRP escrows. Discovered via Domain 19 M-15 expiry-race scan; cross-site comparison was dispositive.

## Reward pool coverage (FINAL)

| Pool (XLS) | Status |
|------------|--------|
| Batch (XLS-0056) | **Cleared** in Domain 3 (no submittable findings, 14 DA attempts) |
| Sponsored Fees (XLS-0068) | **Cleared** in Domain 7 (FYEO remediations verified); L-32 candidate held per M-14; **L-33 discovered Domain 19 (POC-PASS, NEW-in-delta) — submission pending; if accepted, restores 3/5 pool coverage** |
| Permission Delegation (XLS-0075) | **Lost** — DEL-1 reclassified OOS via M-13 kuprum dedup on 2026-04-23. Alternative hunt produced no novel finding (R-66 in local manifest) |
| MPT DEX (XLS-0082) | **Hit** — ESC-1, ESC-2, ESC-3 + L-30, L-31 drafted |
| Confidential MPT (XLS-0096) | **Hit** — CONF-1 |
| Dynamic MPT (XLS-0094) | **Not targeted** — 0 probes. Only unhit reward pool with no Medium attempts. |

**2 of 5 pools covered with submittable findings.** If L-33 (POC-PASS) is submitted and accepted, Sponsored Fees becomes 3/5.

## Key takeaways for future XRPL audits

1. **XRPL MPT `accountHolds` excludes `sfLockedAmount`** — validated blind spot. Any new MPT-touching op that reads balance via this helper must be scrutinized.
2. **MPT escrow (`lsfMPTCanEscrow`) is unconditionally set on vault shares** by `VaultCreate.cpp:184`. No per-capability opt-out exists. Flag every new MPT-issuing transactor for the same pattern.
3. **`ConfidentialMPTConvertBack` zeroes but doesn't remove encrypted fields** — trap-planting primitive. Flag every new confidential-data transactor for the same "zero vs absent" asymmetry.
4. **Pseudo-accounts are immune** from escrow-based planting (cannot sign → cannot escrow). Saves sweep time.
5. **`SponsorshipSet` / `AccountSet` / `MPTokenIssuanceSet` lack `checkGranularSemantics` overrides**. Every new granular permission for these (or future transactors) is a DEL-1 candidate — even though DEL-1 itself was OOS'd, the TEMPLATE is still the right hunt angle.
6. **`MultiSignReserve` is retired** — pre-MSR SignerList legacy branch unreachable via public-tx PoCs in test env. Any finding in this branch is Sherlock-invalid per M-11.
7. **Kuprum-style 3rd-party known-issue indices are GOLD** — per M-13, ingest within 48h of contest start. DEL-1 was a working Medium for days before the index revealed it was OOS.
8. **Variant-refactor regressions** (L-30 pattern) — any PR that wraps an `if / else if / else` chain inside a new lambda is a high-risk refactor site. Review every refactor diff with side-by-side keyword-level comparison.
9. **Parallel-branch asymmetry** (L-31 pattern) — when a helper gains a new branch for a NEW asset type, write the condition table side-by-side BEFORE reading tests. Tests may encode the WRONG expectation.
10. **Unchanged-legacy elevated-impact** (L-32 / M-14) — pre-existing bugs can become in-scope when new amendments make them common-case. Requires explicit elevation argument in writeup.

## Cross-language applicability

The most transferable lessons:

1. **M-12**: any new contest that introduces capability templates / per-op permission masks / fine-grained delegation is a DEL-1-style scope creep candidate. Apply M-12 checklist on first pass of EVM AccessControl, Solana Anchor `#[access_control]`, Aptos Capability types, Soroban fine-grained auth.
2. **M-13**: every competitive audit platform has kuprum-equivalent catalogs. Find them in the first 48h.
3. **M-14**: every contest with a "new or elevated impact only" scope rule has M-14 decision zones. Quantify the elevation ratio explicitly before submitting.

## Session history

- **2026-04-18**: Domains 1-7 complete, 5 Mediums drafted
- **2026-04-22**: Domains 8-11 complete (invariant + AMM rescan)
- **2026-04-23 morning**: Domains 12-14 complete
- **2026-04-23 afternoon**: Kuprum index ingested — DEL-1 OOS, L-30/L-31/L-32 drafted, methodology updated with M-13/M-14
