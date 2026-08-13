# Cross-Class Preflight Firewall

> **Defensive pattern.** When a system has multiple authority classes (delegate / sponsor / pseudo-account / privileged-role / admin / governance / multisig), each class must be validated at the **preflight phase** before reaching transactor-specific business logic. A missing class-validation in any single transactor introduces a finding-class bug, even when the same class is correctly checked in sibling transactors.
>
> **Validated origin**: XRPL Sherlock April 2026 — `MPTokenIssuanceSet` cross-field preflight rejects the entire combinatorial race space `{mutable-fields-presence} × {tx-flag-op}` at preflight, eliminating an attack surface before it can reach business-logic depth probes. Codified as the cross-language audit pattern below.

---

## The principle

In any system with multiple authority classes (each granting a distinct capability scope), the preflight phase is the single chokepoint where every class must be sanity-checked. Concretely:

- A **transactor / instruction / function entry-point** runs through preflight (cheap, no state mutation) before reaching doApply / business logic (expensive, state-mutating).
- Preflight is the natural location for cross-class validation: "this tx claims authority class X — does X actually grant the operation being requested?"
- When a single transactor omits the cross-class check, an attacker holding class X can submit ops that are **outside X's intended scope** but pass through the transactor's class-X-trusting business logic.

The bug class: **missing sibling check at preflight**. The audit smell: a privileged-role check appears in transactor A but is silently absent in sibling transactor B that ALSO accepts the same role.

## The audit test pattern

For every privileged-role / authority-class check found in any transactor, find a SIBLING transactor that ALSO accepts the same authority class. **If the sibling lacks the check, that's the bug.**

Concrete steps:

1. **Enumerate all authority classes** in the codebase (delegate, sponsor, pseudo-account, role-bitmask, capability-token, governance multisig, admin EOA).
2. **For each authority class C**, list every transactor / instruction that accepts C.
3. **For each transactor T accepting C**, locate the preflight check for C (call it `validate_C_preflight`).
4. **Cross-compare**: does every T in the list have an equivalent `validate_C_preflight` call? Or do some Ts trust C without re-validating?
5. **For every T that lacks the check**, construct an attacker scenario: actor holds C, submits a tx that exercises T, and verify whether T's business logic does anything that exceeds C's intended scope.

The pattern generalizes the M-12 (granular permission sandbox) finding: a granular permission grants narrow scope syntactically; missing the per-transactor semantic-override check means every transactor that doesn't override gets the permissive default.

## Cross-language examples

### EVM / Solidity — modifier stacking

Pattern: contracts use OpenZeppelin's `AccessControl` with `onlyRole(...)` modifiers stacked on each function. The preflight is the modifier evaluation order.

Failure mode: contract A has `onlyRole(MODERATOR_ROLE)` + a per-target check (`require(userPaused[user])`). Contract B (sibling, accepts the same role) has `onlyRole(MODERATOR_ROLE)` but NO per-target check — moderator can pause the whole protocol because B trusts the role to grant full scope.

Audit probe: every `onlyRole` modifier — is there a per-target / per-operation scope check after the modifier? Cross-compare across all functions guarded by the same role.

### Solana / Anchor — account-validation order

Pattern: `#[derive(Accounts)]` struct validates signer, owner, PDA seeds. The preflight is the account-resolution phase before instruction body runs.

Failure mode: instruction A validates `signer @ ErrorCode::Unauthorized` AND `signer.key() == state.authority`. Instruction B validates only `signer @ ErrorCode::Unauthorized` and trusts the signer to be the authority — allowing any signer to pass if B's body doesn't re-check.

Audit probe: every `#[account(constraint = ...)]` macro — is the constraint scope-narrowing (checks the TARGET, not just the CALLER)? Cross-compare across all instructions accepting the same account-class.

### Move / Aptos — capability gating

Pattern: capability-typed resources (`Capability<MintRights>`) borrowed at function entry. The preflight is the `borrow_global_mut` / `acquires` declaration.

Failure mode: function A acquires `MintRights` AND asserts the capability targets a specific Coin<T>. Function B acquires `MintRights` but does NOT assert the target — capability-holder can mint any Coin<T> through B even though A scoped them to one.

Audit probe: every `acquires` clause involving a capability — is the capability's scope narrowed by an explicit `assert!` at function entry? Cross-compare across all functions acquiring the same capability.

### Sui Move — capability witness pattern

Pattern: capability objects (`AdminCap` with `key + store`) passed by-reference to functions. The preflight is the parameter binding.

Failure mode: function A takes `&AdminCap` AND asserts `cap.id == target_object.admin_id`. Function B takes `&AdminCap` and trusts the cap's mere presence — admin-cap-holder can call B against any object, not just the one their cap was minted for.

Audit probe: every `&Cap` parameter — does the function body assert the cap-to-target binding? Cross-compare across all functions taking `&Cap`.

### XRPL / C++ — preflight phases (validated origin)

Pattern: every transactor's `Transactor::preflight` runs before `preclaim` / `doApply`. Cross-field firewalls are encoded as preflight `temMALFORMED` returns.

Failure mode: transactor A's preflight rejects the combination `{isMutate=true} × {tx-flag-set}` as `temMALFORMED`, eliminating the race space at preflight. Transactor B (sibling, accepts the same fields and same flags) does NOT have the equivalent reject — letting the race occur during doApply where it's expensive to defend.

Audit probe: for every cross-field rejection found in any preflight, find sibling transactors with the same field+flag combinations. If the sibling doesn't reject, that's the bug class.

## Connection to other findings

### F-15 (pseudo-account immunity)

Pseudo-accounts (XRPL `createPseudoAccount` products; EVM smart contracts; Solana PDAs) bypass standard signer validation by design. The cross-class firewall must enumerate WHICH transactors permit pseudo-account principals and verify each one applies the correct authority-class check. Missing pseudo-account-aware preflight in one transactor while siblings have it = cross-class firewall hole.

### F-43 (cryptographic freshness binding)

When a tx-type binds to off-chain-prepared cryptographic material (ZK proofs, signatures over specific state versions), the freshness binding IS an authority class — it grants the holder authority to consume the bound state at the bound version. Missing freshness check in a sibling transactor that mutates the state's version = the cryptographic binding is bypassed without re-validation.

### Combined attack class

When the cross-class firewall is incomplete AND a sibling transactor exists that mutates the binding state without requiring the binding's keying material, the result is a **delegate-controlled grief primitive**: the delegate holds authority for the sibling op (no binding required), exercises it to bump the binding version, and invalidates all in-flight off-chain-prepared work bound to the prior version. This is the L-35 finding class from the validated origin.

## Audit checklist

When entering a multi-authority-class system audit:

```
[ ] Enumerate every authority class (delegate, sponsor, pseudo-account, role, capability, governance)
[ ] For each class C: list every transactor / instruction / function accepting C
[ ] For each accepting site: locate the preflight check for C
[ ] Cross-compare: does every accepting site have an equivalent preflight check?
[ ] For each missing check: construct attacker scenario
    [ ] Actor holds C
    [ ] Actor submits tx exercising the unchecked transactor
    [ ] Verify whether the transactor's logic exceeds C's intended scope
[ ] For each successful exploit: classify under F-46 cross-class preflight firewall pattern
[ ] Connect to M-12 (granular permission sandbox) if the missing check is in a permission-template system
[ ] Connect to F-15 / F-43 if the missing check involves pseudo-accounts or cryptographic freshness
```

## Anti-patterns

- **Don't trust documentation that says "this op requires class X"** — grep for the actual check. Documentation drift is common.
- **Don't assume the preflight check exists because a sibling transactor has it** — silent absence is the bug class. Enumerate explicitly.
- **Don't conflate doApply check with preflight check** — doApply checks fail late (after partial state writes; reset paths may leak) while preflight checks fail early (cheap, atomic). Both have value but they're not interchangeable.
- **Don't treat "the sibling transactor uses a different check pattern" as safe** — verify the alternative pattern provides equivalent scope narrowing. Equivalent ≠ identical.

## Related

- **M-12** (granular permission sandbox): the canonical instance of this pattern in delegated-permission systems.
- **M-18** (cross-agent contradiction protocol): when one agent flags a missing preflight check and another disagrees, source-code arbitration resolves.
- **rules/finding-output-format.md**: format for reporting cross-class firewall findings.
