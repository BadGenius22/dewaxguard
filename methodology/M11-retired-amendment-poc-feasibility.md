---
id: M-11
name: retired-amendment-poc-feasibility
trigger_type: code
trigger_grep: "retire_feature|hardfork|deprecated|grandfathered|legacy_branch"
trigger_languages: [all]
applies_to_protocol_types: [any]
---

# M-11: Retired-Amendment PoC Feasibility Check

**Origin**: XRPL Sherlock April 2026, Domain 7 (SPON-M1). A real code-level asymmetry in `SponsorshipTransfer` vs `SignerListSet` that would have been a Medium finding, but the pre-MultiSignReserve legacy code branch is unreachable via public transactions in a test environment because `MultiSignReserve` is `XRPL_RETIRE_FEATURE` (always-on, not disableable).

**One-line**: Before investing effort in a finding whose root cause is in a code path gated on a retired / hardfork-completed amendment's legacy state, verify PoC feasibility. If public transactions can't reach the legacy branch in a test environment, the finding fails contest PoC-mandatory rules.

## Double-OOS: retired legacy code is DOUBLY out-of-scope

Retired-amendment legacy branches typically fail TWO contest rules simultaneously:

1. **PoC feasibility** (this methodology): can't reach the branch via public tx in test env.
2. **"Unchanged legacy code = known issue"** (Sherlock April 2026 FAQ update): per the contest FAQ — *"if the impact existed in unchanged legacy code, it remains classified as a known issue."* Even if new code exposes the legacy bug to more users, the impact-source is still the legacy code, which is OOS.

When BOTH rules apply, the finding is doubly OOS. **SPON-M1 is the canonical example**: PoC-blocked (pre-MSR branch unreachable in test env) AND impact-source-blocked (buggy math lives in unchanged legacy `signerCountBasedOwnerCountDelta`, not in new `SponsorshipTransfer`).

Takeaway: before submitting a finding in any legacy-adjacent code path, verify BOTH (a) PoC can reach it via public tx, and (b) the impact-source code itself is in the NEW/CHANGED delta.

## Trigger

Apply whenever a finding's root-cause code path is gated on one of:
- `XRPL_RETIRE_FEATURE(X)` on XRPL (retired amendment — always active)
- `IF_HARDFORK_ACTIVE` / post-fork gating on EVM (legacy branch unreachable post-fork)
- Solana: a retired / replaced instruction variant
- Move: a deprecated function with `#[deprecated]` or similar
- Any "grandfathered" code path whose creation gate has been removed but legacy instances persist

## The Feasibility Matrix

```
                         | Test env can reach it? | Public-tx PoC works? | Sherlock-acceptable? |
-------------------------|------------------------|----------------------|----------------------|
Active branch            | ✅                     | ✅                   | ✅                   |
Retired-amendment legacy | ❌ (toggle gone)       | ❌ (direct SLE only) | ❌ (violates rules)  |
Pre-hardfork legacy      | ❌ (fork always on)    | ❌ same              | ❌ same              |
```

## Process

1. **Identify the gate**: grep the root-cause code for amendment / hardfork / feature-flag checks.
2. **Determine gate status**:
   - Retired? (XRPL: `XRPL_RETIRE_FEATURE`; EVM: hardfork activation block past; Solana: replaced in native program upgrade.)
   - Active but toggleable? (OK — proceed to PoC.)
3. **If retired**: can public transactions still REACH the legacy-state branch?
   - Usually NO — the retirement implies the legacy path is only reachable for state created BEFORE retirement.
   - New state in a test environment always takes the post-retirement path.
4. **If unreachable via public tx**:
   - Document as **protocol-team informational** (not Sherlock submittable).
   - Do NOT attempt to force the PoC via direct-SLE writes / ledger-entry forging / setup-only test helpers — these violate "public transactions only" PoC rules on most contest platforms.
   - Do NOT submit anyway — invalid PoC hurts Watson score more than documenting the observation helps.

## Cross-language mapping

### EVM / Solidity

| Retired surface | PoC feasibility |
|-----------------|-----------------|
| Pre-Shanghai `SELFDESTRUCT` refund behavior | Unreachable — all forks past Shanghai |
| Legacy `tx.origin` auth patterns pre-EIP-3074 | Still reachable (EIP not yet universal) |
| Pre-Constantinople `CREATE2` semantics | Unreachable via public deployment |

### Solana / Rust

| Retired surface | PoC feasibility |
|-----------------|-----------------|
| Retired SPL instruction variants | Unreachable via CPI post-upgrade |
| Legacy account-data formats pre-realloc | Unreachable for new accounts |

### Move / Aptos / Sui

| Retired surface | PoC feasibility |
|-----------------|-----------------|
| Deprecated module versions | Usually unreachable via public entry functions |
| Legacy Capability types | Only reachable if held from pre-upgrade |

### C++ / XRPL (validated origin)

| Retired feature | PoC feasibility on test env |
|-----------------|------------------------------|
| `MultiSignReserve` retired (pre-MSR SignerList path) | Unreachable — gate permanently on, SLE flag always set |
| `MPTokensV1` — still active (not retired) | Reachable ✓ |

## Validated finding

**SPON-M1** (XRPL Sherlock April 2026, not submitted):
- Real asymmetry: `SponsorshipTransfer::getLedgerEntryOwnerCount` returns 1 for SignerList; `SignerListSet::removeSignersFromLedger` returns -(2+N) for pre-MSR SL. Inflates sponsor's ltSponsorship.sfReserveCount by N+1.
- PoC required pre-MSR SignerList (lsfOneOwnerCount=0). MultiSignReserve retired → all test-env SLs have lsfOneOwnerCount=1 → pre-MSR branch unreachable.
- Result: documented for protocol team; NOT submitted to Sherlock.

## Anti-patterns

- **Don't force a PoC via direct state manipulation**. Writing SLEs via `env.app()->openLedger()->insert()` works in-framework but violates contest PoC rules.
- **Don't submit without a PoC on "it's conceptually valid"**. Sherlock / C4 / Cantina all reject findings without runnable PoCs.
- **Don't ignore the lead**. Document it for the protocol team — the bug is real even if Sherlock-invalid. Future codebases may have similar patterns where the PoC IS feasible.

## Related methodology

- **M-10** (prior-audit dedup) — pairs with M-11: both are pre-submission sanity checks.
- **M-04** (feature-pool coverage) — if a finding needs cross-feature PoC extension AND the legacy branch is unreachable, neither can be worked around.
