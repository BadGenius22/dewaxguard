# Phase 4b: Runtime/VM-Specific Attacks — Sui

> **Runtime**: Sui Move VM + Sui Consensus
> **Agent**: depth-runtime
> **Focus**: Sui object model, PTB composition, package upgrades, consensus-level attacks

---

## SYSTEMATIC CHECKS

### A) Programmable Transaction Block (PTB) Composition
1. **Multi-command transactions**: PTBs can chain multiple Move calls in one tx. State from command 1 visible to command 2.
2. **Object passing between commands**: Output of command 1 used as input to command 2. Type safety maintained?
3. **Shared object contention**: Multiple PTBs accessing same shared object — execution order matters
4. **PTB as flash loan**: Borrow in cmd 1, use in cmd 2, repay in cmd 3 — all atomic. Is the protocol vulnerable?
5. **Nested result usage**: Can PTB results be manipulated between commands?

### B) Object Ownership and Consensus
1. **Owned objects**: Only owner can use in tx. Fast path (no consensus needed). Can ownership be stolen?
2. **Shared objects**: Anyone can access. Requires consensus (slower). Can attacker grief by spamming shared object txs?
3. **Immutable objects**: Can't be modified after freeze. But can references to immutable objects be exploited?
4. **Object version**: Each mutation increments version. Can stale version be used?
5. **Object wrapping/unwrapping**: Wrapping an object transfers it to the wrapper. Unwrapping restores it. State preserved?

### C) Package Upgrade Attacks
```bash
grep -rn "UpgradeCap\|upgrade_policy\|make_immutable\|authorize_upgrade" sources/ --include="*.move" | grep -v test
```
1. **Additive compatibility**: Upgrades can add new functions, types, but not modify existing
2. **UpgradeCap holder**: Whoever has UpgradeCap can upgrade. Is it properly protected?
3. **`make_immutable`**: Permanently prevents upgrades. Was this called for critical packages?
4. **Version-specific bugs**: If package V1 has a bug and V2 fixes it, objects created by V1 may still use V1 logic
5. **Friend module changes**: Upgrade can add new friend modules — new attack surface

### D) Consensus and Ordering
1. **Transaction ordering**: For shared objects, Sui orders via consensus. Can validator influence ordering?
2. **Checkpoint finality**: State confirmed after checkpoint. Can state be read before finality?
3. **Equivocation**: Validator signs conflicting transactions — Sui's narwhal prevents this, but verify
4. **Object lock contention**: High contention on popular shared objects (e.g., DEX pool) = throughput degradation = potential DoS

### E) Cross-Package Trust
1. **Public function access**: Any public function callable by anyone. Access control must be inside the function
2. **Friend modules across packages**: Friends are package-level. Cross-package calls go through public interfaces
3. **Package ID verification**: When calling another package, is the package ID hardcoded or user-provided?
4. **Dependency upgrades**: If dependency package upgrades, this package's behavior may change
5. **Type parameter injection**: When calling `Pool<T>`, can attacker provide malicious T from their own package?

### F) Clock and Randomness
```bash
grep -rn "clock::Clock\|clock::timestamp_ms\|random::Random\|random::new_generator" sources/ --include="*.move" | grep -v test
```
1. **Clock**: Sui provides a shared Clock object. Timestamp is validator-determined — slight manipulation possible
2. **Randomness**: Sui has on-chain randomness (random::Random). Is it used in `init` or `entry` context?
3. **Randomness commitment**: For Sui's randomness, the random value is fixed at tx execution time. Can validator see and influence?

### G) Token / Coin Transfers
1. **Transfer restrictions**: Some coins may have custom transfer restrictions via `coin::deny_list`
2. **Sponsored transactions**: Gas paid by sponsor. Can sponsor manipulate the tx?
3. **Object receiving**: `transfer::receive` requires `Receiving<T>` ticket. Can receiving be front-run?
