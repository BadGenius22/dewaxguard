# XRPL Sherlock April 2026 — Finding Pattern Index

**Audit summary**: 5 Medium submission-ready findings from 7 domain audits + 1 L-14 sweep. **All 5 reward pools touched** (3 with findings, 2 cleared with explicit verdicts).

## Findings

| File | Finding | Attack template | Reward pool | Severity |
|------|---------|-----------------|-------------|----------|
| [esc1-clawback-shield.md](esc1-clawback-shield.md) | ESC-1 | M-08 holder-plants-trap | MPT DEX (XLS-0082) | Medium |
| [esc2-dust-destroy.md](esc2-dust-destroy.md) | ESC-2 | M-08 (issuance lifecycle variant) | MPT DEX | Medium |
| [esc3-vault-share.md](esc3-vault-share.md) | ESC-3 | M-08 + M-07 sweep | MPT DEX | Medium |
| [conf1-flag-clear-brick.md](conf1-flag-clear-brick.md) | CONF-1 | M-08 + M-09 SYNC_GAP | Confidential MPT (XLS-0096) | Medium |
| [del1-granular-sponsor-scope-creep.md](del1-granular-sponsor-scope-creep.md) | DEL-1 | M-12 granular-sandbox scope creep | Permission Delegation (XLS-0075) | Medium |

## Attack mechanism breakdown

- **F-13 (accountHolds blind spot)**: ESC-1, ESC-2, ESC-3 — same root cause, 3 different admin ops
- **SYNC_GAP (aggregate vs per-entity)**: CONF-1 — distinct root cause, same M-08 class
- **Granular scope creep (missing semantic override)**: DEL-1 — entirely new mechanism, first validation of M-12

## Reward pool coverage

| Pool (XLS) | Status |
|------------|--------|
| Batch (XLS-0056) | **Cleared** in Domain 3 (no submittable findings, 14 DA attempts) |
| Permission Delegation (XLS-0075) | **Hit** — DEL-1 |
| MPT DEX (XLS-0082) | **Hit** — ESC-1, ESC-2, ESC-3 |
| Confidential MPT (XLS-0096) | **Hit** — CONF-1 |
| Sponsored Fees (XLS-0068) | **Cleared** in Domain 7 (FYEO remediations verified, SPON-M1 PoC-blocked per M-11) |

## Key takeaways for future XRPL audits

1. **XRPL MPT `accountHolds` excludes `sfLockedAmount`** — validated blind spot. Any new MPT-touching op that reads balance via this helper must be scrutinized.
2. **MPT escrow (`lsfMPTCanEscrow`) is unconditionally set on vault shares** by `VaultCreate.cpp:184`. No per-capability opt-out exists. Flag every new MPT-issuing transactor for the same pattern.
3. **`ConfidentialMPTConvertBack` zeroes but doesn't remove encrypted fields** — trap-planting primitive. Flag every new confidential-data transactor for the same "zero vs absent" asymmetry.
4. **Pseudo-accounts are immune** from escrow-based planting (cannot sign → cannot escrow). Saves sweep time.
5. **`SponsorshipSet` / `AccountSet` / `MPTokenIssuanceSet` lack `checkGranularSemantics` overrides**. Every new granular permission for these (or future transactors) is a DEL-1 candidate.
6. **`MultiSignReserve` is retired** — pre-MSR SignerList legacy branch unreachable via public-tx PoCs in test env. Any finding in this branch is Sherlock-invalid per M-11.

## Cross-language applicability

The most transferable lesson is **M-12**: any new contest that introduces capability templates / per-op permission masks / fine-grained delegation is a DEL-1-style scope creep candidate. Apply M-12 checklist on first pass of EVM AccessControl, Solana Anchor `#[access_control]`, Aptos Capability types, Soroban fine-grained auth.
