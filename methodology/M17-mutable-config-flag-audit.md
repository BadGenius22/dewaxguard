# M-17 — Mutable-Configuration-Flag Audit

> **Purpose**: systematic methodology for auditing any protocol that allows post-deployment mutation of configuration flags or parameters that affect EXISTING on-chain state. Triggers on proxy upgradeable contracts, mutable object types, governance-controlled parameters, dynamic feature flags, and any pattern where the configuration tier is decoupled from the value tier.
>
> **Status**: first validated on XRPL April 2026 audit (Domain 16, 8-agent breadth, 2026-04-25). Populated ~70 composition-matrix cells across 12 mutable flags × 8 dimensions on `MPTokenIssuanceSet` (431 LoC). 0 Medium+ submissions but 6 cross-language meta-patterns validated against concrete code.
>
> **Cross-language**: applies to EVM (TransparentProxy / UUPS / Diamond + mutable params), Solana (governance-controlled program upgrades + token-2022 TransferFeeConfig), Sui (mutable objects with `key + store` ability), Aptos (resource accounts with config-table mutation), Move generally (capability mutation).

---

## Trigger

Invoke this methodology when the protocol under audit has ANY of:

1. **Mutable configuration tier separate from value tier** — e.g., `lsmf*` mutability bits gating `lsf*` value bits (XRPL XLS-0094 pattern); EVM upgradeable proxy implementation slot + storage layout; Solana program upgrade authority + program data account.
2. **Post-deployment mutation of flags affecting existing state** — flags consumed by accumulated holder balances, pending orders, in-flight escrows, registered authorizations.
3. **Governance-controlled parameter mutation** — DAO-voteable fees, oracle staleness thresholds, lock durations, withdrawal limits.
4. **Dynamic feature flags** — runtime-mutable feature toggles (`pause()`, whitelist enable/disable, mode switches).
5. **Mutable object types** — Sui `key + store` ability, Move resource mutation capabilities, Aptos config tables.

---

## Phase 0 — Mutability Inventory

Before composition-matrix analysis, exhaustively enumerate the mutability surface.

### Steps

1. Enumerate every flag/parameter that CAN be mutated post-deployment.
2. For each, identify the tier it belongs to (value tier vs mutability tier vs meta-mutability).
3. For each, identify the gating mechanism (per-mutation opt-in bit, role-based access, governance vote, time delay).
4. For each, identify the SOLE writer or list of writers (grep for SLE/account/storage-slot writes).
5. For each writer, identify whether it has a sandbox/guard mechanism (granular permissions, role check, semantic override hook).

### Concrete example (Domain 16 / XLS-0094)

```
12 mutable surfaces on MPTokenIssuanceSet:
- 7 normal flag pairs: CanLock, RequireAuth, CanEscrow, CanTrade, CanTransfer, CanClawback, CanConfidentialAmount
- 3 mutable fields: TransferFee, MPTokenMetadata, DomainID
- 2 set-once fields: IssuerEncryptionKey, AuditorEncryptionKey

Mutability tier (lsmfMPT*): 8 positive-polarity bits + 1 inverse-polarity bit (audit-smell D-44)
SOLE writer: MPTokenIssuanceSet::doApply for issuance fields; VaultSet for vault-share DomainID
```

---

## Phase 1 — Composition Matrix Population (M-17 deliverable)

For every mutable flag/parameter, enumerate `(flag × mutation-direction × consumer × post-mutation-consistency)` cells across 8 dimensions.

### The 8 dimensions

| Dimension | Concerns |
|---|---|
| **Set→Clear retroactive effect** | If flag was enabled and accumulated state (escrows, offers, balances), clearing now — what happens to that state? Does it persist as "sticky state"? |
| **Clear→Set retroactive effect** | If flag was disabled and clearing-era ops were permitted, setting now — are old auth-less actors regularized or stranded? |
| **Mutation-allowed-bit immutability** | The meta-mutability bit (`lsmfMPTCanMutate*`) is set at CREATE and never mutable. Is this enforced everywhere? Check via grep all writers. |
| **Cross-flag coupling** | Mutating flag A changes the meaning of existing flag B (e.g. CanConfidentialAmount implies encryption keys must exist). |
| **Consumer invalidation** | After mutation, which on-ledger SLEs / accounts / storage slots become inconsistent with the new flag state? |
| **Preclaim race** | Same-tx dual mutation (kuprum #6603 style) — does preclaim read current state or projected state? |
| **Batch composition** | Can a Batch / multicall / atomic bundle combine BOTH a flag mutation AND a flag-dependent op such that the second sees stale flag state? |
| **Invariant coverage** | Does any protocol-level invariant catch illegitimate flag flips or post-mutation state inconsistency? |

### Status legend per cell

- `VS` — VERIFIED SAFE (concrete code-level evidence the bug doesn't exist)
- `RC` — REFUTED CLASS (manifest reference; same root-cause family as a known refutation)
- `CB` — CONFIRMED BUG (submittable finding)
- `KN` — KNOWN ISSUE (kuprum-indexed or prior-audit-indexed; OOS per known-issue baseline)
- `UE` — UNEXPLORED (low-priority cell after framework facts established)

### Cross-language ordering mechanisms

Which actors can race the mutation? Per-platform:

| Platform | Mechanism |
|---|---|
| EVM (Ethereum L1) | MEV-boost block builder ordering; same-block tx ordering by gas tip; private-mempool relays |
| EVM (L2 — Optimism, Arbitrum, Base) | Sequencer-controlled ordering; cross-chain message timing |
| Solana | Same-slot ordering by Jito bundle / leader; instruction-array atomicity within tx |
| Sui | PTB (Programmable Transaction Block) atomicity; cross-PTB shared-object access |
| Aptos | Block-STM parallel execution + sequence number ordering |
| XRPL | Canonical TX set ordering by `(account XOR parentHash, seqProxy, txId)`; Batch atomicity (XLS-0056) per F-12 inner-tx propagation |
| Cosmos | ABCI BeginBlock/EndBlock ordering; IBC packet timing |

The platform's ordering mechanism determines:
- Whether an attacker can deterministically race a defender (XRPL: cross-account ~50/50, same-account deterministic by seq, Batch attacker-controlled)
- Whether a defender can atomically bundle defense (Batch / multicall / PTB)
- Whether a "sticky state" trap survives mutation re-ordering

---

## Phase 2 — Reward-Pool / Severity Calibration

### Issuer-trust model gating

If the protocol declares the mutator a TRUSTED actor (issuer, governance multisig, DAO, timelock), bare mutation is OOS for security-grade findings — the trusted actor exercising their rights is not a bug.

Severity ladder for mutation findings (under trusted-mutator model):

1. **Bare mutation by trusted actor** → OOS. T-01-class downgrade.
2. **Asymmetric lock-in / inverse polarity / cleanup gap (spec-break)** → Low. The bug is in the SPEC ROLLOUT (failure to coordinate consumer SLEs with the mutability), not the mutator's action.
3. **Consumer corruption that bypasses trust model (e.g., delegate exceeds scope, sandbox gap)** → Medium. The bug enables an UNTRUSTED actor to trigger the mutation.
4. **Consumer corruption affecting a different tier (e.g., XLS-0096 confidential invariant trap from XLS-0094 flag clear)** → Medium+. Cross-spec amplification.

### Cross-language calibration examples

| Pattern | Severity ceiling under trusted-mutator |
|---|---|
| Issuer raises transfer fee on existing offers (XRPL MP-1) | Low (spec-break: ltOFFER doesn't lock fee while ltESCROW does) |
| EVM proxy admin upgrades implementation, breaking storage layout | Critical (constitutes theft / lockup of user funds — exceeds trust scope) |
| Solana governance admin sets staleness threshold below cached oracle age | Medium (consumer logic now reads fresh-but-stale oracle) |
| Sui mutable object capability rotated mid-PTB | Medium (PTB observes stale capability — race) |
| Token-2022 issuer rotates TransferFeeConfig while orders pending | Low-Medium (Jupiter/Raydium read live fee on pending orders) |

---

## Phase 3 — Anti-pattern Catalog

Flag any of these anti-patterns when scanning a mutable-config surface:

### Anti-pattern 1: Live-read consumers when peer consumers lock-in (asymmetric lock-in — MP-1 archetype)

**Signal**: helper function reads mutable parameter from current state at every call (e.g. `transferRate(view, issuance)`), but ONE consumer SLE persists the parameter at create time while OTHER consumer SLEs do NOT.

**Detection**: grep for the helper's call sites; for each call site identify the calling SLE's persistence schema; check whether the SLE has a snapshot field for the parameter.

**Cross-language**: EVM proxy `transferFee()` consumed by both Escrow contracts (snapshots fee at create) and OrderBook contracts (live-reads fee at fill); Solana token-2022 `getTransferFeeConfig()` consumed inconsistently across Jupiter/Raydium/Phoenix.

### Anti-pattern 2: Inverse-polarity flag in a mostly-positive flag family (D-21/D-44 archetype)

**Signal**: most flag bits in a flag word use "set-to-UNLOCK" semantics (bit=1 means feature enabled / mutation permitted), but one bit uses "set-to-LOCK" semantics (bit=1 means feature disabled / mutation blocked).

**Detection**: enumerate every `lsmf*` / mutability bit; check the gating logic in code for ternary expressions or polarity-inversion conditionals.

**Cross-language**: EVM `paused` (positive: 1=paused) vs typical "enabled" flags (positive: 1=enabled); Solana `is_initialized` (positive: 1=initialized but blocks re-init); Sui `is_frozen`.

### Anti-pattern 3: Cleanup gap when flag is cleared with outstanding accumulated state (CONF-1 archetype)

**Signal**: a flag-clear gate checks an aggregate counter (e.g. `outstandingAmount > 0`) but per-entity state (per-holder fields) can be non-zero while the aggregate is zero.

**Detection**: M-09 SYNC_GAP audit — for every aggregate-vs-per-entity gate, verify aggregate-clean implies per-entity-clean.

**Cross-language**: ERC4626 `totalSupply == 0` blocks `unpause()` but per-vault per-holder shadow state may persist; Solana whitelist `total_count == 0` blocks dewhitelist while per-account whitelist entries persist; Sui shared-object reference count.

### Anti-pattern 4: Missing invariant for "immutable post-create" fields (L-19 archetype)

**Signal**: certain SLE fields are documented as immutable post-create, but no protocol-level invariant enforces this — only transactor preclaim guards do.

**Detection**: enumerate immutable fields per SLE type; check the `NoModifiedUnmodifiableFields` (or equivalent) invariant for explicit per-type cases; default branch coverage = latent gap.

**Cross-language**: EVM proxy `_initialized` flag (single-write enforced by transactor only); Solana program-derived-account discriminator (single-write enforced by program); Sui object freeze (single-write but no slashing-style invariant).

### Anti-pattern 5: Cross-actor trust delegation (ECS-2 archetype)

**Signal**: protocol's stated trust set is {issuer, validators, admins}, but functional dependency on a non-stated actor exists (e.g., MPT issuer pinned to 3rd-party PermissionedDomain owner — implicit trust delegation).

**Detection**: for every cross-SLE reference, identify the controller of the referenced SLE; check whether the controller is in the stated trust set.

**Cross-language**: EVM contract pinned to oracle whose owner is not in the protocol's trust set; Solana account dependency on third-party-deployed program; Cosmos IBC pinned to relayer not in chain's trust set.

### Anti-pattern 6: Same-tx dual mutation preclaim race (kuprum #6603 archetype)

**Signal**: a mutation requires a precondition that's satisfied by another mutation in the same tx; but preclaim reads current state (before in-tx mutations apply).

**Detection**: enumerate every precondition gate that depends on a mutable field; check whether the same tx can mutate that field; verify preclaim-vs-doApply ordering.

**Cross-language**: EVM `require(condition)` in dependent function called via multicall before condition-setter; Solana CPI calls with dependent state; Sui PTB ordering.

---

## Phase 4 — Methodology Application Examples

### Example 1: XRPL Dynamic MPT (Domain 16, validated)

**Surface**: `MPTokenIssuanceSet` (XLS-0094) with 12 mutable flags/fields × 8 dimensions = 96 theoretical cells.

**Result**: ~70 cells populated. 0 Medium+ submissions. Key findings:
- All 6 non-confidential flag retroactive-clear scenarios REFUTED via R-06/24/25/26 (manifest entries) — issuer compliance feature per T-01 trust model.
- CONF-1 (sole CONFIRMED bug) caught by M-09 SYNC_GAP (aggregate `sfConfidentialOutstandingAmount` insufficient vs per-entity encrypted residue).
- MP-1 (PARTIAL Low candidate, HOLD) — anti-pattern 1 (asymmetric lock-in).
- P-2 (PARTIAL Low candidate, REFUTED-by-R-25) — anti-pattern 5 variant (RPC-annotation gap).
- Cross-class preflight firewall (manifest F-46 + D-42) kills entire dual-mutation race space.
- Mutation-allowed-bit (`lsmfMPT*CanMutate*`) immutability structurally enforced (R-83).

### Example 2: EVM proxy upgrade audit (cross-language template application)

**Surface**: TransparentProxy / UUPS upgrade with `_implementation` slot + storage layout + accumulated user balances.

**Apply M-17 cells**:
- **Set→Clear retroactive (admin downgrades fee)**: anti-pattern 1 — pending orders read live fee.
- **Clear→Set retroactive (admin enables clawback)**: anti-pattern 3 — existing balances now clawback-eligible (CONF-1 archetype: per-holder state expects no clawback).
- **Mutation-allowed-bit immutability**: `_initialized` flag — anti-pattern 4 if no invariant.
- **Cross-flag coupling**: implementation slot mutation while storage layout has accumulated state (Critical — exceeds trust scope).
- **Preclaim race**: same-block multicall with upgrade + dependent-call (anti-pattern 6).
- **Invariant coverage**: typically NO protocol-level invariant for proxy storage layout.

### Example 3: Solana governance audit (cross-language template application)

**Surface**: governance-controlled program upgrade + token-2022 TransferFeeConfig + Jupiter/Raydium pending orders.

**Apply M-17 cells**:
- **Set→Clear retroactive (governance lowers fee)**: anti-pattern 1 — pending orders on Jupiter/Raydium read live fee.
- **Mutation-allowed-bit immutability**: program upgrade authority can be revoked (immutability decision); audit governance vote thresholds.
- **Consumer invalidation**: after upgrade, old data accounts may be incompatible with new instruction handlers.
- **Batch composition**: instruction-array atomicity — verify governance vote + dependent action cannot be bundled.

### Example 4: Sui mutable object audit (cross-language template application)

**Surface**: mutable object with `key + store` ability + cross-PTB shared-object references.

**Apply M-17 cells**:
- **Set→Clear retroactive (object owner mutates capability)**: PTB observers may read stale capability mid-execution.
- **Cross-flag coupling**: mutable object referenced across PTB boundaries — atomicity guarantee?
- **Mutation-allowed-bit immutability**: object freeze/unfreeze semantics; verify single-direction immutability.
- **Invariant coverage**: Move ability constraints provide structural enforcement; verify ability composition.

---

## Phase 5 — Anti-patterns to flag (checklist)

When scanning ANY mutable-config surface, raise an audit-smell flag for:

- [ ] **Live-read consumers when peer consumers lock-in** — asymmetric handling (MP-1 / D-42)
- [ ] **Inverse-polarity flag in mostly-positive flag family** — polarity confusion (D-21 / D-44)
- [ ] **Cleanup gap when flag is cleared with outstanding accumulated state** — CONF-1 archetype (M-09)
- [ ] **Missing invariant for "immutable post-create" fields** — L-19 archetype (D-45)
- [ ] **Cross-actor trust delegation** — implicit trust set extension (ECS-2 archetype)
- [ ] **Same-tx dual mutation preclaim race** — kuprum #6603 archetype
- [ ] **No "force-cleanup" mechanism for sticky state** — D-43 archetype
- [ ] **Default-state behavior under amendment activation** — legacy issuance traps (Gap-A archetype)

---

## When NOT to apply M-17

- Protocol has NO post-deployment mutation surface (immutable contracts / objects / programs only).
- All mutations require unanimous consent of all affected parties (functionally equivalent to immutability).
- Mutator is a fully-trusted actor whose actions are explicitly listed as "expected behavior" in the protocol spec, AND no consumer SLE persistence schemas reference mutable parameters.

---

## Validated findings (per-audit)

- **XRPL Domain 16 (2026-04-25)** — 0 Medium+ submissions; 2 PARTIAL Low candidates (MP-1 HOLD per T-13 trust-model; P-2 REFUTED-by-R-25). 6 cross-language meta-patterns extracted. ~70 cells populated. Strong negative-result methodology validation.

---

## Cross-language meta-patterns surfaced

| ID | Pattern | XRPL instance | Cross-language application |
|---|---|---|---|
| F-46 | Cross-class preflight firewall | `MPTokenIssuanceSet.cpp:104-105` rejects mutate × tx-flag-op combo | EVM `require(uint(action) & MUTATE_MASK == 0 \|\| (action & FLAG_OP_MASK) == 0)`; Solana instruction-discriminator partitioning; Move ability-flag firewalls |
| D-42 | Asymmetric on-chain-state-lockin | ltESCROW locks `sfTransferRate` at create; ltOFFER/ltCHECK live-read | EVM proxy + pending Order/Escrow contracts; Solana token-2022 + Jupiter/Raydium; Sui Kiosk listings; Aptos AMM pool fees |
| D-43 | Flag-clear cleanup-responsibility | CONF-1 trap (MPTokenIssuanceSet clear without per-entity sweep) | EVM `pause()` mid-flight; Solana whitelist toggle; Sui mutable refs; Aptos config-table mutation |
| D-44 | Mutability-tier polarity audit | `lsmfMPTCannotMutateCanConfidentialAmount` inverse polarity (D-21) | EVM access-modifier upgrades; Solana program-upgrade authority; Sui mutable object capability |
| D-45 | SOLE post-Create writer pattern | L-19 latent gap on `sfMutableFlags` | EVM proxy `_initialized` flag protection; Solana program-derived-account immutability; Sui object freeze-with-`store`; Move resource ownership |
| F-47 | Fresh consumer reads / no grandfathering | All MPT consumers re-read flag fresh at execution | EVM `view()` callers reading mutable storage; Solana account-data freshness; Move shared-object reads |

---

## Phase 6 — Output format

For each audit, produce a populated composition matrix:

```markdown
| Flag | Set→Clear | Clear→Set | Mutate-bit immut | Cross-flag | Consumer | Preclaim race | Batch | Invariant |
|---|---|---|---|---|---|---|---|---|
| FlagA | VS / RC X-NN | ... | ... | ... | ... | ... | ... | ... |
| FlagB | CB Finding-1 | ... | ... | ... | ... | ... | ... | ... |
```

Append a per-pattern anti-pattern checklist (Phase 5). Include severity calibration per Phase 2.

---

## Anti-bloat note

If the codebase has < 3 mutable flags or no cross-ledger-persistent consumers, M-17 is overkill — use M-09 SYNC_GAP or D-25 switch-firewall directly without the full matrix.
