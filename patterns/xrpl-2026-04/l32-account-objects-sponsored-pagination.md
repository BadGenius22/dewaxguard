# L-32: `account_objects sponsored` Filter Drains Pagination Limit

**Audit**: XRPL Sherlock, April 2026 | **Severity**: Low (risky, contested OOS) | **Feature Pool**: Sponsored Fees (XLS-0068)

## Submission status

**NOT SUBMITTED as of audit closure**. This finding is in the [M-14](../../methodology/M14-elevated-impact-vs-unchanged-legacy.md) decision zone: the buggy code at `AccountObjects.cpp:223` is UNCHANGED from pre-delta (pre-delta `rippled-prev/.../AccountObjects.cpp:184` has the same `if (++i == mlimit)` placement), but a NEW `sponsored=` filter introduced in the delta makes the pre-existing pagination drain bug into a common-case scenario. See M-14 for the risk analysis.

## Attack template

**Pagination-drain via filter predicate applied after counter increment**. A loop increments a counter on every iteration (pre-filter) and stops when the counter hits the user-specified `limit`. If the filter rejects entries, they count against the user's `limit` but produce no output — leading to empty or short pages.

## One-line

`AccountObjects::doAccountObjects` loop at `AccountObjects.cpp:220-225` appends to `jvObjects` only if `canAppend` is true, but increments `++i` on every iteration. User requests `limit=10` with `sponsored=true`; if the first 10 directory entries are non-sponsored, the loop stops with 0 objects and a marker.

## Root cause

`rippled/src/xrpld/rpc/handlers/account/AccountObjects.cpp:195-225`:
```cpp
for (; iter != entries.end(); ++iter)
{
    auto const sleNode = ledger.read(keylet::child(*iter));
    bool canAppend = true;

    if (typeFilter.has_value() && !typeMatchesFilter(...))
        canAppend = false;

    if (sponsored.has_value() && !sponsoredMatchesFilter(sponsored.value(), sponsor))
        canAppend = false;

    if (canAppend)
        jvObjects.append(sleNode->getJson(JsonOptions::none));

    if (++i == mlimit)   // <-- bug: increments regardless of canAppend
    {
        // set marker and return
    }
}
```

**Pre-delta (UNCHANGED SITE)**: `rippled-prev/.../AccountObjects.cpp:184` had the same `if (++i == mlimit)` at the same structural position, pre-dating the `sponsored` filter. The only filter then was `typeFilter`, which is typically narrow enough that page-exhaustion was an edge case.

**What the delta introduced**: the new `sponsored=true/false` filter (gated on `featureSingleAssetVault` / XLS-0068 integration). This filter can reject entire pages of directory entries for typical accounts (most accounts have few sponsored objects), making the pagination drain a common-case failure rather than a rare edge case.

## The M-14 argument (why it might be IN-SCOPE despite unchanged code)

1. **Pre-delta reachability**: `typeFilter`-based drain was rare. Most users don't use `typeFilter` or use it with types that match the common case.
2. **Post-delta reachability**: `sponsored=true` is the primary discovery mechanism for XLS-0068 sponsorship auditing — a core use case. Typical accounts have ~0-5 sponsored objects out of dozens total. The drain is near-universal on any typical account.
3. **Elevation ratio**: rough estimate 10-100x increase in hit rate for typical users.
4. **Reward pool fit**: if accepted, restores XLS-0068 to the covered-pool set. If rejected, no pool change.

## Dedup status

- Kuprum known-issues index: **clean** — no entry mentions `account_objects` pagination or the sponsored filter specifically.
- Prior audits (Halborn Batch / Halborn MPT DEX / FYEO PD / FYEO Sponsored): **clean**.
- Cpp.md known-issue baseline: **clean**.

## Cross-language generalization

This is **filter-counter ordering** — a classic pagination bug that has appeared in many systems:

| Platform | Analog |
|---|---|
| **EVM** | Subgraph / indexer pagination where a post-fetch filter drains the `first` limit |
| **Solana** | getProgramAccounts with dataSlice filter — client-side filter drains serverside limit |
| **SQL** | `LIMIT N WHERE filter` vs `(SELECT ... WHERE filter) LIMIT N` — the latter is correct |
| **Move** | No common instance; Move has less RPC-surface exposure to this pattern |

## Audit heuristic

For every paginated iterator with multiple filter predicates:
1. Verify `++counter` is inside the `if (passesAllFilters) { append; ++counter; }` block, NOT after the append block.
2. If `++counter` is outside, check ALL filter predicates — each one creates the drain condition.
3. If the loop is pre-delta and at least ONE new filter is introduced in the delta, apply M-14 ELEVATED-IMPACT analysis.

## Detection difficulty

- **Compiles**: YES (valid code, no warnings)
- **Static analysis**: NO (pattern is not a dead-code or use-after-free — just semantically wrong)
- **Tests**: caught only if a test explicitly constructs `N+1` non-matching entries before `1` matching entry, with `limit=N`, and asserts the matching entry is returned. XRPL's `testSponsoredFilter()` did NOT include pagination coverage.

## Lesson for future audits

When a NEW filter option is added to an EXISTING paginated RPC, apply M-14 to the unchanged pagination-counter placement. The filter's newness makes the pre-existing drain a new user-facing regression even if the counter line is unchanged.
