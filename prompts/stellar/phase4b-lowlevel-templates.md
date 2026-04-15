# Phase 4b: Low-Level Language Checks — Stellar/Soroban

> **Language**: Rust (Soroban SDK)
> **Agent**: depth-lowlevel
> **Focus**: Rust type system exploits, unsafe code, serialization safety, integer casts, Soroban SDK pitfalls
>
> **🚨 REQUIRED READING**: Before starting, the agent must read `~/.claude/skills/dewaxguard/platform-quirks/stellar.md`. Stellar has critical state archival semantics that differ from common auditor assumptions and have historically produced invalid findings.

---

## SYSTEMATIC GREP PATTERNS

### A) Integer Cast Safety — `as` Bypasses overflow-checks
```bash
grep -rn " as u64\| as u128\| as i64\| as i128\| as usize\| as u32\| as u16\| as u8" contracts/ --include="*.rs" | grep -v target | grep -v test
```
**CRITICAL**: `as` casts in Rust NEVER panic, even with `overflow-checks = true`. They silently truncate or wrap.
- `u128 as u64` → truncates top 64 bits
- `u128 as i128` → negative if MSB set (e.g., `u128::MAX as i128 == -1`)
- `i128 as u128` → wraps negatives to huge positive
- `u32 as usize` → safe on 64-bit, truncates on 32-bit (WASM target is 32-bit-ish for storage keys)

For EACH cast: Is there a guard? Can the source be negative/huge? Does the result affect fund calculations, nonces, or storage keys?

**Soroban-specific concerns**:
- Fee calculation uses `i128` (Soroban token API requirement). Casts between `u128` (math) and `i128` (token) are especially risky.
- `recovery_id as u32` in secp256k1 code — does the source value have the correct range?
- Options-parser `read_u16() as u32` — small but worth checking.

### B) Unchecked Arithmetic and `checked_*` Handling
```bash
grep -rn "\.wrapping_\|\.overflowing_\|\.saturating_\|checked_add\|checked_sub\|checked_mul\|checked_div" contracts/ --include="*.rs" | grep -v target | grep -v test
```
1. `saturating_add/sub` silently clamps — can this hide an error in fee or balance accounting?
2. `wrapping_add/sub` wraps — intentional or bug? (Very suspicious in money paths)
3. `checked_*` returns `Option` — is `None` properly handled? `.unwrap()` panics (tx revert, acceptable); silent default via `unwrap_or_default()` is a bug.
4. `.expect("...")` on arithmetic — acceptable (reverts tx) but check the invariant stated in the message is actually enforced.

**Verify `[profile.release] overflow-checks`**: Soroban contracts MUST have `overflow-checks = true` in `Cargo.toml`. If missing/false, default `+`/`-`/`*` wraps silently → HIGH severity finding.

```bash
grep -n "overflow-checks" Cargo.toml
```

### C) Unsafe Code
```bash
grep -rn "unsafe\s*{\|unsafe fn\|transmute\|from_raw_parts" contracts/ --include="*.rs" | grep -v target | grep -v test
```
Soroban contracts should have **zero** `unsafe` blocks. Any `unsafe` is a red flag — Soroban's design does not require it. If found:
1. What invariant must hold?
2. Can external input violate the invariant?
3. Why is unsafe used instead of safe alternatives?

### D) `.unwrap()` and `panic!` in Non-Test Code
```bash
grep -rn "\.unwrap()\|panic!\|\.expect(" contracts/ --include="*.rs" | grep -v target | grep -v tests/ | grep -v test_ | grep -v "#\[cfg(test)\]"
```
Soroban `.unwrap()` calls panic the entire transaction. Classify each:
1. **Safe panic**: On invariants that cannot be violated (e.g., `OwnableStorage::owner(env).unwrap()` on a contract that set owner in constructor) — acceptable.
2. **Authorization-context panic**: Inside `__check_auth`, panics are equivalent to returning `Err` (deny the operation) — acceptable.
3. **User-triggerable panic**: `user_input.unwrap()` or `parse(user_data).unwrap()` — DoS vector, downgrade or finding.
4. **Cross-contract call panic**: `client.call().unwrap()` where the target contract could return unexpected data — denial by external contract.

### E) Manual Byte Encoding / Decoding
```bash
grep -rn "buffer_reader\|buffer_writer\|BufferReader\|BufferWriter\|to_xdr\|from_xdr\|to_bytes\|from_bytes\|slice(\|to_array(" contracts/ --include="*.rs" | grep -v target | grep -v tests/
```
For each encode/decode pair:
1. **Symmetry**: Does `decode(encode(x)) == x` for all valid `x`? Run this mentally for each field.
2. **Bounds**: Do `read_bytes(n)` calls check `n <= remaining`? (Soroban SDK panics on underflow, but verify the panic is acceptable.)
3. **Field order**: Is the order of writes consistent with the order of reads?
4. **Length prefixes**: Variable-length fields need length prefixes, or the decode gets misaligned.
5. **Address payload encoding**: `write_address_payload` vs `from_payload(AddressPayload::ContractIdHash)` — source type must match destination type or address is silently misconstructed.

### F) Signature Verification Patterns
```bash
grep -rn "secp256k1_recover\|ed25519_verify\|crypto()\|crypto_hazmat" contracts/ --include="*.rs" | grep -v target | grep -v tests/
```
1. **s-value normalization (low-s)**: For secp256k1, is `s <= n/2` enforced? Missing → signature malleability (EIP-2 equivalent).
2. **Recovery ID range**: Is `v` normalized to 0/1 from Ethereum's 27/28 format?
3. **Sorted signer check**: If verifying multiple signatures in a threshold scheme, are signers sorted to prevent duplicate acceptance?
4. **Network binding**: Does the hash signed include a network identifier? If not, cross-network replay is possible when the same contract is deployed on multiple Stellar networks.
5. **Replay protection**: Is the hash/nonce stored somewhere to prevent replay? (See **platform-quirks/stellar.md #1** for the storage tier that must be used. Do NOT store replay protection in persistent storage and forget — see archival semantics.)

### G) String/Bytes Handling
```bash
grep -rn "Bytes::\|BytesN::\|Symbol::new\|String::from" contracts/ --include="*.rs" | grep -v target | grep -v tests/
```
1. **User-supplied bytes as storage keys**: Length-delimited? Max length enforced?
2. **Symbol construction**: `Symbol::new(env, "...")` panics on invalid symbols (must be `[a-zA-Z0-9_]{0,32}`).
3. **Comparison**: Byte-level vs logical equality — especially for addresses converted via `AddressPayload`.

---

## DEEP ANALYSIS QUESTIONS

1. **For each `as` cast**: Compute the worst-case value at the source and trace through the destination. Does it affect fund calculations, storage keys, or authorization decisions?
2. **For each `.unwrap()` in production code**: Prove the inner value is always `Some`. If not provable, classify as DoS finding.
3. **For each encode/decode pair**: Manually trace at least one non-trivial input through both directions and verify symmetry.
4. **For each signature verification**: Check all 5 concerns above (s-value, recovery ID, ordering, network binding, replay protection).
5. **For `overflow-checks = true` in release**: If missing or false, this is a HIGH severity systemic bug.

## Prohibited Finding Patterns

Do NOT report findings based on the following misconceptions. See `~/.claude/skills/dewaxguard/platform-quirks/stellar.md` for the complete list:

- ❌ "Persistent storage expires to default value enabling replay/bypass/desync"
- ❌ "Instance counter desyncs from persistent entries because persistent expires"
- ❌ Any claim involving persistent/instance storage reverting to default values on TTL expiry — these tiers **archive** with preserved values on Stellar; only **temporary** storage actually deletes.
