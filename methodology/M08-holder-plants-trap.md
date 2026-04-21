# M-08: Holder-Plants-Trap / Admin-Action-Bricks-State

**Origin**: XRPL Sherlock April 2026 — the highest-yield attack template from this audit. 4 of 4 Medium findings (ESC-1/2/3, CONF-1) traced to this pattern.

**One-line**: An untrusted holder cheaply pre-plants persistent, harmless-looking state; a legitimate issuer/admin action later trips on that state and bricks, fails, or inverts outcome.

## Trigger

Apply to **every new amendment / protocol feature that touches token state**. Specifically:
- New token types (MPT, confidential tokens, vault shares, wrapped tokens)
- New balance-modifying transactors (escrow, stake, lock, convert)
- New flag-mutation transactors (DynamicMPT, compliance toggles)
- New per-holder state fields (encrypted balances, auditor keys, pending claims)

## The Triad

A valid M-08 finding answers **yes** to all three:

### (1) Holder action
- Can an untrusted party cheaply pre-plant persistent state on their account / token / issuance?
- Is the cost ≤ a few transaction fees + XRP/gas reserve?
- Does the state look harmless to naïve observers (e.g. "just an escrow", "just a converted-back balance")?

### (2) Issuer/admin action
- Is there a privileged operation whose correctness / success depends on the holder's state being in a "clean" configuration?
- Examples: clawback expects `balance > 0`, destroy expects `supply == 0`, flag-clear expects `no outstanding state`.

### (3) Failure mode
- When the planted state is present, does the admin action:
  - **Brick** subsequent operations (invariant trips every touch)?
  - **Silently fail** (returns success code but effect is no-op)?
  - **Partially apply** (leaves inconsistent state)?
- Any of the three = finding.

## Process

1. **Enumerate privileged operations** on the surface under review.
2. **For each**, identify what holder-side state it reads / depends on.
3. **Ask**: "Can a holder move, wrap, lock, convert, or otherwise mutate that state to a form that defeats the operation's assumption?"
4. **Validate with a PoC**: sequence the planting transaction(s) → admin action → assert failure code.
5. **Check permanence**: is the planted state recoverable by the holder (they can cooperate) or truly uncancellable (cryptographic commitment / time-lock with no cancel)?

## Cross-language mapping

### EVM / Solidity
| Planting mechanism | Admin op defeated |
|---------------------|-------------------|
| Holder wraps tokens in a Timelock contract | `Token.forceTransfer(from, to, amount)` sees zero balance |
| Holder delegates voting power to self via snapshot-time race | Governance admin's veto window expires with stale quorum |
| Holder stakes LP into "locked forever" escrow | AMM admin's emergency rebalance fails funding check |
| Holder transfers to a contract with selfdestruct prevention | Admin whitelist-remove gets orphan balance |

### Solana / Rust
| Planting mechanism | Admin op defeated |
|---------------------|-------------------|
| Holder closes their ATA (legitimate) | `freeze_account` errors on missing account |
| Holder delegates SPL to escrow PDA | Issuer's `freeze_account` freezes empty ATA |
| Holder makes their MintAuthority a program-only PDA | Mint admin's `set_authority` to new owner fails permission |

### Move / Aptos & Sui
| Planting mechanism | Admin op defeated |
|---------------------|-------------------|
| Holder wraps `Coin<T>` in a Capability-gated vault | `burn_from` hits wrapper, not underlying balance |
| Holder creates a Ref (TransferRef / BurnRef) without relinquishing | Future admin op expecting single owner fails |

### Soroban / Stellar
| Planting mechanism | Admin op defeated |
|---------------------|-------------------|
| Holder locks assets in ClaimableBalance with revoke-claim conditions | `clawback_claimable_balance` requires revoked-auth path |
| Holder uses sponsorship to attach a data entry that requires their signature | Admin's `remove_account` is blocked |

### C++ / XRPL (validated origin)
| Finding | Planting mechanism | Admin op defeated |
|---------|---------------------|-------------------|
| ESC-1 | Uncancellable escrow of entire MPT balance | Issuer `Clawback` sees transparent balance = 0 |
| ESC-2 | Dust escrow (1 MPT unit, uncancellable) | Issuer `MPTokenIssuanceDestroy` blocked (`sfLockedAmount > 0`) |
| ESC-3 | Escrow of vault shares | Asset-issuer `VaultClawback` sees share balance = 0 |
| CONF-1 | Convert→MergeInbox→ConvertBack round-trip leaves encrypted-zero fields | Issuer clears `CanConfidentialAmount`; any subsequent tx on the bricked MPToken fails `tecINVARIANT_FAILED` |

## PoC skeleton (language-agnostic)

```
Test: {ADMIN_OP_NAME} defeated by {PLANTING_MECHANISM}

Setup:
    admin = create admin/issuer
    holder = create untrusted holder
    admin.create_asset_or_deploy(flags_that_allow_planting)
    admin.transfer(holder, initial_amount)

Plant:
    holder.{plant_state}()    # e.g. escrow, wrap, convert-roundtrip

Assert pre-state:
    assert holder.{planted_view} != 0           # state is present
    assert holder.{admin_visible_view} == 0    # admin sees zero (or bricked)

Attempt admin op:
    expect(admin.{op}(holder, target), {ERROR_CODE})

Assert state is stuck:
    attempt(holder.self_recovery(), FAILS or uncooperative_required)
    attempt(admin.{op_again}(), SAME_ERROR)    # permanent
```

## Anti-patterns

- **Self-griefing ≠ M-08**. If the holder's action only harms themselves (e.g. they can't withdraw), that's not a finding — the holder chose that.
- **Requires-admin-cooperation ≠ M-08**. If the planted state is escape-able by the holder on request, it's an inconvenience, not a bug.
- **"By design" traps**. If the protocol DOCUMENTS that holders can block certain ops (e.g. "holders may decline to unfreeze"), that's not a finding. But **check carefully**: "issuer compliance is trusted not to misuse" does NOT imply "holder is trusted not to defeat compliance".

## Related methodology

- **M-03** (inverse-trust) is the higher-level framing; M-08 is the concrete planting template.
- **M-09** (SYNC_GAP) often identifies the crack that M-08 plants exploit (e.g. aggregate counter reads clean while per-entity state is dirty).
- **M-04** (feature-pool coverage) needed when root cause is in shared infra.

## ROI data

This template is the single highest-value finding generator in the XRPL audit. 4 of 4 Medium submission-ready findings trace to it, across 2 reward pools (MPT DEX and Confidential MPT). Apply it systematically to every new token-state transactor.
