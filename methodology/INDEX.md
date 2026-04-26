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
| [M-18](M18-account-lifecycle-cleanup-switch.md) | Account-Lifecycle Cleanup-Switch Completeness Matrix | XRPL Domain 18 (2026-04-25; AccountDelete × new-SLE matrix; 442 LoC `AccountDelete.cpp` + 9 cleanup helpers + new-SLE writers; 8-agent breadth; ~28 cells populated × 8 dimensions; 0 Medium+ submissions; 1 contested PARTIAL CONFIRMED Low post-arbitration ECS18-1; 4 known-issue dedups (kuprum #6889/#6892/#6893/#6900) all surface as predicted by matrix) | Systematic audit of any protocol with account/object lifecycle close + obligation-check gating. 8 dimensions per cell: switch-completeness, block-vs-cascade-vs-orphan choice, dual owner-dir linking, reserve refund symmetry, dormancy/time-lock window, post-cleanup invariant coverage, test coverage, RPC observability. Tier-A/B/C/D adversarial-creation × cleanup-coverage classification (tier-D is the kuprum #6892 anti-pattern). **NEW SUB-METHODOLOGY (Phase 3): cross-agent contradiction handling — generalized into M-21.** Applicable to EVM (`selfdestruct` deprecated EIP-6049 + ERC-6900 plugin uninstall), Solana (`close` instruction with lamport recovery), Sui (`object::delete` with `key + store` ability cascade), Aptos (`move_from` resource destruction), Cosmos (`keeper.Delete()` patterns). |
| [M-19](M19-path-selection-determinism-x-asymmetry.md) | Path-Selection Determinism × Economic-Asymmetry Matrix | XRPL Domain 21 (2026-04-26; Pathfinder × MPT; 1413 LoC `Pathfinder.cpp` + ~530-line diff; 8-agent breadth; ~35-cell matrix populated; 0 Medium+ submissions, 1 NEW Low submittable L-34 surfaced; 5-way agent concurrence on consensus-bound-vs-RPC-only architectural distinction) | Systematic audit of any path-finding / route-selection / DEX-aggregator code. Two axes (~35 cells): D1-D7 determinism dimensions (hash-map iteration, pointer comparison, FP math, eval order, sort stability, comparator strict-weak-order, address-dependent ordering); E1-E10 economic-asymmetry dimensions (token-direction asymmetry, self-issued advantage, transfer-fee carve-outs, pseudo-account immunity, multi-hop fee composition, first-depositor edge, cross-validator divergence, frozen-state mid-route, stale-parameter retroactive effect, convergence iteration count by asset type). Applicable to EVM (Uniswap V3 SmartOrderRouter, 1inch Pathfinder, Cowswap solver), Solana (Jupiter aggregator, Orca route-handler), Sui (DeepBook router), Aptos (PancakeSwap-style aggregator). |
| [M-20](M20-wire-format-mature-layer-audit.md) | Wire-Format Mature-Layer Audit Matrix | XRPL Domain 20 (2026-04-26; Binary Serialization / Canonical-Form Attacks; 8-agent breadth on `sfields.macro` 35 NEW SFields + STAmount/STObject/STParsedJSON/STTx/STPathSet/Indexes/Serializer; 0 Medium+, 0 Low submittables; 4-dim verdict 35/35 PASS unanimously) | Systematic audit of binary/wire-format serialization layers in mature codebases. 4-dimension verdict per type-codec cell (parse-time validation / template completeness / cross-codec consistency / fuzz-coverage). Includes orphan-public-API filter and convergence-on-informational handling (when N agents converge on same property, the convergence is evidence not noise). Cross-language examples: Bitcoin `CTransaction` consensus rules, Ethereum RLP canonical encoding, Solana borsh schema validation, Cosmos protobuf PROTO3 LAST-WINS trap, Sui/Aptos BCS. |
| [M-21](M21-cross-agent-contradiction-protocol.md) | Cross-Agent Contradiction Protocol with Mandatory Source-Code Arbitration | XRPL Domain 17 (2026-04-26; lone-flagger arbitration produced L-35 — the 3rd reward-pool hit that all 7 other breadth agents missed; independently re-validated in Domain 18 ECS18-1 against majority-refute) | When multi-reviewer pipelines (8-agent breadth, peer review, formal-verifier vs dynamic-analyzer, static-vs-LLM) produce contradictory verdicts OR a lone-flagger surfaces a finding the others missed: mandatory source-code arbitration at the merge step. Never majority-vote, never trust citations alone, never defer to higher-confidence agent. 4-step protocol: catalog disagreement → read source at union of ranges → classify A-correct/B-correct/neither → write override record. Generalizes the M-18 Phase-3 sub-rule into an always-on merge protocol. **Highest-leverage methodology in the v1.5.0 release** — without it, the XRPL audit would have shipped 2 of 5 reward pools instead of 3. |

## How to use

1. **Before starting an audit**: skim all templates. They prime the attention system.
2. **During breadth analysis**: at each transactor/function, ask:
   - Does M-08 apply? (cheap-plant + admin-op dependency?)
   - Does M-09 apply? (aggregate counter gates transition?)
   - Does M-12 apply? (granular permission with default-permissive semantic hook?)
3. **After a finding**: apply M-07 sweep to related helpers.
4. **At the merge step (multi-agent pipelines)**: apply **M-21** — never majority-vote without source-code arbitration on lone-flaggers.
5. **Before submission**: run M-04 (feature classification) + M-10 (dedup) + M-11 (feasibility).

## Per-audit high-yield template

From the XRPL audit: **M-08 accounts for 5 of 5 Mediums**. Start every audit by running M-08 probe on every privileged operation. Yield > effort by a wide margin.

**For multi-agent breadth pipelines specifically**: **M-21** is the single highest-leverage merge-step protocol. In the XRPL April 2026 audit, M-21 alone produced the 3rd reward-pool hit (L-35) that all 7 other breadth agents missed. Cost ~5 min per arbitration; yield can be the difference between covering N and N+1 reward pools.

For ZK-using protocols specifically, start with **M-16 Phase 0 (orphan-public-API reachability check)** — skipping unreachable primitives saves ~20% of audit depth budget. Then run M-16 Phase 1 (composition matrix) as the breadth-analysis scaffold.

For DEX aggregator / path-finder audits: **M-19 35-cell matrix** is the breadth-scaffold. The most common false-positive Critical findings live at the consensus-bound-vs-RPC-only architectural seam — verify reachability before investing depth.

For wire-format / serialization layers: **M-20 4-dim verdict matrix** with explicit "0 findings = methodology validated, not failure" framing. Mature wire layers usually pass; the matrix prevents both over-investment in known-safe surfaces and silent skipping of asymmetric edge cells.

## Contribution guide

When a new audit validates a new template, add it here as M-NN with:
- **Name** + 1-sentence description
- **Origin** (which audit, which finding validated it)
- **Trigger** (when to apply)
- **Process** (concrete steps)
- **Cross-language mapping** (at least 2 language examples)
- **Anti-patterns** (when NOT to apply)
