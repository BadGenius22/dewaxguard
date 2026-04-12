# Phase 4b: Runtime/VM-Specific Attacks — Aptos

> **Runtime**: Aptos Move VM
> **Agent**: depth-runtime
> **Focus**: Move VM execution model, module upgrades, resource publishing, transaction composition

---

## SYSTEMATIC CHECKS

### A) Module Upgrade Attacks
```bash
grep -rn "upgrade_policy\|PackageRegistry\|code::publish\|can_change_module" sources/ --include="*.move" | grep -v test
```
1. **Upgrade replaces logic**: Module upgrade changes function behavior for all existing resources
2. **Immutable vs compatible**: `immutable` prevents upgrade. `compatible` allows adding but not removing/changing
3. **Friend module changes**: Upgrade can add new friend modules that access private functions
4. **Storage layout change**: Upgrade can change struct layout — existing resources reinterpreted with new layout

### B) Transaction Composition (Aptos-specific)
1. **Multi-signer transactions**: Aptos supports multiple `&signer` params. Can attacker trick user into co-signing?
2. **Script transactions**: Can execute arbitrary Move code in a script. Are there guards against script-based attacks?
3. **Batch transactions**: Multiple entry functions in one tx. State modified by first function visible to second
4. **Payload builder manipulation**: Can the payload be modified between user signing and submission?

### C) Gas/Execution Limits
1. **Gas metering**: Move VM meters every instruction. Complex operations can exceed gas limit
2. **Storage gas**: Reading/writing global storage has high gas cost. Many `borrow_global` = expensive
3. **Vector operations**: Large vectors consume O(n) gas for operations. Can attacker inflate vector size?
4. **Table operations**: O(1) but each access has base cost. Many table reads in one tx?
5. **Abort codes**: Different abort codes reveal different information. Information leakage via abort?

### D) Resource Publishing / Global Storage
```bash
grep -rn "move_to\|move_from\|exists<\|borrow_global" sources/ --include="*.move" | grep -v test
```
1. **Resource squatting**: Can attacker publish a resource at an address before the legitimate owner?
2. **`move_to` to signer only**: Resources can only be published under the signer's address. But what about objects?
3. **`move_from` authorization**: Only the module that defines the resource can `move_from`. But the module might expose a public function that does this
4. **`exists<T>` check-then-act**: TOCTOU between `exists` check and `borrow_global`. In single tx, safe. Across txs, not.

### E) Event Ordering and Indexing
1. **Event replay**: Events are not deduplicated on-chain. Same event emitted twice = processed twice by indexers
2. **Event ordering**: Within a tx, events are ordered. Across txs in a block, order depends on execution
3. **Missing events for critical state changes**: State changes without events = invisible to monitoring

### F) Randomness (Aptos-specific)
```bash
grep -rn "randomness\|RandomnessConfig\|random_" sources/ --include="*.move" | grep -v test
```
1. **On-chain randomness**: Aptos has native randomness API. Is it used correctly?
2. **Randomness bias**: Can validator influence the random output?
3. **Commit-reveal patterns**: If using external randomness, is the commit phase secure?

### G) Cross-Module Trust
1. **Friend modules**: Who are the friends? Can a friend module be compromised?
2. **Public entry functions**: Any public entry function is callable by anyone — is access control enforced inside?
3. **Module authority**: Does the module use `@module_addr` for authority? Can module address be spoofed?
4. **Dependency chain**: If module A depends on module B, and B is upgraded, A's behavior changes
