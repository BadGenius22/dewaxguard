# Phase 4b: Runtime/Execution-Specific Attacks — C/C++ Ledger Nodes

> **Runtime**: Native C++ consensus nodes (XRPL/rippled, Bitcoin Core, Aptos/Move VM, Diem-derived chains, consensus-critical daemons)
> **Agent**: depth-runtime
> **Focus**: Transactor state machines, consensus invariants, amendment/feature gating, cross-tx composition, p2p protocol handling
>
> **🚨 REQUIRED READING**: Before starting, the agent MUST read `~/.claude/skills/dewaxguard/platform-quirks/cpp.md`. It documents 11 critical quirks and a baseline known-issue list with 7 historical XRPL bugs. Each finding MUST be cross-checked against the known-issue list — findings with the same root cause as a known issue are out of scope.

> **Note**: C++ ledger runtimes are NOT like EVM/Solana/Move smart contracts. There is NO sandboxed VM, NO permissionless call stack, NO reentrancy in the Solidity sense. The attack surface is: network messages, transaction validation, state machine transitions, consensus determinism, cryptographic protocols, and p2p handling. The checks below are tuned for THAT model.

---

## SYSTEMATIC CHECKS

### A) Transaction validation phase ordering
```bash
rg -n "preflight\b|preclaim\b|doApply\b|preflight2\b" --type cpp
rg -n "checkFee|checkSign|checkSeq|checkPriorTxAndLastLedger" --type cpp
```
For each transactor:
1. **Static vs dynamic checks in the right phase**: preflight should validate STATIC properties (field shapes, signatures, flags). preclaim should validate DYNAMIC state (account exists, balance, authorization). doApply should validate FINAL invariants. A static check in preclaim wastes ledger state reads; a dynamic check in preflight fails across ledger closes.
2. **Expensive operation placement**: ZK proof verification, signature aggregation, Bulletproof verify, Merkle path validation. These should ideally be in preclaim AFTER cheap checks reject obvious bad inputs, so attackers can't burn node CPU with cheap-to-craft invalid-proof txs. Pattern to find: expensive op in preclaim with no cheap pre-check.
3. **TER result class (rippled-specific)**: `temX` = static reject, no fee charged. `tefX` = failure, fee charged, tx stored. `tecX` = runtime reject, fee charged, tx stored. `terX` = retry-later. **Wrong class = economic bug**. Example: returning `tecINTERNAL` for a user-correctable error charges the user for the node's mistake.
4. **Preflight2 signature check**: `preflight2()` checks signatures for normal txs; returns early for inner batch txs. Under what conditions can the signature check be skipped when it shouldn't be?

### B) Amendment / feature flag gating
```bash
rg -n "rules\(\)\.enabled\(|view.*rules.*enabled|ctx.*rules.*enabled" --type cpp
rg -n "feature\w+|fix\w+" --type cpp | grep -v test | head -50
```
For each `rules().enabled(featureX)` check:
1. **Gate inversion**: `if (rules.enabled(fix))` vs `if (!rules.enabled(fix))` — easy off-by-one in negation.
2. **Wrong feature name**: Cut-and-paste bugs where a fix is gated by an UNRELATED feature.
3. **Missing gate**: New behavior added without a gate — breaks deterministic replay of history ledgers.
4. **Pre-fix branch reachability**: Most fixes have an `else` branch for pre-amendment behavior. Is the pre-fix branch actually unreachable under post-amendment state, or can a specific input-state combo resurrect the old bug?
5. **Gate ordering**: Two amendments that depend on each other — does the gate check the right one first?
6. **Amendment-conditional struct layout**: A field that exists only when an amendment is enabled — is field presence checked before read?

### C) SLE (Serialized Ledger Entry) lifecycle and orphan reads
```bash
rg -n "view\.(read|peek|erase)|keylet::" --type cpp
rg -n "dirRemove|dirInsert|dirAdd" --type cpp
rg -n "adjustOwnerCount" --type cpp
```
For each ledger state mutation:
1. **Owner count consistency**: Every object creation → `adjustOwnerCount(+1)`. Every deletion → `adjustOwnerCount(-1)`. Missing either side = reserve accounting drift.
2. **Orphan read**: Reading a field from an SLE that was just erased (or about to be erased). Example pattern from XRPL #6895: `MPTokenIssuanceDestroy` reads sponsor from an erased SLE.
3. **Directory linkage**: `dirInsert` → `dirRemove` must be paired. Orphan directory entries break iteration.
4. **Keylet mismatch**: Two code paths computing a keylet with different inputs → write to one location, read from another.
5. **Partial state mutation under exception**: If an exception throws between two related state updates, does the ledger apply partial state?
6. **View vs PeekableView**: `view.read()` is const; `view.peek()` returns mutable. Mixing them can cause stale reads within a single tx.

### D) Consensus determinism
```bash
rg -n "std::unordered_(map|set)" --type cpp
rg -n "std::map\|std::set" --type cpp | head -20
rg -n "rand\(\)\|mt19937\|random_device" --type cpp
rg -n "timestamp\|now\(\)\|system_clock" --type cpp
```
1. **Unordered containers in consensus path**: `std::unordered_map` iteration order is implementation-defined. If iteration result affects consensus (tx apply order, signature aggregation order), nodes will diverge.
2. **RNG in consensus**: Randomness must be deterministic across nodes. `rand()` or `std::random_device` in a code path that feeds consensus = fork.
3. **Wall-clock time in consensus**: `std::chrono::system_clock::now()` varies across nodes. Ledger time comes from the last-closed-ledger `parent_close_time`, not host clock.
4. **Floating point in consensus**: IEEE 754 is deterministic, but compiler optimizations (FMA, reassociation) are not. Grep for `float`/`double` in tx application paths.
5. **Pointer-based ordering**: Sorting by address hash = non-deterministic.

### E) p2p / network message handling
```bash
rg -n "read.*Message|parse.*Message|deserialize|fromProto|fromJson" --type cpp
rg -n "send.*Peer\|Overlay\|PeerImpl" --type cpp | head -20
```
1. **Message length validation**: Attacker-controlled length field used in memcpy/memmove — classic buffer overflow.
2. **Recursive parsing**: Deeply nested messages can stack-overflow if no depth limit.
3. **Zip bomb / proof bomb**: Small compressed message expands to huge uncompressed data — memory exhaustion.
4. **Peer ID spoofing**: Is the peer's claimed identity verified against their signing key?
5. **Unsolicited response handling**: Does the node accept a response that wasn't paired with a request? Could be used for cache poisoning.
6. **Rate limiting**: Is there a per-peer rate limit on expensive operations (proof verification, signature aggregation)?

### F) Cross-tx composition (Batch, Sponsor, Delegate, etc.)
```bash
rg -n "sfDelegate|sfSponsor|sfBatchSigners|tfInnerBatchTxn" --type cpp
```
For any composition feature:
1. **Auth check layering**: Each wrapper adds an auth layer. Does each inner operation see the correct account for its own auth check? Pattern from XRPL: `ctx.tx[sfAccount]` for inner = grantor (delegate case) or sponsee (sponsor case). Getting it wrong cross-wires permissions.
2. **Fee/reserve accounting across wrappers**: Fee charged once at the outer, or per-inner? Reserves tracked against outer or inner account?
3. **Sequence/ticket uniqueness**: Inner txs in atomic modes must use distinct sequences. Same-seq inner txs = replay.
4. **Partial failure semantics**: In `UntilFailure` / `OnlyOne` modes, what state does a mid-batch failure leave? Does inner-N's state persist if inner-N+1 fails?
5. **Wrapper bypass**: Can the innermost operation be executed WITHOUT going through the wrapper's auth? E.g., a batch inner tx bypass when cosign is not required.
6. **Wrapper composition**: Feature A wrapping feature B wrapping feature C. Each pair may be dev-tested, but the triple may have a seam. Specifically check:
   - Batch × Delegate × ConfMPT
   - Batch × Sponsor × ConfMPT
   - Sponsor × Delegate × MPT_DEX

### G) Invariant coverage completeness
```bash
rg -n "Invariant\.cpp|InvariantCheck|class.*Invariant" --type cpp | head -30
```
For each invariant:
1. **Tx-type coverage**: Does the invariant fire on ALL relevant tx types, or does it skip some? Pattern from XRPL #6908: `ValidMPTPayment` invariant skips all confidential tx types.
2. **Field-level coverage**: An invariant that checks field X should also check related fields Y and Z that must move in lockstep.
3. **Short-circuit escape**: `if (txType == ttX) return true;` — is the skip safe, or does it let state-corrupting txs slip through?
4. **Invariant return code**: Returning `true` = pass. Is there a `return true;` in an error path that should be `return false;`?
5. **New tx types in old invariants**: When a new tx type is added, is every relevant invariant updated to handle it?

### H) Cryptographic protocol integration
```bash
rg -n "EVP_\|SHA256\|Keccak\|Blake\|secp256k1_\|ec_(sign|verify)\|BN_" --type cpp
rg -n "FiatShamir\|contextHash\|challenge\|transcript" --type cpp
```
1. **Fiat-Shamir context binding**: What data is in the challenge hash? Missing a field = cross-context proof replay. Example patterns from XRPL #6875 (Clawback context hash missing version).
2. **Signature verification result ignored**: `ec_verify(...)` return value not checked, or checked with wrong sense.
3. **Constant-time comparison**: Cryptographic equality should use constant-time compare (`CRYPTO_memcmp`, `sodium_memcmp`). `memcmp` for MAC/signature = timing oracle.
4. **Non-canonical signatures**: Is the low-S form enforced? High-S is valid under curve math but breaks uniqueness (transaction malleability).
5. **Off-curve points**: Public keys / commitments must be validated as curve points before use.
6. **Zero as secret**: Discrete log proofs with witness=0 behave degenerately. Check for explicit zero-witness rejection.
7. **Domain separation**: Hash inputs for different purposes must have distinct tags. Missing DST = cross-protocol attack surface.

### I) Resource exhaustion / DoS
1. **Unbounded loop**: Transaction application that iterates over attacker-controlled list — is there a cap? (Rippled checks txn sizes in preflight but iterates object lists in doApply.)
2. **Proof verification cost**: ZK proof verify is expensive. Can an attacker submit many low-fee txs that each trigger expensive verify before being rejected?
3. **Memory during parse**: Are parser stack limits set? Recursive struct serialization can eat stack.
4. **Storage growth**: Objects that can be created cheaply but persist in ledger forever.
5. **Consensus vote flood**: Amendment voting messages — bounded per ledger close?

### J) Time-based logic
```bash
rg -n "parent_close_time\|netTime\|ledgerClose|EscrowFinish|CheckCancel" --type cpp
```
1. **Clock source**: All consensus-affecting time must come from `parent_close_time`, not host clock.
2. **Boundary inclusivity**: `finishAfter == parent_close_time` — is the boundary inclusive or exclusive? Common off-by-one.
3. **Expiry windows**: Ledger checks `time > expiry` — if expiry is 0 or unset, is the object permanently valid or permanently expired?
4. **Amendment activation time**: Features take effect at the ledger AFTER the amendment is supported by majority. Tests that assume instant activation miss the one-ledger gap.

### K) Fee, reserve, and ownership accounting
```bash
rg -n "sfBalance\|sfReserveCount\|sfOwnerCount\|sfSponsorCount" --type cpp
rg -n "adjustOwnerCount\|checkInsufficientReserve" --type cpp
```
1. **Reserve drift**: Every owned object contributes to reserve. Every create → +1, every destroy → -1. Pattern from XRPL #6863: co-signed create cycles inflate ReserveCount unboundedly.
2. **Base reserve vs incremental reserve**: Base is per-account, incremental is per-object. Sponsor paying base when sponsee already paid it = double-count (XRPL #6894).
3. **Fee payer resolution**: Under Sponsor/Delegate, who is the fee payer? Mis-resolution = free txs or wrongly charged txs.
4. **Ownership accounting under delete**: When an object is deleted, all its related counters must decrement. Pattern from XRPL #6895 (MPTokenIssuanceDestroy reads sponsor from erased SLE).

### L) Test coverage gap mining
```bash
rg -n "BEAST_EXPECT\|BEAST_REQUIRE\|BEAST_DEFINE_TESTSUITE" --type cpp | head -50
```
For the `src/test/app/` directory:
1. **Test titles tell you what devs worry about**: Enumerate test case titles per feature. Seams tested in dev are OUT of the audit opportunity; seams NOT tested are IN.
2. **Known-bug tests**: Tests labeled "pre-fix", "known bug", "legacy" mark the pre-amendment/post-amendment boundary. Read both branches.
3. **Invariant test coverage**: `Invariants_test.cpp` should test every invariant against every relevant tx type. Gaps there are gaps in the invariant suite itself.

---

## DEEP ANALYSIS QUESTIONS

For each candidate:

1. **Actor category**: Who triggers the bug? Permissionless user / semi-trusted admin / UNL validator / node operator? Trusted actors are typically out-of-scope for contest findings.
2. **Baseline comparison**: Was this behavior reachable in the previous version? What was its impact then? The current version must show STRICTLY ELEVATED impact to be in-scope.
3. **Invariant break**: Does the bug break a stated invariant in code comments, a spec requirement (XLS-NNNN), or an implicit assumption made elsewhere in the codebase?
4. **PoC feasibility**: Can this be demonstrated with a `beast::unit_test` using the jtx helpers? If not, it can't be submitted.
5. **Known-issue dedupe**: Cross-check the root cause against the known-issue baseline. Same root cause = OUT of scope. Same symptom with different root cause = IN.

## Ledger-runtime-specific common vulnerability classes

Top C++ ledger bug patterns to recognize on sight:

1. **Stale view snapshot in multi-step ops**: A loop reads a state value at iteration 0 and doesn't refresh across iterations — aggregate check undercounts concurrent changes.
2. **Amendment-gated fix with residual reachable pre-fix branch**: Rare but high-value.
3. **Invariant escape via specific tx type**: e.g., "skip invariant if tx is LoanBrokerDelete" — can attacker craft a state where the escape is exploitable?
4. **TER wrong class (tem/tef/tec/ter)**: Economic bug, low severity but in-scope for spec-compliance judging.
5. **Field read before presence check**: `(*sle)[sfX]` without first checking `isFieldPresent(sfX)`.
6. **Owner count drift**: +1/-1 imbalance in create/destroy.
7. **Cross-feature composition auth bypass**: Wrapper A's auth check doesn't fire when wrapped by B.
