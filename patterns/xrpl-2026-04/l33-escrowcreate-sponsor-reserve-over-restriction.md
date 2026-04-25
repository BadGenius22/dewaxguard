# L-33: `EscrowCreate` Sponsor-Reserve Over-Restriction (XLS-0068)

**Audit**: XRPL Sherlock, April 2026 | **Severity**: Low (POC-PASS verified) | **Feature Pool**: Sponsored Fees and Reserves (XLS-0068)

## Submission status

**PENDING user decision** as of audit closure. Discovered via Domain 19 Math Precision agent (originally tagged MP-1). Submission would restore reward pool coverage from **2/5 → 3/5** (XLS-0068 currently uncovered after L-32 was held). Verified by direct delta diff against `rippled-prev/` (`6d1a5be`) — root cause is NEW code in the April 2026 delta.

## Attack template

**Sponsor-aware helper called with `{}` instead of the in-scope sponsor handle**. The new `checkInsufficientReserve(view, tx, sle, balance, sponsorSle, ownerCountDelta)` helper has a sponsor-branch and a no-sponsor-branch. When a caller passes `{}` for `sponsorSle` while still requesting `ownerCountDelta=1`, the no-sponsor branch over-counts `ownerReserveUnits` by exactly 1 `incrementReserve` for sponsored submitters — rejecting legitimate sponsored XLS-0068 transactions at the boundary band.

## One-line

`EscrowCreate.cpp:410-414` (XRP-only post-amount-deduction check) passes `{}` for `sponsorSle` to `checkInsufficientReserve`, while `EscrowCreate.cpp:401-404` (first check) and the analogous `PaymentChannelCreate.cpp:73-74` correctly pass `sponsor`. The `{}` forces the no-sponsor branch (`View.cpp:361-371`), over-counting `ownerReserveUnits` by 1 `incrementReserve` (~2 XRP) for sponsored submitters.

## Root cause

```cpp
// rippled/src/libxrpl/tx/transactors/escrow/EscrowCreate.cpp:398-414 (current — buggy)
auto const balance = sle->getFieldAmount(sfBalance).xrp();
auto const sponsor = getTxReserveSponsor(view(), ctx_.tx);
if (auto const ret = checkInsufficientReserve(
        ctx_.view(), ctx_.tx, sle, balance, sponsor, 1);   // ✓ sponsor passed
    !isTesSuccess(ret))
    return ret;

if (isXRP(amount))
{
    if (auto const ret = checkInsufficientReserve(
            ctx_.view(), ctx_.tx, sle, balance - STAmount(amount).xrp(),
            {}, 1);                                          // ✗ {} forces no-sponsor branch
        !isTesSuccess(ret))
        return tecUNFUNDED;
}
```

Cross-site comparison was the dispositive evidence:

| Site | Sponsor param | `ownerCountDelta` | Correct? |
|---|---|---|---|
| `EscrowCreate.cpp:401-404` (first check) | `sponsor` ✓ | 1 | ✓ |
| `EscrowCreate.cpp:410-414` (second check, XRP) | `{}` ✗ | 1 | **BUG (L-33)** |
| `PaymentChannelCreate.cpp:73-74` | `sponsor` ✓ | 1 | ✓ |
| `PaymentChannelFund.cpp:75-76` | `{}` | 0 (no new object) | ✓ (delta=0 cancels over-count) |
| `CredentialCreate.cpp:120-121` | `sponsor` ✓ | 1 | ✓ |
| `CredentialAccept.cpp:85-89` | `newSponsor` ✓ | 1 | ✓ |

`EscrowCreate.cpp:410-414` is the only site that combines `{}` + `ownerCountDelta=1` after a balance subtraction.

## Discovery path

Surfaced by Domain 19 Math Precision agent as **MP-1** while probing adjacent arithmetic sites during the Expiry Race Matrix scan (M-15). The agent was looking for time-gated reserve drift — found instead a sibling-site asymmetry. M-15's value here was indirect: it didn't directly find an expiry race, but probing the EscrowCreate reserve-accounting site under M-15 surfaced the parallel-site bug.

**Methodology lesson**: when a sponsor-aware helper accepts an OPTIONAL `sponsorSle` param, every caller must explicitly verify the param is not silently elided. Cross-site comparison (idiomatic pattern in `PaymentChannelCreate` vs deviation in `EscrowCreate`) is the dispositive evidence that "this caller forgot, that one didn't."

## Verification

`./xrpld --unittest=EscrowCreateSponsoredReserveOverRestriction` — **POC-PASS** (59 assertions, 0 failures) on current buggy code. Sanity check: top up alice by `+incReserve` → tx succeeds, confirming over-count is exactly 1 `incrementReserve` (not a generic balance-calc bug).

## Cross-language generalization

This is **silent-default-arg sponsor elision** — a defaulting/optional-parameter bug class that appears across languages whenever an authorization-aware helper has a "no auth" fallback path:

| Platform | Analog |
|---|---|
| **EVM** | `permit2.transferFrom(token, to, amount, witness)` — `witness` defaulted to empty bytes silently disables the witness binding. Cross-call comparison of `permit2`/`permit3` callers reveals which forgot. |
| **Solana** | Anchor `#[account(constraint = signer.is_some())]` vs `#[account(constraint = signer)]` — first compiles to no-op when `signer` is `Option::None`. |
| **Move** | `escrow::deposit(coin, &mut store, std::option::none())` for an optional `sponsor` param — recipient may default to caller, silently bypassing the sponsor's payment. |
| **Soroban** | `helper.deduct(env, balance, None::<&Sponsor>)` — Rust optionals at FFI boundary make the no-sponsor branch reachable from any caller that omits the param. |

## Audit heuristic (for future audits)

For every helper that accepts an optional auth/sponsor handle:
1. List ALL callers of the helper.
2. For each caller, determine whether the auth/sponsor is in scope (i.e., the caller has a non-null handle available).
3. If yes-in-scope but caller passes `{}` / `None` / `null` / default → flag immediately.
4. Compare against sibling/idiomatic callers (e.g., `PaymentChannelCreate` vs `EscrowCreate`). Asymmetric sponsor-passing across paired transactors is a high-confidence bug signal.

This is the **paired-transactor binding comparison** pattern (D-38 / F-42 family from D15) generalized: sibling transactors must use sibling auth idioms.

## Detection difficulty

- **Compiles**: YES (valid C++; `{}` is a valid `std::shared_ptr<SLE const>` default).
- **Static analysis**: NO direct rule. A custom linter for "function with optional auth handle: warn if caller has handle in scope but passes empty" would catch it.
- **Tests**: caught only if a test explicitly creates a sponsored XRP escrow at the narrow boundary band `[trueFloor, trueFloor + incReserve)`. Pre-delta tests had no sponsor concept; new delta tests cover the sponsor-Path but not the boundary.

## Lesson for future audits

When a NEW helper is introduced that consolidates pre-existing checks AND adds an optional auth/sponsor parameter, sweep ALL callers and verify the parameter is passed consistently. Cross-site comparison against the idiomatic caller is faster and higher-confidence than reasoning about each caller in isolation. M-15's structure (matrix-cell enumeration over interacting ops) gave the agent the discipline to enumerate every reserve-touching site, which surfaced the asymmetry.
