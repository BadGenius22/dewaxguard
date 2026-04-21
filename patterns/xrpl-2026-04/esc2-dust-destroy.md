# ESC-2: Dust Escrow Permanently Blocks Issuance Destroy

**Audit**: XRPL Sherlock, April 2026 | **Severity**: Medium | **Feature Pool**: MPT DEX (XLS-0082)

## Attack template

[M-08](../../methodology/M08-holder-plants-trap.md) holder-plants-trap — variant targeting issuance lifecycle.

## One-line

1 unit of MPT + uncancellable escrow permanently blocks the issuer from calling `MPTokenIssuanceDestroy`. Cost: ~1 dust + 2 XRP reserve.

## The triad

| Criterion | Instance |
|-----------|----------|
| (1) Holder action | Escrow 1 MPT with crypto-condition, no `sfCancelAfter` |
| (2) Admin op | `MPTokenIssuanceDestroy` |
| (3) Failure mode | `tecHAS_OBLIGATIONS` (sfOutstandingAmount != 0 OR sfLockedAmount != 0) |

## Root cause

`MPTokenIssuanceDestroy.cpp:28-31` preclaim:
```cpp
if ((*sleMptIssuance)[sfOutstandingAmount] != 0 ||
    (*sleMptIssuance).isFieldPresent(sfLockedAmount))
    return tecHAS_OBLIGATIONS;
```
Both flags are bumped by `lockEscrowMPT` which runs at escrow creation time; neither is decremented without cooperation from the holder (escrow finish) or expiry (not set when `sfCancelAfter` is absent).

## Cross-language generalization

Any system where:
- Object destruction requires "all child state cleared"
- An untrusted party can create child state at negligible cost
- That state is not auto-expiring / auto-cleanup

Examples:
- **EVM**: UniswapV4 Hook where admin wants to deprecate a pool; user creates a tiny LP position that doesn't earn fees but blocks pool close.
- **Solana**: Anchor program where the admin wants to close the program; any account using `close = admin` that is never closed by its owner blocks the admin close.
- **Move**: Aptos resource-account deletion blocked by any leftover `Coin<T>` of 1 unit.

## PoC structure

```
1. admin.create_asset(with_escrow=true, with_transfer=true)
2. admin.pay(holder, 1)                              // 1 dust unit
3. holder.escrow_create(
       self, 1, cb1, finish_after=far, cancel_after=NONE
   )
4. admin.destroy()                                    // tecHAS_OBLIGATIONS
5. admin.cancel_escrow(holder)                        // tecNO_PERMISSION
6. admin.destroy()                                    // tecHAS_OBLIGATIONS (permanent)
```

## Feature-pool classification

Same as ESC-1 — root cause in `featureMPTokensV2`-gated code. PoC shares `testMPTDEXCoverage` coverage.

## Dedup verdict

All clean (same result as ESC-1).

## Recommended fix pattern

- **Option A**: grace-period cancel for escrows past an absolute maximum duration (e.g. 30 days).
- **Option B**: allow issuer to force-cancel escrows of their own asset.
- **Option C**: require `sfCancelAfter` on all escrows of non-XRP assets.

## Related

- [ESC-1](esc1-clawback-shield.md) — same mechanism, different admin op
- [ESC-3](esc3-vault-share.md) — same mechanism, vault shares
