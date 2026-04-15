# Phase 4b: Low-Level Language Checks — C / C++

> **Language**: C and C++ (tuned for consensus-node / ledger implementations: rippled, Bitcoin Core, consensus clients, cryptographic primitives)
> **Agent**: depth-lowlevel
> **Focus**: C++20 type system, memory safety, integer semantics, undefined behavior, template instantiation, serialization correctness
>
> **🚨 REQUIRED READING**: Before starting, the agent MUST read `~/.claude/skills/dewaxguard/platform-quirks/cpp.md`. It documents 11 critical platform quirks for XRPL/rippled-style consensus-node audits (TER result class semantics, transactor phase ordering, amendment gating, SLE field access, consensus determinism, invariant coverage, Fiat-Shamir context binding, owner count accounting, cross-tx composition, assertions-are-noops, C++ UB traps) plus a baseline known-issue list. These quirks MUST be internalized before writing any finding, and every finding must be cross-checked against the baseline known-issue list to avoid duplicates.

---

## SYSTEMATIC GREP PATTERNS

Run ALL of these before deep analysis. Every match is a candidate.

### A) Integer overflow / underflow / signed-unsigned confusion
```bash
rg -n "std::uint(8|16|32|64)_t|std::int(8|16|32|64)_t|uint\d+_t" --type cpp --type c | head -50
rg -n "\.size\(\)\s*-\s*\d|\.size\(\)\s*-\s*\w" --type cpp --type c
rg -n "static_cast<(u|)int\d+_t>" --type cpp
rg -n "1u?\s*<<\s*\w|1u?l?l?\s*<<\s*\w" --type cpp --type c
```
For each numeric operation:
1. **Unsigned underflow**: `size_t - size_t` where LHS < RHS wraps to huge value. Common in "remaining bytes" calculations after a length check reordering.
2. **Narrowing cast**: `static_cast<uint32_t>(uint64_t)` silently truncates — does the upstream check bound the source?
3. **Signed shift**: `1 << 31` on signed int is UB in C and pre-C++14. `1u << 31` is fine.
4. **Shift width overflow**: `x << 64` where `x` is `uint64_t` is UB. Always `assert(shift < sizeof(T)*8)`.
5. **Mixed signed/unsigned comparison**: `int x; size_t y; x < y` converts x to size_t. Negative x becomes huge.
6. **INT_MIN negation**: `-x` where `x == INT_MIN` is signed overflow UB.
7. **Division**: `INT_MIN / -1` is UB. `x / 0` is UB.
8. **Modulo negative**: `-7 % 3` is implementation-defined pre-C++11, defined as -1 in C++11+.

### B) Pointer arithmetic / array bounds / unchecked buffer access
```bash
rg -n "memcpy|memmove|memset|std::copy|strncpy|strcpy" --type cpp --type c
rg -n "operator\[\]|\.data\(\)\[" --type cpp
rg -n "reinterpret_cast<" --type cpp
```
For each raw memory op:
1. **Length validation**: Is the destination buffer size proven ≥ copy length at compile time or verified at runtime?
2. **Source bounds**: Is the source length ≤ actual available bytes? (Most buffer over-reads come from trusting a length field without checking.)
3. **Aliasing**: `memcpy` requires non-overlapping; use `memmove` if maybe overlapping.
4. **reinterpret_cast**: Only legal for `unsigned char*`/`std::byte*` aliasing or trivially-copyable type punning with `memcpy`. Everything else is strict-aliasing UB.
5. **operator[] on span/vector**: No bounds check on index. `.at()` throws; `[]` does not.
6. **std::data() + size()**: Is the returned length the ACTUAL usable length, or the capacity?

### C) Lifetime / dangling references / use-after-free
```bash
rg -n "std::string_view|std::span|string_view|std::optional.*&|auto&\s" --type cpp
rg -n "\.c_str\(\)\s*\)|\.data\(\)\s*\)" --type cpp
rg -n "const auto&\s+\w+\s*=|auto&\s+\w+\s*=" --type cpp
```
For each reference/view:
1. **Dangling string_view**: `string_view v = f();` where `f()` returns `std::string` by value — the temporary is destroyed, v dangles. C++17 lifetime rules do NOT extend temporary to named string_view.
2. **Lambda capture by reference**: `[&](){...}` returned from a function — captures dangle when the function returns.
3. **Iterator invalidation**: Storing an iterator before a container mutation (push_back, erase, rehash). `std::vector::push_back` invalidates all iterators when capacity grows.
4. **Reference to temporary bound in range-for**: `for (auto& x : f().get_container())` — if `f()` returns a value, the temporary is destroyed at end of expression.
5. **std::optional<T&>** is not allowed pre-C++26; people fake it with `optional<reference_wrapper<T>>` which has subtle lifetime semantics.
6. **shared_ptr cycles**: Two shared_ptrs holding each other never destruct — memory leak, resource leak.

### D) Exception safety / error propagation
```bash
rg -n "throw\s|Throw<|try\s*{|catch\s*\(" --type cpp
rg -n "noexcept" --type cpp
rg -n "std::expected|std::variant<.*error" --type cpp
```
For each error path:
1. **Dual error mechanisms**: Function returns error code AND throws — caller may check return and ignore exception.
2. **noexcept violation**: Function declared `noexcept` that actually throws → `std::terminate` (denial of service).
3. **Partial state on exception**: Between resource acquisition and cleanup, does an exception leave state partially modified?
4. **Destructors throwing**: Destructor that throws during stack unwinding → `std::terminate`.
5. **try/catch swallowing**: `catch(...)` with no logging or rethrow — silent failure.
6. **TEC vs TEM vs TEF vs TER semantics** (ledger-specific): In rippled-like systems, tx result codes have fee-charge implications. `tem*` = static rejection (no fee), `tec*` = runtime rejection (fee charged). Returning the wrong class is a semantic bug (see known issue pattern in XRPL #6884 — ZKP failures wrongly returning `tecINTERNAL`).

### E) Serialization / deserialization correctness
```bash
rg -n "memcpy.*out|memcpy.*data\(\)|writeBytes|readBytes|readUint|writeUint" --type cpp --type c
rg -n "Serializer|SerialIter|ByteVector|deserialize" --type cpp
```
For each serialization operation:
1. **Length prefix validation**: Is the declared length bounded by the remaining buffer?
2. **Canonical form**: Is there exactly ONE valid serialization for each value? (Non-canonical = signature bypass risk.)
3. **Endianness**: Explicit big/little-endian calls, or relying on host order?
4. **Padding/alignment**: Struct-to-bytes via memcpy — padding bytes may contain uninit stack data (information leak).
5. **Field order**: Deserialization order must match serialization order exactly.
6. **Optional fields**: Is field presence checked before read? Missing `sfX` field + `tx[sfX]` access = throw or default-init surprise.

### F) Template instantiation / SFINAE / concepts
```bash
rg -n "template\s*<" --type cpp | head -50
rg -n "if constexpr\|std::enable_if|std::is_same_v|std::is_base_of_v" --type cpp
rg -n "requires\s*{" --type cpp
```
For each template:
1. **Silent instantiation drift**: Same template body, two instantiations produce divergent code (e.g., integer vs floating type). Check each instantiation.
2. **SFINAE bypass**: `std::enable_if` conditions that can be side-stepped by an attacker-controlled type.
3. **Default template args**: Adding a default arg to a template in a later release breaks existing code relying on the old default.
4. **Concept mismatch**: C++20 concept refinement that silently accepts a type it shouldn't.

### G) Assertions and runtime invariants
```bash
rg -n "assert\(|XRPL_ASSERT|LOG_FATAL|std::terminate|abort\(" --type cpp
```
For each assertion:
1. **Release vs debug**: `assert()` is NO-OP in release builds. Any logic that depends on the assertion side-effect is broken in release.
2. **Assertion as error handling**: Assertions should check invariants, not validate inputs. If attacker can reach `assert(!maliciousInput)`, it's a DoS in debug + exploitable in release.
3. **Assertion in hot path**: In production, unexpected state should return an error code, not crash.
4. **KNOWN PATTERN** (XRPL `fixSecurity3_1_3` #6867 neighborhood): pre-fix assertions were replaced with proper error returns; grep the post-fix code for any remaining assertion-on-invariant that should be a return.

### H) Undefined behavior traps
```bash
rg -n "\+\+.*\+\+|--.*--|=.*=.*=" --type cpp  # sequence-point pitfalls
rg -n "union\s+\w+" --type cpp --type c
rg -n "volatile\s" --type cpp --type c
```
For each:
1. **Sequence points**: `i = i++ + 1` is UB. Modern compilers warn, but older code base may have it.
2. **Union type punning**: Legal in C since C99, UB in C++ (pre-C++20). Use `std::bit_cast` or `memcpy`.
3. **volatile ≠ atomic**: `volatile` does not provide thread-safety. Multi-threaded access requires `std::atomic`.
4. **Strict aliasing**: Casting `int*` → `float*` and dereferencing is UB. `unsigned char*` aliasing is allowed.
5. **Self-move**: `x = std::move(x)` is typically UB or leaves x in indeterminate state.

---

## DEEP ANALYSIS QUESTIONS

For each finding from grep scan:

1. **Can an attacker control the input that reaches this code path?** (Is the input from a network message, RPC call, transaction field, or consensus data?)
2. **What is the worst-case value an attacker can provide?** (MAX, MIN, 0, empty, oversized, canonical vs non-canonical, off-curve, near-boundary)
3. **Does the wrong result affect consensus state, fund balance, authorization, or cryptographic soundness?**
4. **Is this a fresh bug or a well-known C++ pattern that's been audited before?** (Cross-check against the known-issue baseline and prior-audit exclusion list.)
5. **Can this be combined with another finding (chain)?**

## Ledger-specific additions (XRPL/rippled pattern)

1. **Amendment gating correctness**: `view.rules().enabled(feature)` — is the correct feature name used? Typo = bug survives the gate. Pre-fix code path present but reachable under post-amendment state?
2. **SLE (Ledger Entry) field presence**: `(*sle)[sfX]` throws if field absent. `(*sle)[~sfX].value_or(default)` is the safe form. Grep for the unsafe form.
3. **Transactor phase ordering**: preflight → preflight2 → preclaim → doApply. Expensive checks (ZK proof verify, cryptographic ops) in preclaim run BEFORE fee is fully charged in preflight2 — potential free compute.
4. **jtx helper availability for PoC**: Does the file under audit have corresponding test helpers in `src/test/jtx/`? If yes, PoC is feasible.
