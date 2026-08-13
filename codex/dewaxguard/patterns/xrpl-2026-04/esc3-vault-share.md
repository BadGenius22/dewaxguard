# ESC-3: Vault Share Escrow Shields From VaultClawback

**Audit**: XRPL Sherlock, April 2026 | **Severity**: Medium | **Feature Pool**: MPT DEX (XLS-0082)

## Attack template

[M-08](../../methodology/M08-holder-plants-trap.md) holder-plants-trap. Discovered via [M-07](../../methodology/M07-post-finding-sweep.md) post-finding sweep of `accountHolds` callers, after ESC-1 validated the root cause.

## One-line

Vault shares are themselves MPTs with `CanEscrow` set unconditionally by `VaultCreate`. Holders escrow shares → asset-issuer's `VaultClawback` can't see share holdings → compliance defeated.

## Discovery origin

This finding was not in the initial breadth pass. It emerged from the **L-14 sweep**: after ESC-1 validated `accountHolds` has a blind spot for `sfLockedAmount`, the sweep spawned 3 agents to check all other callers. Vault's share-clawback path was the only productive hit (Lending and AMM were immune via F-15 pseudo-account rule).

## The triad

| Criterion | Instance |
|-----------|----------|
| (1) Holder action | Escrow vault shares with uncancellable crypto-condition |
| (2) Admin op | Asset-issuer's `VaultClawback` (pulls asset out of vault by burning shares) |
| (3) Failure mode | `tecINSUFFICIENT_FUNDS` at `accountSend` of shares to vault account — same F-13 path as ESC-1 |

## Cross-language generalization

Any layered-asset system where:
- A vault / wrapper issues receipt tokens against an underlying
- The underlying asset has clawback; the wrapper receipt inherits it
- Receipt tokens have the same locking / wrapping primitives as primary tokens
- The wrapper's clawback uses the same "balance-check helper" that has the blind spot

Examples:
- **EVM**: Yearn v3 vault shares subject to underlying's ERC-3643 `forceTransfer`; user locks vault shares in a Timelock.
- **Solana**: Meteora DLMM position NFTs; admin's remediation tx can't locate NFT in a user-owned escrow.
- **Move**: SUI deepbook LP object wrapped in Kiosk that requires owner to unlock.

## PoC structure

```
1. issuer.create_asset(with_clawback=true)
2. issuer.pay(holder, 1000)
3. vault_owner.create_vault(asset=issuer_asset)
4. holder.deposit(1000) -> gets 1000 shares
5. holder.create_offer(XRP, 100 shares)             // MPT DEX coverage tx
6. holder.escrow_create(
       self, 1000 shares, cb1, finish_after=far, cancel_after=NONE
   )
7. issuer.vault_clawback(holder, 1000)              // tecINSUFFICIENT_FUNDS
8. issuer.vault_clawback(holder, 0)                 // tecPRECISION_LOSS
9. vault_owner.delete_vault()                        // tecHAS_OBLIGATIONS
```

## Feature-pool classification

Vault is gated on `featureSingleAssetVault` (NOT reward-pool). BUT the share MPT inherits `featureMPTokensV2` semantics — and VaultCreate unconditionally sets `lsfMPTCanTrade` on shares, so the PoC includes an `OfferCreate` on vault shares (XLS-0082 tx) to bridge to MPT DEX reward pool.

## Key extracted lesson

**Sweep methodology win**. ESC-1 → L-14 sweep → ESC-3 in ~15 agent-minutes. Whenever a shared helper has a confirmed blind spot, sweep all callers. F-15 (pseudo-account immunity) filter reduces false positives.

## Recommended fix

Preferred: extend `accountHolds` to include locked balance when queried by privileged ops (fixes ESC-1/2/3 simultaneously).

## Related

- [ESC-1](esc1-clawback-shield.md) — validated the root cause this sweep extended
- [M-07](../../methodology/M07-post-finding-sweep.md) — the methodology that found this
