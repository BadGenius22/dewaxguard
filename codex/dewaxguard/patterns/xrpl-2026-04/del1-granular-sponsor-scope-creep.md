# DEL-1: Granular SponsorFee / SponsorReserve Scope Creep

**Audit**: XRPL Sherlock, April 2026 | **Severity**: Medium | **Feature Pool**: Permission Delegation (XLS-0075)

## ⚠️ Submission status (updated 2026-04-23)

**NOT SUBMITTED — classified OOS as duplicate of public known issue [XRPLF/rippled#6890](https://github.com/XRPLF/rippled/issues/6890)** "SponsorFee granular permission allows delegate to create self-benefiting fee sponsorship, redirecting principal's XRP", **created 2026-04-12 16:27:52 UTC** — ~22.5 hours BEFORE contest start (2026-04-13 15:00 UTC). Discovered via [M-13](../../methodology/M13-kuprum-known-issue-index-ingestion.md) kuprum-index ingestion mid-audit.

- **Root cause match**: identical (SponsorshipSet missing `checkGranularSemantics` override + `sfSponsee` in granular template)
- **Site match**: identical (`permissions.macro:82-88`, `SponsorshipSet.cpp:187-194`, `Transactor.h:227-234`)
- **Recommendation match**: identical (add override or remove `sfSponsee` from template)

**Methodology implications still valid**: M-12 (granular permission sandbox) is still the correct attack-template; this instance was just discovered first by another researcher. The next granular-permission contest on ANY platform should still use M-12.

**Pool coverage impact**: XRPL April 2026 submission reduced from 5 Mediums / 3 pools → 4 Mediums / 2 pools. Permission Delegation (XLS-0075) no longer hit.

---

(Original pattern writeup preserved below for methodology reference)

## Attack templates

[M-12](../../methodology/M12-granular-permission-sandbox.md) granular permission scope creep — **the canonical example**.

## One-line

V1.1 Permission Delegation introduces granular permissions (`SponsorFee`, `SponsorReserve`) with per-field sandbox templates. `SponsorshipSet` doesn't override `checkGranularSemantics` → default returns `tesSUCCESS` → delegate granted narrow "manage fees" permission can CREATE arbitrary new sponsorships, draining principal's XRP.

## The scope-creep triad

| M-12 layer | Behavior in DEL-1 |
|------------|-------------------|
| **Sandbox / template** (syntactic) | `SponsorFee` template allows fields `{sfFeeAmount, sfMaxFee, sfSponsee, sfCounterpartySponsor}`. Delegate's tx matches — sandbox passes. |
| **Semantic hook** (per-transactor override) | **`SponsorshipSet` doesn't override** `checkGranularSemantics`. Base-class default at `Transactor.h:227-234` returns `tesSUCCESS`. |
| **Transactor preflight/preclaim** | Doesn't distinguish delegate-initiated from principal-initiated. `doApply` runs the CREATE branch if no existing sponsorship exists. |

Result: delegate uses narrow-scope permission to reach broader state-creation surface.

## Sibling with correct override

`TrustSet.cpp:109-137` — the pattern that SHOULD exist on `SponsorshipSet`:
```cpp
if (!sleRippleState)
    return terNO_DELEGATE_PERMISSION;   // cannot CREATE
if (curLimit != saLimitAllow)
    return terNO_DELEGATE_PERMISSION;   // cannot change limit
```

## Cross-language generalization

Every system with capability templates / per-op permission masks is a candidate:

### EVM / Solidity
- **OpenZeppelin AccessControl**: role-based guards that check the role, not the scope. A role granting `pauseUser` may also allow `pauseProtocol` if guard is only `onlyRole(MODERATOR)`.
- **Diamond (EIP-2535) facet selection**: granular-facet auth often defaults to "signer has facet access" without checking per-function scope.

### Solana / Rust
- **Anchor `#[access_control]`**: if it only validates the signer holds an authority, without validating the authority's scope against the instruction's target, scope creep emerges.

### Move / Aptos
- **Capability types**: `SpendingCapability<T>` may not enforce amount limits at the type level; the enforcement depends on the consumer's implementation.

## PoC structure (abstracted)

```
1. principal.grant_granular_permission(delegate, "narrow_op")
2. delegate.submit_tx_as_delegate(
       broad_op,                             # exceeds grant's scope
       target = attacker_chosen_new_entity,
   )
3. assert delegate's tx succeeded (sandbox passed, semantic hook default-permissive)
4. assert principal's state modified beyond granted scope
```

## Impact

- **Financial loss via `SponsorFee` path**: attacker creates Alice→Mallory sponsorship with `sfFeeAmount = 50000 XRP`. Alice's balance debited 50,000 XRP. Recoverable via `SponsorshipSet tfDeleteObject` if Alice notices.
- **Reserve lock via `SponsorReserve` path**: attacker creates sponsorship with `sfReserveCount = 100`. Mallory (colluder) can consume 100 reserve slots from Alice's budget.
- **Repeatable**: attack succeeds until Alice submits `DelegateSet` revoking the granular permission.

## Dedup verdict (April 2026)

- FYEO Permission Delegation v1.0: **clean** — audited pre-granular-sandbox v1.0 (4 findings: shadowed variable, optimization, exchange concerns, empty DelegateSet).
- Other 3 prior audits: **unrelated scope**.
- GitHub baseline #6863/67/75/84/94/95/908: **clean** — none reference granular-sandbox or `checkGranularSemantics`.

## Recommended fix

Add `checkGranularSemantics` override to `SponsorshipSet` matching `TrustSet` pattern:

```cpp
// SponsorshipSet.cpp (new method)
NotTEC
SponsorshipSet::checkGranularSemantics(
    ReadView const& view, STTx const& tx,
    std::unordered_set<GranularPermissionType> const&)
{
    auto const sponsor = tx[~sfCounterpartySponsor].value_or(tx[sfAccount]);
    auto const sponsee = tx[~sfSponsee].value_or(tx[sfAccount]);
    if (!view.read(keylet::sponsor(sponsor, sponsee)))
        return terNO_DELEGATE_PERMISSION;   // cannot CREATE
    if (tx[sfFlags] & tfDeleteObject)
        return terNO_DELEGATE_PERMISSION;   // cannot DELETE
    return tesSUCCESS;
}
```

Plus: compile-time or code-review rule that every `GRANULAR_PERMISSION` entry must have an override or explicit documentation of why default-permissive is safe.

## Key extracted lesson

**Whenever a contest introduces granular / templated permissions, enumerate every entry and verify semantic-override presence**. Missing overrides = M-12 finding candidate. In the XRPL audit, DEL-1 was the 5th Medium and hit the 3rd reward pool (Permission Delegation) — disproportionate value for future pool-diversification plays.

## Related

- [M-12 methodology](../../methodology/M12-granular-permission-sandbox.md) — the generalized template
- [ESC-1/2/3, CONF-1](INDEX.md) — the 4 M-08-pattern findings from the same audit
- Sibling pattern: `TrustSet::checkGranularSemantics` at `TrustSet.cpp:109-137`
