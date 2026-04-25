# Cross-Language Methodology Index

> **Cross-language, cross-platform audit methodology.** Entries here apply to EVM/Solidity, Rust/Solana, Rust/Soroban, Move/Aptos, Move/Sui, and C/C++ alike.
>
> **Origin**: distilled from completed audits where each entry was validated against concrete findings.
>
> **Read these before every audit.** They encode attack-template thinking that pays off across projects.

## Entries

| ID | Name | Validated in | Purpose |
|----|------|--------------|---------|
| [M-03](M03-inverse-trust-lens.md) | Inverse-trust-direction lens | XRPL Domain 4 ESC-1/2 | Probe every compliance primitive from the opposite trust direction |
| [M-04](M04-feature-pool-coverage.md) | Feature-pool PoC coverage | XRPL Domain 4 ESC-1 | Bridge shared-infrastructure root cause to a specific contest feature pool |
| [M-07](M07-post-finding-sweep.md) | Post-finding root-cause sweep | XRPL L-14 sweep → ESC-3 | Fan-out a validated blind spot across all callers of the affected helper |
| [M-08](M08-holder-plants-trap.md) | Holder-plants-trap / admin-action-bricks-state | XRPL ESC-1/2/3 + CONF-1 + DEL-1 (5/5) | The highest-yield attack template across audits |
| [M-09](M09-sync-gap-detection.md) | Aggregate-vs-per-entity SYNC_GAP | XRPL CONF-1 | Any aggregate counter gating a state transition is a SYNC_GAP candidate |
| [M-10](M10-prior-audit-dedup.md) | Pre-submission 3-layer dedup | XRPL Sherlock submission | Mandatory pre-submission validation — prior audits / GitHub baseline / remediation |
| [M-11](M11-retired-amendment-poc-feasibility.md) | Retired-amendment PoC feasibility check | XRPL Domain 7 SPON-M1 (not submitted) | Before investing in a finding in a legacy code branch, verify PoC reachability |
| [M-12](M12-granular-permission-sandbox.md) | Granular permission sandbox ↔ semantic override audit | XRPL Domain 6 DEL-1 | Any "capability templates / per-op masks" system has default-permissive scope creep |
| [M-15](M15-expiry-race-matrix.md) | Expiry Race Matrix (SLE × interacting-op × race) | XRPL Domain 19 (2026-04-24; ~46 cells populated, 0 Medium+ submissions but template validated + 1 adjacent Low MP-1 surfaced) | Systematic audit of time-gated state transitions; 4-question matrix per cell (who wins at boundary / observable / triggerable / profitable asymmetry); enumerates cross-language ordering mechanisms (canonical, Batch/multicall, MEV-boost, Jito bundle, Solana instruction array, Sui PTB) |
| [M-16](M16-zk-proof-bundle-composition.md) | ZK-Proof-Bundle Composition Audit | XRPL Domain 15 (2026-04-24; 6,364 LoC C cryptographic library — mpt-crypto; ~50 cells populated, 0 Medium+ submissions but template validated + 1 Low PERIPH-M1 candidate HOLD) | Systematic audit of any protocol composing ≥2 ZK primitives (sigma + range, sigma + linkage, equality + range) or using verifier-derived public commitments. 6 cross-language meta-patterns: verifier-derived remainder, two-primitive amount-binding, orphan-public-API reachability filter, completeness-vs-soundness tradeoff, prover-verifier seckey_verify symmetry seam, paired-transactor binding comparison. Applicable to EVM (Aztec, Railway, zkBob, zkSync confidential), Solana (light-protocol, Elusiv), Aleo (record programs), Noir/Circom (range-proof circuits), Move (native ZK). |
| [M-17](M17-mutable-config-flag-audit.md) | Mutable-Configuration-Flag Audit | XRPL Domain 16 (2026-04-25; 611 LoC `MPTokenIssuanceSet.cpp`; ~70 cells populated across 12 mutable flags × 8 dimensions; 0 Medium+ submissions; 2 PARTIAL Low candidates (MP-1 HOLD per T-13 trust-model, P-2 REFUTED-by-R-25)) | Systematic audit of any protocol that allows post-deployment mutation of configuration flags/parameters affecting existing state (proxy upgradeable contracts, mutable object types, governance-controlled parameters, dynamic feature flags). 6 cross-language meta-patterns: cross-class preflight firewall, asymmetric on-chain-state-lockin, flag-clear cleanup-responsibility, mutability-tier polarity audit, SOLE post-Create writer, fresh consumer reads / no grandfathering. Applicable to EVM (TransparentProxy / UUPS / Diamond), Solana (governance + token-2022 extensions), Sui (mutable objects with `key + store`), Aptos (resource accounts). |

## How to use

1. **Before starting an audit**: skim all 8 templates. They prime the attention system.
2. **During breadth analysis**: at each transactor/function, ask:
   - Does M-08 apply? (cheap-plant + admin-op dependency?)
   - Does M-09 apply? (aggregate counter gates transition?)
   - Does M-12 apply? (granular permission with default-permissive semantic hook?)
3. **After a finding**: apply M-07 sweep to related helpers.
4. **Before submission**: run M-04 (feature classification) + M-10 (dedup) + M-11 (feasibility).

## Per-audit high-yield template

From the XRPL audit: **M-08 accounts for 5 of 5 Mediums**. Start every audit by running M-08 probe on every privileged operation. Yield > effort by a wide margin.

For ZK-using protocols specifically, start with **M-16 Phase 0 (orphan-public-API reachability check)** — skipping unreachable primitives saves ~20% of audit depth budget. Then run M-16 Phase 1 (composition matrix) as the breadth-analysis scaffold.

## Contribution guide

When a new audit validates a new template, add it here as M-NN with:
- **Name** + 1-sentence description
- **Origin** (which audit, which finding validated it)
- **Trigger** (when to apply)
- **Process** (concrete steps)
- **Cross-language mapping** (at least 2 language examples)
- **Anti-patterns** (when NOT to apply)
