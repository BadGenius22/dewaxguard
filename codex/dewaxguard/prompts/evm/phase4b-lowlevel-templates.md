# Phase 4b: Low-Level Language Checks — EVM/Solidity

> **Language**: Solidity 0.6.x - 0.8.x
> **Agent**: depth-lowlevel
> **Focus**: Solidity compiler behavior, type system exploits, assembly safety

---

## SYSTEMATIC GREP PATTERNS

Run ALL of these before deep analysis. Every match is a candidate.

### A) Inline Assembly / Yul
```bash
grep -rn "assembly\s*{" --include="*.sol" | grep -v test | grep -v mock
```
For each assembly block:
1. **MSTORE/MLOAD bounds**: Is the memory offset validated? Writing beyond allocated memory corrupts free memory pointer.
2. **RETURNDATACOPY**: Is `returndatasize()` checked before copy? Copying beyond returndata = zero bytes, not revert.
3. **Free memory pointer (0x40)**: Is it restored after manual allocation? Corrupted FMP breaks subsequent Solidity code.
4. **CALLDATACOPY/CALLDATALOAD**: Is offset + length within calldatasize? Out-of-bounds reads return zeros.
5. **EXTCODECOPY**: Return value not checked? Non-contract addresses return empty.
6. **Arithmetic in assembly**: No overflow protection in Yul, even in Solidity ≥0.8.

### B) Type Casting / Truncation
```bash
grep -rn "uint128\|uint96\|uint64\|uint32\|uint16\|uint8\|int128\|int64" --include="*.sol" | grep -v test
```
For each narrowing conversion:
1. Solidity ≥0.8 reverts on explicit narrowing if value overflows — **but only for explicit casts**
2. `abi.decode` with wrong types does NOT revert — it silently truncates/reinterprets
3. Signed-to-unsigned: `int256(-1)` cast to `uint256` = `type(uint256).max`
4. Downcast in unchecked blocks: `unchecked { uint128(x) }` silently truncates

### C) abi.encode / abi.encodePacked Collisions
```bash
grep -rn "abi\.encodePacked\|keccak256.*abi\." --include="*.sol" | grep -v test
```
For each `abi.encodePacked`:
1. **Hash collision**: `encodePacked(string, string)` — two dynamic types concatenated without length prefix. `("ab","c")` == `("a","bc")`
2. If used for signatures, mappings, or access control — exploitable
3. Fix: use `abi.encode` (length-prefixed) instead

### D) Unchecked Blocks
```bash
grep -rn "unchecked\s*{" --include="*.sol" | grep -v test
```
For each unchecked block:
1. Read the developer's reasoning. Is it ACTUALLY correct?
2. Check ALL arithmetic inside — not just the intended one
3. Common mistake: unchecked loop counter is fine, but OTHER math inside the loop is also unchecked
4. Subtraction underflow in unchecked = huge number, not revert

### E) Delegatecall / Storage Layout
```bash
grep -rn "delegatecall\|DELEGATECALL\|_fallback\|_delegate" --include="*.sol" | grep -v test
```
For each delegatecall:
1. **Storage collision**: Does the implementation use the same storage layout as the proxy?
2. **Uninitialized proxy**: Can the implementation's initializer be called directly?
3. **Function selector collision**: Can a proxy function shadow an implementation function?
4. **Diamond/multi-facet**: Are storage slots properly namespaced (ERC-7201)?

### F) Low-Level Calls
```bash
grep -rn "\.call\(\|\.call{" --include="*.sol" | grep -v test
```
For each `.call`:
1. Is the return value checked? `(bool success, bytes memory data) = target.call(...)`
2. Is `success` actually used? Silent failure = fund loss
3. Returnbomb: malicious contract returns huge `data`, consuming caller's gas on memory expansion
4. Gas forwarding: `.call{gas: X}` — is X sufficient? Too low = always fails

### G) Storage Gaps and Upgrades
```bash
grep -rn "__gap\|storage.*slot\|ERC7201\|STORAGE_LOCATION" --include="*.sol" | grep -v test
```
For upgradeable contracts:
1. Are storage gaps properly sized?
2. After upgrade, do new variables collide with existing storage?
3. Is `_disableInitializers()` called in constructors?

---

## DEEP ANALYSIS QUESTIONS

For each finding from grep scan:

1. **Can an attacker control the input that reaches this code path?**
2. **What is the worst-case value an attacker can provide?**
3. **Does the wrong result affect token balances, approvals, or access control?**
4. **Can this be combined with another finding (chain)?**
