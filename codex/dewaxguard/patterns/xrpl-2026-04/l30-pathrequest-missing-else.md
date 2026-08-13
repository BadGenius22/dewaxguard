# L-30: Missing `else` in PathRequest Source-Issuer Selection

**Audit**: XRPL Sherlock, April 2026 | **Severity**: Low | **Feature Pool**: MPT DEX (XLS-0082)

## Attack template

Refactor regression. An MPT-aware refactor wrapped a Currency/MPT visitor lambda around an existing `if / else if / else` chain and lost the third `else` keyword. The third block became a free unconditional statement.

## One-line

`PathRequest::parseJson` inserts `{currency, *raSrcAccount}` into `sciSourceAssets` unconditionally on every `source_currencies` entry, in addition to the user-requested issuer — regardless of which earlier `if`/`else if` branch fired.

## Root cause

`rippled/src/xrpld/rpc/detail/PathRequest.cpp:400-412`:
```cpp
srcPathAsset.visit(
    [&](Currency const& currency) {
        if (srcIssuerID != *raSrcAccount) { /* branch 1 */ }
        else if (saSendMax->getIssuer() != *raSrcAccount) { /* branch 2 */ }
        {   // <-- MISSING `else` — runs unconditionally
            sciSourceAssets.insert(Issue{currency, *raSrcAccount});
        }
    },
    [&](MPTID const& mpt) { sciSourceAssets.insert(mpt); });
```

Pre-delta (`rippled-prev/src/xrpld/rpc/detail/PathRequest.cpp:376-387`) had a correct `if / else if / else` chain operating on `sciSourceCurrencies`. The MPT-refactor to `sciSourceAssets` + `PathAsset::visit` dropped the keyword.

## Lesson for future audits

**Variant-refactor regressions**: any PR that migrates a strongly-typed container (`set<X>`) to a variant-based container (`set<variant<X, Y>>`) via lambda wrapping is a high-risk refactor site. Review every `if/else if/else` chain that is now INSIDE a lambda — the lambda body braces can accidentally swallow the `else` keyword structure if the reformatter is not careful.

## Cross-language generalization

| Platform | Analog |
|---|---|
| **EVM** | Struct-field refactor where `Issue{currency, issuer}` → `Asset(type, data)` union wrapping — any `if/else if/else` on the asset type inside the new union handler has refactor-regression risk |
| **Solana** | Account-type discriminator refactors (`AccountType` → `AccountType::V2`) where legacy branches are wrapped in match arms |
| **Move** | `Coin<T>` → `Asset<T>` generic wrapping |

## Audit heuristic

When you see a diff where a variant visitor / enum match / type-dispatch pattern is NEW in the delta, **read every else chain inside the new handler** by pasting the pre-delta source next to the post-delta source. Token-level side-by-side. Looking for: any block that has opening `{` but no preceding keyword (if/else/switch case).

## Detection difficulty

- **Compiles**: YES (free block is valid C++)
- **Static analysis**: MAYBE — cppcheck / clang-tidy may flag "statement has no effect" style warnings depending on the block contents, but a single `insert()` call doesn't trigger that
- **Tests**: only caught if test explicitly counts entries in the affected container AND a diff vs pre-delta output exists. XRPL team did NOT add such a test.

The dev test added in the delta (`PathRequest_test.cpp` testcases) did not check `sciSourceAssets.size()` post-parse.
