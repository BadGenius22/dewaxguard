# L-31: `accountDestAssets` IOU-vs-MPT DEST-Filter Asymmetry

**Audit**: XRPL Sherlock, April 2026 | **Severity**: Low | **Feature Pool**: MPT DEX (XLS-0082)

## Attack template

**Parallel-branch asymmetry**: a function has parallel branches for two asset types (IOU and MPT). The branches use *inconsistent* conditions for the "include asset" predicate. New code writes the NEW branch with a tighter/looser condition than the existing OLD branch; no test catches the asymmetry.

## One-line

`accountDestAssets` IOU branch at L63 includes trustlines with any capacity remaining (`saBalance < limit`). MPT branch at L78 requires `isZeroBalance() && !isMaxedOut()` — excluding holders with existing non-zero MPT balances from `path_find` destination-currency discovery.

## Root cause

`rippled/src/xrpld/rpc/detail/AccountAssets.cpp:50-89`:
```cpp
// IOU branch — capacity check only, mirrors pre-delta semantics
if (saBalance < rspEntry.getLimit())
    assets.insert(saBalance.get<Issue>().currency);

// MPT branch — asymmetric, requires ZERO balance
if (rspEntry.isZeroBalance() && !rspEntry.isMaxedOut())
    assets.insert(rspEntry.getMptID());
```

The SRC-path helper `accountSrcAssets` at L41 uses `!isZeroBalance() && !isMaxedOut()` (correct SRC-side semantic — needs some balance to send from). The DEST-path helper INVERTS `isZeroBalance()` rather than dropping it entirely — which would have been the correct mirror of the IOU branch.

Pre-delta (`rippled-prev/src/xrpld/rpc/detail/AccountCurrencies.cpp:40-65`): the function had NO MPT branch at all. The MPT branch is entirely new code in the delta, written with an incorrect condition.

## Observation channel

The bug is visible in `path_find` / `ripple_path_find` responses via the `destination_currencies` JSON array (populated by `accountDestAssets` at `PathRequest.cpp:195, 692`). NOT visible in the `alternatives` enumeration, because the Pathfinder algorithm uses separate discovery logic.

**PoC channel matters**: our original L-31 PoC asserted on `alternatives` — which was incorrect. The Domain 14 Periphery agent caught this and the PoC was corrected to assert on `destination_currencies`. This is a reminder that when a function has a narrow output surface (one JSON field), the PoC must assert on that surface specifically.

## Cross-language generalization

| Platform | Analog |
|---|---|
| **EVM** | ERC-20 / ERC-1155 parallel helpers where the enumeration function has type-specific inclusion predicates |
| **Solana** | SPL token account vs Token-2022 account enumeration with different "includable" conditions |
| **Move** | `Coin<T>` vs `FungibleAsset<T>` parallel iteration in balance-discovery helpers |

## Audit heuristic

For every parallel IOU/MPT / IOU/NFT / V1/V2 helper that has two branches for the same conceptual operation (include this asset type, transform this asset type, etc.), **write out the boolean condition for each branch side-by-side and verify they are semantic mirrors**. "Include if can receive more" → IOU uses `balance < limit`, MPT should use `!isMaxedOut()`. Any extra condition on one side (like `isZeroBalance`) is a bug unless there's an explicit-comment reason.

## Detection difficulty

- **Compiles**: YES
- **Static analysis**: NO (the condition is syntactically valid, no dead code)
- **Tests**: caught only if test explicitly compares `destination_currencies` for IOU vs MPT destination accounts with analogous non-zero holdings. Dev tests did NOT add such a comparison.

## Lesson for future audits

When a helper gains a parallel branch for a NEW asset type in a delta, write the side-by-side condition table BEFORE reading any tests. The test may encode the WRONG expectation (matching the buggy code), which makes test-oracle methodology (M-02 / Domain 14) less effective.
