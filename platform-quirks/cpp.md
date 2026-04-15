# C / C++ Ledger Node Quirks — Critical Reference

> **READ THIS BEFORE ANY C/C++ LEDGER-NODE AUDIT.** This document captures platform-specific semantic quirks that produce invalid findings or missed bugs when misunderstood. Tuned for XRPL/rippled and similar consensus-node codebases (Bitcoin Core, BCH node, consensus clients).

**Scope**: Native C++ consensus nodes are **not** smart contracts. There is no sandboxed VM, no permissionless call stack, no reentrancy in the Solidity sense. The attack surface is: transaction validation, state machine transitions, consensus determinism, cryptographic protocols, p2p handling, and node resource exhaustion. Standard EVM/Solana/Move vulnerability classes rarely port cleanly — the threat model is different.

---

## 🚨 #1 — TER Result Class Semantics (Wrong Class = Economic Bug)

### The Misconception

> "A transaction failure is a transaction failure. Returning `tecINTERNAL` when something unexpected happens is fine."

### The Reality (XRPL-Specific)

In rippled and XRPL-derived chains, transaction results are grouped into **classes** that determine economic consequences:

| Class | Meaning | Fee Charged? | Ledger Stored? | Example |
|-------|---------|-------------|---------------|---------|
| `temX` | **Malformed** — static rejection | No | No | `temBAD_AMOUNT` (negative value) |
| `tefX` | **Failure** — tx cannot be applied | Yes | Yes | `tefPAST_SEQ` |
| `tecX` | **Claim** — runtime reject, but valid for inclusion | Yes | Yes | `tecUNFUNDED_PAYMENT` |
| `terX` | **Retry** — might succeed later | No | No | `terQUEUED` |

**Getting the class wrong is an economic bug**, even if the "error message" is similar:

- **`temX` misused as `tecX`**: User pays a fee for a malformed tx they should have been rejected for free.
- **`tecX` misused as `temX`**: Runtime error doesn't charge the fee → node wastes CPU on free work.
- **`tecINTERNAL` for a user-correctable error**: The user pays for the NODE's mistake, not their own.

### Known Real Bug

- **XRPL #6884** (ZKP failures wrongly return `tecINTERNAL`): A cryptographic proof verification failure is a client-side error (bad proof) but was returned as `tecINTERNAL` (implying node bug). Fee charged to user for their own invalid submission is fine; classifying it as a node bug misleads debugging and breaks the semantic contract.

### Checklist for Every Transactor

- [ ] Every `return tecINTERNAL` — is this actually a node-side bug, or a user-facing error?
- [ ] Every `return temX` — does rejecting mean "no fee"? If so, is the static-rejection property actually static (no ledger state read)?
- [ ] Every `return tefX` — is the tx genuinely unprocessable (not just unlikely to succeed)?
- [ ] Every `return terX` — is retry actually plausible?

### Action

When auditing a transactor, map every error return path to one of the four classes and verify the class matches the semantic (static vs dynamic, user-correctable vs node-bug, retry-viable vs not).

---

## 🚨 #2 — Transactor Phase Ordering (preflight → preflight2 → preclaim → doApply)

### The Misconception

> "A check in preclaim is equivalent to a check in preflight — they both run before doApply."

### The Reality

The four phases have distinct semantic contracts:

| Phase | Purpose | State Access | Failure Cost |
|-------|---------|-------------|--------------|
| **preflight** | Static validation (field shapes, flags, signatures) | None | `temX` — no fee |
| **preflight2** | Signature verification for normal txs | None | `temX` — no fee |
| **preclaim** | Dynamic validation (account exists, balance, authorization) | Read-only ledger state | `tecX`/`tefX` — fee charged |
| **doApply** | Final state mutation | Read/write ledger state | `tecX` — fee charged, state modified |

### Known Attack Pattern

**Expensive operation in the wrong phase** = free CPU burn:

- ZK proof verification in `preflight` (no fee charged) → attackers submit many cheap-to-craft invalid proofs. Node burns CPU, attacker pays nothing.
- Signature aggregation in `preclaim` (fee charged) → safe, attacker pays for each failed attempt.
- Static field shape check in `preclaim` → wasted — the check reads no state; put it in `preflight`.

### Checklist

- [ ] Every expensive check (ZK verify, signature aggregation, Bulletproof verify, Merkle proof validation) — is it in a phase where the fee is charged even on failure?
- [ ] Every static check (value < max, flag set, field present) — is it in `preflight` so failures are free (no DB read)?
- [ ] Every ledger-state-reading check — is it in `preclaim`?
- [ ] Is any ledger-state write happening before `doApply`?

---

## 🚨 #3 — Amendment Gating Correctness

### The Misconception

> "The fix is gated by `rules.enabled(fixX)`. It's safe."

### The Reality

Amendment gates have several failure modes that a single `enabled()` check doesn't catch:

1. **Typo in feature name**: `rules.enabled(fixSecurity3_1_3)` vs `rules.enabled(fixSecurity3_1_2)` — silent bug. No compiler error, no test failure unless the test explicitly names the feature.
2. **Gate inversion**: `if (enabled(fix))` vs `if (!enabled(fix))` — off-by-one semantics.
3. **Residual reachable pre-fix branch**: After a fix is gated, the `else` branch still exists for history ledgers. Is it reachable under post-amendment state via some unexpected input?
4. **Amendment ordering**: If fix B depends on fix A being enabled first, does the code check them in the right order?
5. **Amendment-conditional struct layout**: A field exists only when an amendment is enabled. Code that reads the field must check amendment state first, not just field presence.

### Known Real Bug

- **XRPL #6867 neighborhood** (fixSecurity3_1_3 pre-fix assertions): Pre-amendment code used `assert()` for invariants that should have been error returns. The fix replaced assertions with proper returns, but the pre-fix branch is still present and reachable for history ledgers. Audit question: any remaining assertion-on-invariant in code paths reachable post-amendment?

### Checklist

- [ ] Every `rules.enabled(featureX)` — is the feature name correct and matches the intended fix?
- [ ] For every fix, is the pre-fix branch audited for reachability under post-amendment state?
- [ ] Cut-and-paste check: search for copy-pasted amendment checks with wrong feature names.
- [ ] Tests for both branches (pre-amendment and post-amendment)?

---

## 🚨 #4 — SLE (Serialized Ledger Entry) Field Access Semantics

### The Misconception

> "`(*sle)[sfX]` reads field X from SLE — standard lookup."

### The Reality

XRPL's SLE field access has subtle lifecycle and presence semantics:

1. **`(*sle)[sfX]` THROWS** if field X is absent. It does NOT return a default.
2. **`(*sle)[~sfX]`** returns `std::optional`. Use this form for optional fields.
3. **`(*sle)[~sfX].value_or(default)`** is the safe default-on-absent pattern.

### Known Attack Patterns

**Orphan SLE read**: Reading a field from an SLE that was just erased in the same tx. The SLE handle may still be valid in memory, but the ledger state it references is gone.

- **XRPL #6895** (MPTokenIssuanceDestroy reads sponsor from erased SLE): The destroy path read `sfSponsor` from an SLE that had just been erased in an earlier step. The value was stale or undefined depending on timing.

**Amendment-conditional field access**: A field exists only after an amendment is enabled. Code that reads the field without checking the amendment state throws on older ledgers during replay.

### Checklist

- [ ] Every `(*sle)[sfX]` — is X guaranteed present? If not, use `~sfX` form.
- [ ] Every field read after an erase operation — is the field from the erased SLE or a different one?
- [ ] For amendment-conditional fields, is the amendment state checked before the field read?
- [ ] `view.read()` (const) vs `view.peek()` (mutable) — are you reading the right view for the phase?

---

## 🚨 #5 — Consensus Determinism

### The Misconception

> "The code is single-threaded, so all nodes see the same state — consensus is automatic."

### The Reality

Consensus determinism requires that every validator produces **bit-identical** state transitions. Several subtle sources of non-determinism exist:

1. **`std::unordered_map` / `std::unordered_set` iteration order** is implementation-defined. If iteration result affects consensus (signature aggregation order, tx apply order, vote tally), validators with different libstdc++ versions will fork.
2. **`std::map` iteration is deterministic** (ordered by key), but the key type matters — pointer keys are not deterministic across processes.
3. **RNG**: `rand()`, `std::random_device`, `std::mt19937` seeded by time/address — all non-deterministic. Consensus RNG must use a deterministic seed derived from ledger state.
4. **Wall-clock time**: `std::chrono::system_clock::now()` varies across nodes. Ledger-relevant time must come from `parent_close_time`.
5. **Floating point**: IEEE 754 arithmetic is deterministic, but compiler optimizations (FMA, reassociation, `-ffast-math`) break determinism. Pure integer arithmetic is safer in consensus paths.
6. **Pointer-based ordering**: `sort(vec.begin(), vec.end(), [](auto* a, auto* b) { return a < b; })` — pointer addresses differ across processes.

### Checklist

- [ ] No `std::unordered_*` container in any consensus code path (tx apply, signature aggregation, vote tally).
- [ ] No `rand()`, `std::random_device`, or time-seeded RNG in consensus.
- [ ] No `std::chrono::system_clock::now()` in tx processing — use `parent_close_time`.
- [ ] No `float`/`double` in tx value calculation — use fixed-point integers.
- [ ] No pointer-address ordering.

---

## 🚨 #6 — Invariant Coverage Completeness

### The Misconception

> "There's an invariant check for field X, so field X is protected."

### The Reality

Invariants in XRPL are implemented as a chain of `InvariantCheck` subclasses that run after `doApply`. Several gaps are possible:

1. **Tx-type coverage gaps**: An invariant may `return true;` for certain tx types, skipping them entirely. If the skipped tx type can violate the invariant, the skip is a bug.
2. **Field-level coverage gaps**: An invariant checks field X but not field Y, even though X and Y must move in lockstep.
3. **New tx types in old invariants**: When a new tx type is added, every relevant existing invariant must be updated. Missing update = new tx type escapes the invariant.
4. **Return code bugs**: `return true;` means "invariant passes." An errant `return true;` in an error path passes a failing tx.
5. **Invariant test coverage**: `Invariants_test.cpp` should exercise every invariant against every relevant tx type. Gaps in the test file indicate gaps in the invariant suite.

### Known Real Bug

- **XRPL #6908** (ValidMPTPayment invariant skips confidential tx types): The `ValidMPTPayment` invariant returned `true;` unconditionally for any confidential MPT transaction type, meaning no payment validation was performed. A confidential payment could violate balance invariants without detection.

### Checklist

- [ ] For every invariant, list the tx types it checks vs the tx types it skips. Are the skips justified?
- [ ] For every new tx type, list the invariants updated vs the invariants not updated.
- [ ] Grep for `return true;` in `*Invariant.cpp` files — is any of them in an error path?
- [ ] Every invariant has a corresponding test in `Invariants_test.cpp` covering every relevant tx type.

---

## 🚨 #7 — Fiat-Shamir Context Binding (Crypto Protocol)

### The Misconception

> "The Fiat-Shamir transform takes a hash of the public inputs — it's secure."

### The Reality

Fiat-Shamir transforms prove a statement by hashing all relevant context into the challenge. **Missing any context field** allows the same proof to be replayed in a different context where the statement is not actually true.

Common missing fields:

1. **Version / protocol ID**: Same proof accepted across protocol versions with different semantics.
2. **Contract / ledger identifier**: Proof replayed across ledgers or side chains.
3. **Statement parameters**: Proof about commitment C accepted for a different commitment C' if C is not in the hash.
4. **Domain separation tag**: Two different proof types sharing a hash function without a DST allow cross-type replay.

### Known Real Bug

- **XRPL #6875** (Clawback context hash missing version): The Fiat-Shamir challenge hash for a Clawback proof did not include a version byte. A proof generated for version N could be replayed at version N+1 where the Clawback semantics changed, enabling an unauthorized claw.

### Checklist

- [ ] For every Fiat-Shamir transform, list all fields hashed into the challenge. Compare to the statement being proven.
- [ ] Is a version byte or protocol ID in the hash?
- [ ] Is a domain separation tag in the hash (or is the hash function purpose-specific)?
- [ ] Are all public inputs of the statement in the hash?

---

## 🚨 #8 — Owner Count and Reserve Accounting

### The Misconception

> "Every object creation adjusts the owner count, so reserves are consistent."

### The Reality

Owner count drift occurs when creation and destruction paths do not exactly mirror each other:

1. **Create without adjust**: A new object is created but `adjustOwnerCount(+1)` is not called. Reserve undercounted → account can create more than it should.
2. **Destroy without adjust**: An object is destroyed but `adjustOwnerCount(-1)` is not called. Reserve overcounted → account cannot delete last object to recover the reserve slot.
3. **Partial create**: Creation involves multiple SLEs. Adjusting count for only some = drift.
4. **Base reserve vs incremental reserve double-charge**: Base reserve is per-account; incremental is per-object. Sponsors paying the base reserve when the sponsee already paid it = double-count.
5. **Co-signed create cycles**: A feature that allows creating an object via multiple parties can inflate the owner count if each party increments independently.

### Known Real Bugs

- **XRPL #6863** (Co-signed create cycles inflate ReserveCount): A create-with-cosign flow incremented the owner count for each cosigner independently, inflating it unboundedly.
- **XRPL #6894** (Sponsor base reserve double-count): Sponsor paid the base reserve for a sponsee who had already paid it. Net effect: sponsee overcharged.

### Checklist

- [ ] Every `adjustOwnerCount(+1)` is paired with exactly one `adjustOwnerCount(-1)` on destruction.
- [ ] Base reserve charged exactly once per account (not multiple times via sponsor/delegate).
- [ ] Multi-party create flows increment the owner count exactly once per object created.
- [ ] `dirInsert` paired with `dirRemove` — no orphan directory entries.

---

## 🚨 #9 — Cross-Transaction Composition (Batch, Sponsor, Delegate)

### The Misconception

> "Each composition feature is unit-tested. Combining them is safe because each layer enforces its own auth."

### The Reality

Composition features add auth layers that must compose correctly. Common failure modes:

1. **Auth layer confusion**: Inner tx's `sfAccount` could be the grantor (delegate case), the sponsee (sponsor case), or the batch initiator. Getting it wrong cross-wires permissions.
2. **Fee/reserve accounting across wrappers**: Fee charged once at the outer vs per-inner. Reserves tracked against outer or inner account. Wrong answer = free txs or wrongly charged txs.
3. **Sequence/ticket uniqueness**: Inner txs in atomic batches must use distinct sequences. Same-seq inner = replay.
4. **Partial failure semantics**: `UntilFailure` / `OnlyOne` modes — what state persists when a mid-batch tx fails? Is the partial state rolled back or committed?
5. **Wrapper bypass**: Can the innermost operation be reached WITHOUT going through the wrapper's auth check?
6. **Triple composition**: Pairs may be dev-tested; triples may not. Batch × Sponsor × MPT can have a seam that neither pair-test catches.

### Checklist

- [ ] For each composition feature, trace `sfAccount` through every layer. Is the right account used at the right auth check?
- [ ] Fee payer resolution under composition — who pays?
- [ ] Sequence uniqueness across inner txs.
- [ ] Failure semantics — partial rollback or commit?
- [ ] Triple composition testing: Batch × Delegate × MPT, Batch × Sponsor × ConfMPT, Sponsor × Delegate × DEX — are they tested?
- [ ] Wrapper bypass: can the inner operation be called directly?

---

## 🚨 #10 — Assertions Are No-Ops in Release Builds

### The Misconception

> "There's an `assert(invariant)` that catches this case."

### The Reality

`assert()` is **stripped in release builds** (with `NDEBUG`). Any logic that depends on the assertion's side effect or early-exit is broken in release:

1. **Assertion as input validation**: `assert(!badInput)` — in release, the bad input passes through.
2. **Assertion on state invariants**: `assert(ownerCount >= 0)` — in release, the state continues with underflow.
3. **Assertion in hot path**: Should be an error return, not a crash.
4. **Partial-state assertion**: `assert(success)` followed by state mutation — release continues with partial state.

### Known Real Bug

- **XRPL #6867 neighborhood** (fixSecurity3_1_3 assertion replacement): Pre-fix code used assertions to enforce invariants. The fix replaced them with proper error returns. Audit question: any remaining assertions in post-amendment code paths that should be returns?

### Checklist

- [ ] Every `assert(x)` — is `x` guaranteed true by construction, or is it actually checking attacker input?
- [ ] If `x` can be false, replace with a proper error return.
- [ ] If the assertion is for a debug-only invariant, add a release-mode check.

---

## 🚨 #11 — C++ Undefined Behavior Traps

### The Misconception

> "The code compiles and tests pass, so UB is caught."

### The Reality

C++ has many silent UB traps that compilers may or may not catch:

1. **Signed integer overflow**: `INT_MAX + 1` is UB. Unsigned overflow is defined (wraps).
2. **Shift width overflow**: `x << 64` where `x` is `uint64_t` is UB. Always `assert(shift < sizeof(T)*8)`.
3. **Sequence point violation**: `i = i++ + 1` is UB.
4. **Union type punning**: Legal in C, UB in C++ pre-C++20. Use `std::bit_cast` or `memcpy`.
5. **Strict aliasing**: `*(float*)&int_var` is UB. Only `unsigned char*`/`std::byte*` can alias.
6. **Dangling reference**: `string_view v = f();` where `f()` returns `string` by value — temporary dies, v dangles.
7. **Self-move**: `x = std::move(x)` leaves x in indeterminate state.
8. **`memcpy` with overlap**: UB. Use `memmove`.
9. **INT_MIN negation**: `-INT_MIN` overflows signed int.
10. **`INT_MIN / -1`**: Signed overflow UB.

### Checklist

- [ ] Integer math on signed types — bounded or `checked_*`?
- [ ] Bit shifts — shift width bounded?
- [ ] Pointer aliasing only through `unsigned char*` / `std::byte*` / `memcpy`?
- [ ] String/span/view lifetimes — no dangling references across function returns?

---

## Prohibited Finding Patterns (Do Not Report)

These patterns are typically **out of scope** for XRPL-style contest audits:

1. ❌ **Trusted actor misbehavior** (UNL validator misbehavior, node operator misconfiguration) — trust model explicitly allows these.
2. ❌ **Duplicate of baseline version behavior** — if the bug was already present and at the same impact in a prior release, it's not a regression.
3. ❌ **Theoretical UB without reachable trigger** — UB that requires compiler internals to be exploited without a user-reachable path.
4. ❌ **Best-practice suggestions unrelated to security** — "use `std::optional` instead of raw pointer" without a concrete bug.
5. ❌ **Style / readability** — spec compliance and semantic bugs are in-scope, style is not.

---

## Baseline Known-Issue List (XRPL Specific)

When auditing XRPL, cross-check findings against this known-issue list. A finding with the same root cause is typically OUT of scope.

| Issue | Pattern | Status |
|-------|---------|--------|
| #6863 | Co-signed create cycles inflate ReserveCount | Known |
| #6867 | fixSecurity3_1_3 pre-fix assertions replaced with error returns | Known |
| #6875 | Clawback Fiat-Shamir context hash missing version byte | Known |
| #6884 | ZKP verification failures wrongly return `tecINTERNAL` | Known |
| #6894 | Sponsor base reserve double-counted when sponsee already paid | Known |
| #6895 | MPTokenIssuanceDestroy reads sponsor from erased SLE | Known |
| #6908 | ValidMPTPayment invariant unconditionally skips confidential tx types | Known |

For each finding you write:
- Is the root cause in this list? → Likely duplicate.
- Is the symptom similar but root cause different? → In scope; note the distinction.
- Is this a new pattern not in the list? → Highest-value finding.

---

## History of Lessons

Lessons learned from past XRPL audits get appended here. This document only improves by accumulating pain.

- 2026-04: Platform quirks file created. Seeded with 11 quirks from the existing `prompts/cpp/` depth templates, which themselves reference the 7 XRPL issue numbers above.
