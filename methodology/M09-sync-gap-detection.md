# M-09: Aggregate-vs-Per-Entity SYNC_GAP Detection

**Origin**: XRPL Sherlock April 2026, Domain 5 CONF-1 finding — a state-transition precondition checked the aggregate counter but the downstream invariant read per-entity state.

**One-line**: Any aggregate counter used as a gate for a state transition is a SYNC_GAP candidate — the aggregate can be "clean" while per-entity state is still dirty.

## Trigger

Apply whenever the code has:
- A **precondition** that reads an aggregate counter (sum, max, count across entities).
- The counter gates a **state transition** (flag flip, object delete, capability toggle).
- Downstream **invariants or transactors** read per-entity state that is DERIVED from the aggregate but not atomically synced.

## The Asymmetry

The bug class:
```
[Precondition]   aggregate_counter == clean_value  →  permit transition
[Per-entity]     some_entity.residual_field != clean  →  invariant trips on next write
```

The aggregate counter is NECESSARY but not SUFFICIENT for safe transition. The gap exists when per-entity cleanup doesn't fully sync with the aggregate.

## Process

1. **Identify aggregate counters**: grep for fields like `sfOutstandingAmount`, `totalSupply`, `balance.total`, `pool_size`, `count`.
2. **For each aggregate**, find the **state-transition precondition** that gates on it.
3. **Per entity that contributes to the aggregate**, check:
   - Does the per-entity contribution return to its "clean" state atomically when the aggregate decrements?
   - Or does the per-entity record retain residual fields / metadata after contribution is zero?
4. **For any residual per-entity state**, check:
   - Is there a downstream invariant or transactor that reads it?
   - What does it enforce that the precondition doesn't re-verify?
5. **PoC**: drive aggregate to clean value with residual per-entity state present → trigger transition → trigger the invariant-reading tx → expect failure.

## Cross-language mapping

### EVM / Solidity
| SYNC_GAP surface | Aggregate | Per-entity residual |
|------------------|-----------|---------------------|
| ERC-20 allowance reset | `totalAllowance` (if tracked) | `allowance[owner][spender]` stale |
| Compound market exit | `totalSupply` | `userIndex[user]` stale |
| Staking pool liquidation | `poolTotalStake` | `stake[user].rewardDebt` orphan |
| Governance proposal archive | `activeProposalCount` | `proposal[id].voterRegistry` never cleaned |

### Solana / Rust
| SYNC_GAP surface | Aggregate | Per-entity residual |
|------------------|-----------|---------------------|
| SPL mint close | `mint.supply` | Leftover ATA accounts with zero balance keep rent-exempt deposit |
| Token2022 extension close | `mint.extension_length` | Extension-specific TLV data in `account.data` |
| Program state migration | `state.total_accounts` | Per-account `is_initialized` stale |

### Move / Aptos & Sui
| SYNC_GAP surface | Aggregate | Per-entity residual |
|------------------|-----------|---------------------|
| Aggregator overflow | `aggregator.value` | Per-resource counters desync |
| Dynamic field table close | `table.length` | Orphan dynamic fields |

### Soroban / Stellar
| SYNC_GAP surface | Aggregate | Per-entity residual |
|------------------|-----------|---------------------|
| Persistent storage archival | Top-level TTL counter | Archived entries' derived state stale |

### C++ / XRPL (validated origin)
| Finding | Aggregate | Per-entity residual |
|---------|-----------|---------------------|
| CONF-1 | `sfConfidentialOutstandingAmount` on issuance | `sfConfidentialBalanceInbox` / `sfConfidentialBalanceSpending` / `sfIssuerEncryptedBalance` on holder MPToken — zeroed but not `makeFieldAbsent`, persist after ConvertBack |

## The Three Variants

### Variant A: Auto-cleanup asymmetry
One type of field (e.g. `STUInt64` with `soeDEFAULT`) auto-removes at 0, while another type (e.g. `STBlob`) leaves encrypted-zero placeholder. CLEAR precondition checks only the auto-cleaned field.

### Variant B: Cascade cleanup gap
Deleting a parent SLE's aggregate field drives count to 0, but child SLEs with derived fields aren't cascade-deleted.

### Variant C: Version-counter desync
Aggregate version incremented per-batch, per-entity version per-item; cross-reading creates stale reads.

## Anti-patterns

- **Don't confuse SYNC_GAP with staleness bugs**. Staleness = "read returns old value"; SYNC_GAP = "aggregate says clean but per-entity is dirty".
- **Don't report if the downstream invariant tolerates residual state**. If `ValidXxx` accepts encrypted-zero fields as valid, there's no trap.
- **Don't ignore immunity classes**. Pseudo-accounts (F-15 in XRPL manifest) are immune from many planting paths that otherwise enable SYNC_GAP exploitation.

## Detection checklist

```
[ ] Found an aggregate counter used as precondition
[ ] Identified all per-entity contributors to the aggregate
[ ] For each contributor: check atomic cleanup on contribution zero
[ ] For each residual field: check downstream readers (invariants, transactors)
[ ] For each residual-reader: check what it enforces beyond the precondition
[ ] If mismatch: construct PoC (drive aggregate to 0, leave residual, transition, trigger reader)
```

## Related methodology

- **M-08** (holder-plants-trap) uses SYNC_GAP when the aggregate gate is the "clean signal" the issuer relies on but can't see the trap.
- **M-07** sweep finds additional SYNC_GAPs once one is validated — same pattern applies to every aggregate counter in the codebase.
