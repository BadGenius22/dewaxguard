# Auth-Critical File Allowlist

> **Phase**: 1 (recon respects allowlist when emitting source bundles) → 3/4b (agents trust full bodies for these files)
> **Purpose**: Prevent the "missing `require_auth` / missing access control" hallucination that occurs when an agent reads a function body that has been collapsed/squeezed/summarized for context budget. Auth guards live INSIDE function bodies; if the body is collapsed, the guard becomes invisible and the agent invents a missing-guard finding.
> **Origin**: Ported from cosminmarian53/skills `soroban-auditor` `--keep-full` allowlist.

---

## The hallucination this prevents

Token squeezers and "skeleton view" preprocessors collapse function bodies to `{ ... }` for context efficiency. This is correct for most files — agents should query individual function bodies on demand via `Read`. But for auth-critical files, the squeezed view directly causes false positives:

```rust
// What the squeezer emits:
pub fn set_admin(env: &Env, new_admin: Address) { ... }

// What the agent concludes:
"set_admin has no require_auth — anyone can become admin"

// What the actual body contains (hidden by squeezer):
pub fn set_admin(env: &Env, new_admin: Address) {
    storage::admin(env).require_auth();   // ← guard the agent never saw
    storage::set_admin(env, &new_admin);
}
```

This finding class is high-volume, easy to flag, and 100% wrong. The fix is mechanical: prevent the squeezer from collapsing auth-critical files.

---

## Allowlist contract

A file is auth-critical if its path matches **any** of these substrings (case-insensitive):

```text
admin
access_control
access-control
auth
authorize
authorization
emergency
upgrade
ownable
ownership
multisig
governance
permissions
roles
rbac
acl
```

OR the file is in this language-specific list (these names appear in routinely audited entry points):

| Language | Files |
|---|---|
| **EVM/Solidity** | `Ownable.sol`, `AccessControl.sol`, `AccessControlEnumerable.sol`, `Pausable.sol`, `TimelockController.sol`, `Governor.sol`, `Permit.sol` |
| **Stellar/Soroban** | `token/src/contract.rs`, `a-token/src/contract.rs`, `debt-token/src/contract.rs`, `pool-configurator/src/contract.rs`, `admin.rs`, `access_control.rs`, `emergency.rs`, `upgrade.rs`, files implementing `__check_auth` |
| **Solana/Anchor** | files defining `#[derive(Accounts)]` structs with `Signer`/`has_one`/`constraint` checks; `instructions/admin*.rs`, `instructions/initialize*.rs`, `state/config.rs`, `state/admin.rs` |
| **Aptos/Sui Move** | `governance.move`, `admin.move`, `access_control.move`, `capabilities.move`, modules containing `Capability`/`AdminCap`/`OwnerCap`/`UpgradeCap`/`TreasuryCap` |
| **C++ ledger** | `Transactor.cpp`, `Transactor.h`, files defining `preflight`/`preclaim`/`doApply`, validator/consensus auth, `Permissions.h`/`.cpp` |

---

## Recon emit contract

When the recon agent (or `scripts/build_recon_maps.sh` — see commit 2) emits a "minified core" or "skeleton" source bundle, every file matching the allowlist MUST be emitted with **full bodies**, even if every other file in the bundle is body-collapsed.

The emitted bundle MUST mark these files with a `[full-bodies]` tag in the file header so downstream agents know they can trust the visible code:

```
// === contracts/access_control.rs [full-bodies] ===
pub fn require_admin(env: &Env, caller: &Address) {
    if caller != &storage::admin(env) { panic!("not admin"); }
    caller.require_auth();
}

// === contracts/lending/pool.rs [collapsed] ===
pub fn supply(env: &Env, ...) { ... }
pub fn withdraw(env: &Env, ...) { ... }
```

Files without the tag are body-collapsed and agents MUST `Read` the file directly before claiming any guard-related finding on them.

---

## Agent rule (HARD)

Every breadth and depth agent prompt MUST include:

```
Before claiming "missing auth", "missing access control", "missing role check", or
"missing privilege check" on any function:

1. Check if the source file is marked [full-bodies] in the bundle header.
2. If [full-bodies]:
   - The visible code is authoritative. If you don't see the guard in the body, it
     genuinely doesn't exist. Proceed with the finding.
3. If [collapsed] (or no tag):
   - You CANNOT claim a missing-auth bug from the skeleton view alone.
   - Read the actual function body via the Read tool before flagging.
   - If you cannot Read it within your tool budget, DOWNGRADE to LEAD and note
     "auth-check unverified, body not read".
4. Always grep {SCRATCHPAD}/guard-map.md (when present) for the function name as a
   secondary check — guards may be enforced via a wrapping macro/modifier that
   the body collapse hid.
```

---

## Validator rule (HARD)

In Phase 5d (Bug Validator), Gate 1 (Refutation) for any finding alleging missing auth/access-control MUST include:

```
auth_check: SAW_FULL_BODY:{file:line} — guard absent in full body, finding stands
auth_check: SAW_GUARD:{file:line} — found `require_auth()` / `onlyOwner` / `require_admin`, REJECT
auth_check: SKELETON_ONLY — body never read, DOWNGRADE to LEAD
```

Findings without `auth_check:` populated are auto-failed by the validator harness.

---

## Why this is a separate rule (not just "always read the body")

In a 15K-LOC audit, "always read every function body" exceeds context budget for breadth agents. The squeezer is genuinely valuable for the 95% of files where bodies don't materially affect breadth-stage hypotheses. The allowlist is the surgical fix: keep bodies for the 5% of files where missing them produces a known false-positive class.

This rule pairs with `rules/agent-tool-budgets.md` (which caps Read calls per agent) — the budget cap forces agents to skim, the allowlist ensures the things they skim past aren't auth-critical.
