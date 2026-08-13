---
id: M-12
name: granular-permission-sandbox
trigger_type: code
trigger_grep: "granular_permission|checkgranularsemantics|onlyrole|accesscontrol|access_control|capability<|delegateset|permissionmask"
trigger_languages: [all]
applies_to_protocol_types: [any]
---

# M-12: Granular Permission Sandbox ↔ Semantic Override Audit

**Origin**: XRPL Sherlock April 2026, Domain 6 (DEL-1). A 5th Medium finding where XLS-0075 v1.1's new granular-permission sandbox enforces syntactic field/flag templates but defaults the per-transactor semantic hook to permissive. `SponsorshipSet` lacks the override → delegate granted narrow `SponsorFee` permission can CREATE arbitrary new sponsorships, draining principal's XRP.

**One-line**: Whenever a system introduces "capability templates" / "per-op permission masks" / "granular delegation", audit every entry for a semantic-override check. The default (permissive) is almost always the bug.

## Trigger

Apply whenever:
- The codebase introduces per-op or per-field **capability templates** (bitmasks, structs, inherited-authority patterns).
- The auth enforcement has a **two-layer pattern**: syntactic (template-match) + semantic (per-transactor custom rule).
- The **semantic layer has a default** that callers can skip by not implementing.

## The Triad (Scope-Creep Pattern)

| Layer | Enforces | Default if unchecked |
|-------|----------|----------------------|
| **Sandbox / template** | Fields / flags are WITHIN the permission's declared scope | Tight — only allowed tx fields pass |
| **Semantic hook** | State-level invariants (e.g. "object must exist", "amount must not exceed baseline") | **Permissive — returns "OK" unless overridden** |
| **Transactor's own preflight / preclaim** | Tx-level validity (signatures, format) | Runs independently — doesn't substitute for the semantic hook |

Scope creep: the sandbox passes a tx that satisfies the TEMPLATE but violates the INTENT. Without a semantic override, the transactor runs.

## Process

1. **Enumerate** every granular / templated permission entry in the codebase.
   - XRPL: grep for `GRANULAR_PERMISSION` in `permissions.macro`.
   - EVM: grep for role-bitmask enums + custom `AccessControl` overrides.
   - Solana: grep for fine-grained authority instructions in programs.
   - Aptos: grep for per-operation Capability types.
2. **For each permission P → txType T mapping**:
   - Verify T overrides the semantic-check hook. XRPL: `T::checkGranularSemantics`. EVM: `T.beforeCall` / `validateCall`. Solana: instruction-level auth. Aptos: `assert!` at entry of the function.
   - If NOT overridden: default is permissive → SCOPE-CREEP candidate.
3. **For each candidate**, find a SIBLING transactor with a correct override as the reference pattern (e.g. `TrustSet` overrides `checkGranularSemantics` in XRPL; use it as the "correct implementation" baseline).
4. **Construct the attack**:
   - Delegate granted narrow permission P
   - Submits tx that satisfies template (syntactic sandbox passes)
   - But performs action outside P's INTENT (create new object vs. modify existing, etc.)
   - Semantic hook returns `tesSUCCESS` (permissive default)
   - Transactor's preflight / preclaim doesn't re-check the delegate's authority scope
   - Attack succeeds
5. **Validate with PoC**: setup, delegate-signs-tx, assert state transition that should be unauthorized.

## Cross-language mapping

### EVM / Solidity
- **Pattern**: OpenZeppelin's `AccessControl` with `onlyRole(MODERATOR_ROLE)` guards but no per-function scope narrowing. A role granting "pause individual user" may also allow "pause whole protocol" if the guard is only role-level.
- **Audit probe**: every `onlyRole` modifier — is there a per-operation scope check too? Or does the role grant the full function?

### Solana / Rust
- **Pattern**: Anchor `#[access_control]` attribute that validates the signer holds a specific Capability / Authority. Does the instruction ALSO validate the scope (e.g. "this Capability allows only withdrawing from account X, not Y")?
- **Audit probe**: every Anchor `access_control` — does it check the TARGET, not just the CALLER?

### Move / Aptos
- **Pattern**: fine-grained `Capability<T>` objects gated by `has key` traits. A `SpendingCapability<Coin<USDC>>` may or may not enforce amount limits.
- **Audit probe**: every capability's `borrow_global_mut` call — is the scope narrowed?

### C++ / XRPL (validated origin)
- **Pattern**: `GRANULAR_PERMISSION(name, txType, value, allowedFlags, allowedFields)` + `Transactor::checkGranularSemantics<T>()`.
- **DEL-1 case**: `SponsorFee` / `SponsorReserve` granular permissions for `SponsorshipSet`. Sandbox template allows fields {sfFeeAmount, sfSponsee, sfCounterpartySponsor}. No `checkGranularSemantics` override on `SponsorshipSet`. Compare to `TrustSet` which overrides to require pre-existing trustline.

## Validated finding

**DEL-1** (XRPL Sherlock April 2026, submitted):
- Root cause: `SponsorshipSet` lacks `checkGranularSemantics` override → `tesSUCCESS` default → delegate with `SponsorFee` creates new sponsorship to attacker-chosen sponsee with 50,000 XRP fee amount.
- PoC validated: Alice lost 50,000 XRP to attacker-controlled sponsorship via 1 delegate tx.
- Feature label: **Permission Delegation (XLS-0075) reward pool**.
- Fix pattern: add `checkGranularSemantics` override matching `TrustSet.cpp:109-137` ("must exist" + "field-unchanged" guards).

## Checklist

When auditing a new granular-permission system:

```
[ ] Enumerate all granular / templated permissions
[ ] For each: identify target transactor / function
[ ] For each: verify semantic-override hook is implemented (not just default)
[ ] Cross-compare to "known-correct" sibling (find one via grep for the hook override)
[ ] For every un-overridden entry: M-08 style probe
    [ ] Can delegate with this permission create new state that the principal didn't intend?
    [ ] Can delegate target a different account / object / ID than what the grant implied?
    [ ] Can delegate bundle operations (Batch / multi-instruction) to amplify scope?
[ ] Quantify impact: what's the worst-case loss per attack execution?
```

## Anti-patterns

- **Don't assume "the default is safe"**. Default-permissive is almost always the bug. If it were safe by default, there'd be no need for the override mechanism.
- **Don't treat sandbox template match as sufficient**. Syntactic fields-allowed ≠ semantic intent-satisfied.
- **Don't skip the "find a sibling with correct override" step**. Without a template-correct example, the reviewer can't argue "this pattern should exist here too". The sibling is your submission's anchor.

## Related methodology

- **M-03** (inverse-trust) is the upstream framing: who trusts whom, what scope is granted.
- **M-08** (holder-plants-trap) is the upstream attack template: DEL-1 is an M-08 instance where the "trap" is the mere grant of an under-constrained permission.
- **M-10** (dedup) — check that the sibling you found as reference isn't also buggy (otherwise you're arguing for a pattern that has its own bug).

## ROI

**1 of 5 Medium findings** from the XRPL audit used M-12 — but it hit an otherwise-unhit reward pool (Permission Delegation). For contests with per-feature-pool rewards, M-12 has disproportionate value. It unlocked the 3rd of 5 pools.
