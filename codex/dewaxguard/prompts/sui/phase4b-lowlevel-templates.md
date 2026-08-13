# Phase 4b: Low-Level Language Checks — Sui Move

> **Language**: Move (Sui variant)
> **Agent**: depth-lowlevel
> **Focus**: Sui Move type system, object model, ability exploits, dynamic fields

---

## SYSTEMATIC GREP PATTERNS

### A) Ability Constraint Exploits (Same as Aptos + Sui-specific)
```bash
grep -rn "has copy\|has drop\|has store\|has key\|phantom" sources/ --include="*.move" | grep -v test
```
Same checks as Aptos Move, plus:
1. **`key` ability on Sui**: Required for objects. Objects without `key` can't exist independently
2. **`store` on Sui**: Required to be wrapped inside another object or stored in dynamic fields
3. **Shared vs owned**: Objects with `key` can be shared (`share_object`) or owned. Wrong choice = different security model

### B) Integer Safety (Same Move VM)
```bash
grep -rn "as u64\|as u128\| \+ \| \- \| \* \| / \|<< \|>> " sources/ --include="*.move" | grep -v test
```
1. **Shift overflow**: `x << n` where `n >= bit_width` ABORTS. The Cetus $223M exploit on Sui was this exact bug.
2. **Casting aborts**: `(x as u64)` aborts if x > u64::MAX. Safe but DoS vector.
3. **Division by zero**: Aborts. Trace all division paths for zero divisor.

### C) Object Ownership Model (Sui-specific)
```bash
grep -rn "transfer::transfer\|transfer::share_object\|transfer::freeze_object\|transfer::public_transfer" sources/ --include="*.move" | grep -v test
```
1. **Owned → Shared escalation**: Once shared, an object is accessible by anyone. Can't go back to owned.
2. **`public_transfer` vs `transfer`**: `public_transfer` requires `store` ability. `transfer` is module-only.
3. **Wrapped objects**: Object inside another object loses its independent identity. Can it be extracted?
4. **Object ID reuse**: After deletion, can the same ID be reused? (No — UIDs are unique)
5. **Dynamic object fields**: `ofield::add/remove` — can attacker add fields to an object they don't own?

### D) Dynamic Fields
```bash
grep -rn "dynamic_field\|dynamic_object_field\|df::add\|df::remove\|df::borrow\|ofield::" sources/ --include="*.move" | grep -v test
```
1. **Type confusion**: `df::borrow<K, V>` — can attacker provide wrong V type? (Move prevents at runtime)
2. **Key collision**: Two different logical entries with same key type + value → only one can exist
3. **Orphaned dynamic fields**: Parent object deleted but dynamic fields remain — are they recoverable?
4. **Gas exhaustion via many fields**: Object with thousands of dynamic fields — iterating = expensive

### E) Witness Pattern
```bash
grep -rn "struct.*has drop\|one_time_witness\|OTW\|init(" sources/ --include="*.move" | grep -v test
```
1. **One-Time Witness (OTW)**: Used in `init()` for module initialization. Can only be created once.
2. **Witness leaking**: If witness type has `copy` or `store`, it can be saved and reused
3. **Missing OTW check**: If function expects OTW but doesn't verify it's from `init`, can be spoofed

### F) Coin/Token Safety
```bash
grep -rn "coin::split\|coin::join\|coin::value\|coin::destroy_zero\|balance::" sources/ --include="*.move" | grep -v test
```
1. **Zero coin**: `coin::destroy_zero` panics on non-zero. But what if protocol doesn't check?
2. **Coin splitting**: `coin::split` creates new coin. Original reduced. Are both tracked?
3. **Balance vs Coin**: `Balance<T>` is the raw type, `Coin<T>` is the object wrapper. Mixing = confusion
