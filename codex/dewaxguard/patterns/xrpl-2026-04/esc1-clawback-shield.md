# ESC-1: Clawback-Shield via Uncancellable Escrow

**Audit**: XRPL Sherlock, April 2026 | **Severity**: Medium | **Feature Pool**: MPT DEX (XLS-0082)

## Attack template

[M-08](../../methodology/M08-holder-plants-trap.md) holder-plants-trap — canonical example.

## One-line

`accountHolds(mpt)` reads only transparent balance (`sfMPTAmount`), excluding escrow-locked balance (`sfLockedAmount`). Holder escrows entire balance with uncancellable crypto-condition; issuer's Clawback sees balance = 0.

## The triad

| M-08 criterion | Instance |
|----------------|----------|
| (1) Holder action | `EscrowCreate` with `sfCondition = cb1`, no `sfCancelAfter`, `sfFinishAfter = far future`. Cost: 1 tx fee + 2 XRP reserve. |
| (2) Admin op | Issuer's `Clawback(holder, MPT, amount)` |
| (3) Failure mode | `tecINSUFFICIENT_FUNDS` — `accountHolds` returns 0 for a holder whose MPT is fully locked |

## Root cause

`rippled/src/libxrpl/ledger/helpers/TokenHelpers.cpp:328`:
```cpp
amount = STAmount{mptIssue, sleMpt->getFieldU64(sfMPTAmount)};  // transparent only
```
Does not add `sfLockedAmount`. Clawback transactor reads this via `accountHolds` at `Clawback.cpp:152-155`.

## Cross-language generalization

Any asset system with:
- An authority-level seizure primitive (`clawback`, `forceTransfer`, `freeze_and_redistribute`)
- A helper that reads "available balance" as a proxy for "total holdings"
- A user-controllable mechanism to move balance into a form not counted by the helper

Examples:
- **EVM**: ERC-3643 compliance token with `forceTransfer` that reads `balanceOf`; holder wraps in a Timelock.
- **Solana**: SPL Token 2022 with `freeze_account` that errors if ATA is empty; holder transfers to escrow PDA.
- **Move**: `coin::burn_from<T>` reads the direct `Coin<T>` resource; holder wraps in a Capability vault.

## PoC structure (abstracted)

```
// See full source in findings/ESC-1-*.md or
// scratchpad/dewaxguard-domain-04/MPTEscrowGrief_test.cpp

1. admin.create_asset(with_clawback=true, with_escrow=true)
2. admin.pay(holder, 1000)
3. holder.escrow_create(
       destination = self,
       amount = 1000,
       condition = cb1,                    // only holder knows pre-image
       finish_after = now + 100_000s,
       cancel_after = NONE,                // <- makes it uncancellable
   )
4. admin.clawback(holder, 1000)
   // Expect: INSUFFICIENT_FUNDS
5. admin.cancel_escrow()
   // Expect: NO_PERMISSION (no cancel_after)
6. admin.destroy_asset()
   // Expect: HAS_OBLIGATIONS (sfOutstandingAmount > 0)
```

## Feature-pool classification

Root cause code path gated on `featureMPTokensV2` (MPT DEX amendment). PoC extended with `testMPTDEXCoverage` case that uses `OfferCreate` (XLS-0082 signature tx) with `TakerGets=MPT` + cross-currency Payment via BookStep.

## Dedup verdict (April 2026 Sherlock)

- Halborn MPT DEX (ef128a): **clean** — covers XLS-82d AMM / XLS-33 MPT DoS, not escrow.
- Halborn Batch (420598): **clean** — unrelated.
- FYEO Permission Delegation: **clean** — unrelated.
- FYEO Sponsored Fees: **clean** — closest finding (FYEO-XRPL-03) is about sponsor-field attribution to wrong SLE, not balance accounting.
- GitHub baseline (#6863/67/75/84/94/95/908): **clean**.

## Recommended fix pattern

Two options, cross-language applicable:
- **Option A (preferred)**: modify the "available balance" helper to include locked / wrapped / escrowed balance when queried by privileged operations.
- **Option B**: refuse to create the planting mechanism (escrow, wrap) when the asset has the compliance flag (`CanClawback`) enabled. Blocks legitimate use cases.

## Related

- [ESC-2](esc2-dust-destroy.md) — same mechanism, different admin op
- [ESC-3](esc3-vault-share.md) — same mechanism, different token (vault shares)
- [CONF-1](conf1-flag-clear-brick.md) — different mechanism (SYNC_GAP), same attack class
