# Phase 4b: Low-Level Language Checks — Solana/Rust

> **Language**: Rust (Anchor 0.29+, Native Solana)
> **Agent**: depth-lowlevel
> **Focus**: Rust type system exploits, unsafe code, serialization safety, integer casts

---

## SYSTEMATIC GREP PATTERNS

### A) Integer Cast Safety — `as` Bypasses overflow-checks
```bash
grep -rn " as u64\| as u128\| as i64\| as i128\| as usize\| as u32\| as u16\| as u8" programs/ --include="*.rs" | grep -v target | grep -v test
```
**CRITICAL**: `as` casts in Rust NEVER panic, even with `overflow-checks = true`. They silently truncate or wrap.
- `u128 as u64` → truncates top 64 bits
- `i64 as u128` → negative values wrap to huge positive (e.g., -1 → u128::MAX)
- `u64 as usize` → safe on 64-bit, truncates on 32-bit (WASM)
- `i64 as u64` → negative wraps to large positive

For EACH cast: Is there a guard? Can the source be negative/huge? Does the result affect fund calculations?

### B) zero_copy / repr(C) Struct Safety
```bash
grep -rn "zero_copy\|repr(C)\|#\[account(zero_copy" programs/ --include="*.rs" | grep -v target | grep -v test
```
For each zero_copy struct:
1. **Padding**: Are all fields explicitly aligned? Implicit padding = uninitialized bytes readable
2. **Bool as u8**: Move `bool` uses `u8` in zero_copy — check no values other than 0/1 are possible
3. **Account size**: If account data is shorter than struct size, `AccountLoader::load()` returns error — verify
4. **Discriminator spoofing**: Can attacker create account with correct 8-byte discriminator but garbage data?
5. **Field overflow**: In `repr(C)`, writing beyond one field overflows into the next — check all `set` operations

### C) Unsafe Code
```bash
grep -rn "unsafe\s*{\|unsafe fn\|transmute\|from_raw_parts\|as_ptr\|offset(" programs/ --include="*.rs" | grep -v target | grep -v test
```
For each unsafe block:
1. What invariant must hold?
2. Can external input violate the invariant?
3. Is the unsafe block actually necessary? (Sometimes it's legacy)

### D) Borsh/Bytemuck Serialization
```bash
grep -rn "BorshSerialize\|BorshDeserialize\|Pod\|Zeroable\|try_from_slice\|try_from_bytes" programs/ --include="*.rs" | grep -v target | grep -v test
```
1. **Type confusion**: Can account data for type A be deserialized as type B?
2. **Anchor discriminator**: 8-byte SHA256 prefix. Collision probability = 1/2^64 per type — low but check
3. **Remaining bytes**: Does deserializer consume ALL data? Extra bytes ignored = can append garbage
4. **Account realloc**: After `realloc`, is new space initialized? (`zero_init` flag)

### E) Checked vs Unchecked Arithmetic
```bash
grep -rn "\.wrapping_\|\.overflowing_\|\.saturating_\|checked_add\|checked_sub\|checked_mul\|checked_div" programs/ --include="*.rs" | grep -v target | grep -v test
```
1. `saturating_add/sub` silently clamps at MAX/0 — can this hide an error?
2. `wrapping_add/sub` wraps around — intentional or bug?
3. `checked_*` returns `Option` — is `None` properly handled? (`.unwrap()` = panic = tx revert)
4. `.expect("...")` on arithmetic — acceptable (reverts tx) but ungraceful

### F) String/Bytes Handling
```bash
grep -rn "from_utf8\|as_bytes\|to_string\|String::from\|str::from" programs/ --include="*.rs" | grep -v target | grep -v test
```
1. User-supplied strings as PDA seeds: length-delimited? Max length enforced?
2. UTF-8 validation: `from_utf8_unchecked` = UB on invalid UTF-8
3. String comparison: byte-level vs unicode-level

---

## DEEP ANALYSIS QUESTIONS

1. For each `as` cast: compute the worst-case value and trace it through the program
2. For each zero_copy struct: manually count byte offsets and verify alignment
3. For each unsafe block: prove or disprove the invariant holds for all inputs
4. For each serialization: can an attacker craft account data that deserializes to unexpected values?
