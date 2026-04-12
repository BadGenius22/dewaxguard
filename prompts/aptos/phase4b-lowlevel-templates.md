# Phase 4b: Low-Level Language Checks — Aptos Move

> **Language**: Move (Aptos variant)
> **Agent**: depth-lowlevel
> **Focus**: Move type system exploits, ability constraints, generic safety, resource lifecycle

---

## SYSTEMATIC GREP PATTERNS

### A) Ability Constraint Exploits
```bash
grep -rn "has copy\|has drop\|has store\|has key\|phantom" sources/ --include="*.move" | grep -v test
```
1. **Missing `drop`**: Resource without `drop` must be explicitly destroyed. If ANY code path doesn't destroy it → transaction aborts. Can attacker force a code path that leaks?
2. **Missing `copy`**: Resource without `copy` is moved on use. Double-use = compile error. BUT: references (`&` / `&mut`) bypass this — check for reference lifecycle bugs
3. **Missing `store`**: Can't be stored in global storage. If code tries to store it → compile error. Check for workarounds via wrapping
4. **`key` without `store`**: Object can exist in storage but can't be wrapped inside another struct
5. **`phantom` type params**: Phantom types carry no runtime data but affect type matching. Can phantom type be spoofed?

### B) Integer Overflow/Underflow
```bash
grep -rn "as u64\|as u128\|as u256\| \+ \| \- \| \* \| / " sources/ --include="*.move" | grep -v test
```
**Move VM aborts on overflow/underflow** — this is SAFE. But:
1. **Abort = DoS**: If overflow causes abort, the transaction fails. Can attacker trigger this to block critical operations?
2. **`(x as u64)`**: Casting u128/u256 to u64 ABORTS on overflow (unlike Rust's silent truncation). Safe but can DoS.
3. **Division by zero**: Aborts. Can attacker make divisor zero?
4. **Shift operations**: `x << n` where `n >= bit_width` ABORTS (Cetus $223M exploit was exactly this pattern)

### C) Generic Type Exploits
```bash
grep -rn "fun.*<T\|struct.*<T\|public fun.*<.*>" sources/ --include="*.move" | grep -v test
```
1. **Type confusion**: Can attacker instantiate `Pool<FakeToken>` that interacts with `Pool<RealToken>`?
2. **Witness pattern**: Is the generic type parameter used as a witness for access control?
3. **Missing constraints**: `fun do_thing<T>()` vs `fun do_thing<T: store + drop>()` — missing constraints = wider attack surface
4. **Phantom type abuse**: If `T` is phantom, attacker chooses any type without providing a value

### D) Reference Safety (`&` / `&mut`)
```bash
grep -rn "borrow_global\|borrow_global_mut\|move_from\|move_to\|freeze" sources/ --include="*.move" | grep -v test
```
1. **Dangling reference**: `borrow_global_mut` → modify → reference still held? Move prevents this at compile time, but check module-level patterns
2. **Ref lifecycle across functions**: Ref created in function A, passed to B, used after A's state changes?
3. **ConstructorRef/TransferRef/MintRef**: One-time capabilities from object creation. If stored incorrectly, can be reused
4. **freeze()**: Converts `&mut` to `&`. After freeze, can the original mut ref still be used? (No — Move prevents this)

### E) Object Model (Aptos-specific)
```bash
grep -rn "object::create\|object::transfer\|ObjectCore\|ConstructorRef\|TransferRef\|DeleteRef" sources/ --include="*.move" | grep -v test
```
1. **TransferRef stored permanently**: Whoever has TransferRef can transfer the object forever
2. **DeleteRef stored permanently**: Whoever has DeleteRef can delete the object (and drain contained resources)
3. **Object address determinism**: Object addresses are deterministic from creation seed. Can attacker predict and pre-interact?
4. **Untransferable objects**: If `allow_ungated_transfer` is false, transfer requires TransferRef. Is this consistently enforced?

### F) Fungible Asset Safety
```bash
grep -rn "fungible_asset\|FungibleStore\|FungibleAsset\|primary_fungible_store\|deposit\|withdraw" sources/ --include="*.move" | grep -v test
```
1. **Dispatchable hooks**: FA with `dispatchable_withdraw` / `dispatchable_deposit` can execute arbitrary code during transfers — reentrancy vector
2. **FungibleStore vs CoinStore**: Different APIs, different safety guarantees
3. **Concurrent supply**: If using concurrent supply tracking, race conditions possible in high-TPS scenarios
