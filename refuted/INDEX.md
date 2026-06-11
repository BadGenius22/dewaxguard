# Cross-Audit Refuted Vulnerability Classes

> **Tier 1 #3 (negative-results retrieval).** Before any agent invests depth/PoC budget in a hypothesis, grep this index. If the class appears here, read the **structural reason** — the hypothesis is dead ONLY if that reason also holds in the current target.
>
> **Hard rule — a refutation does not transfer automatically.** Each entry records WHY the class failed (a structural property of the audited system). The agent MUST verify the same property exists in the new codebase before discarding. If the property is absent, the class is LIVE and should be investigated normally.
>
> **Anti-anchoring rule.** Entries are class-level only — no project-specific finding text beyond what's needed to verify the structural reason. Per the ephemeral-session principle, this index stores negative knowledge (what was proven safe and why), never positive bug patterns.
>
> **Amendment rule.** If a later audit or contest result contradicts an entry (a finding in the "refuted" class turns out valid), NARROW the entry's scope and record the counterexample — see RF-03 for the canonical example. Never silently delete.

## Format

`RF-NN | class | language/protocol scope | structural reason for refutation | precondition to re-check in a new target | source`

## Entries

### RF-01 — Intra-block/ledger expiry race via timestamp drift
- **Scope**: XRPL (validated); analog check needed per chain
- **Structural reason**: XRPL `parentCloseTime` is per-ledger invariant — every transaction in a ledger sees the identical close time, so two ops in the same ledger cannot disagree about whether an expiry has passed. (XRPL R-69)
- **Re-check before transfer**: Does the target expose sub-block/sub-ledger time (e.g. per-instruction clocks, L2 sequencer timestamps, oracle-pushed time)? EVM `block.timestamp` is also per-block invariant → refutation transfers; systems with per-tx or per-shard time → class LIVE.
- **Source**: XRPL Sherlock 2026-04, Domain 19 (M-15 matrix)

### RF-02 — ConvertBack Enc(0)−Enc(X) → Enc(−X) extraction (confidential-amount conversion)
- **Scope**: XRPL mpt-crypto (C); any sigma+Bulletproof confidential-amount bundle
- **Structural reason**: sound via two-primitive composition — the sigma proof binds `PC_b` to the plaintext amount AND the verifier derives the remainder commitment itself (`pc_rem = PC_b − amount·G`), so the prover cannot supply a malicious remainder. (XRPL F-45; closes kuprum #6885/#6886)
- **Re-check before transfer**: (a) Does the target verifier DERIVE the remainder commitment (vs accepting it from the prover)? (b) Are amounts bound in TWO independent primitives? If either is no → class LIVE.
- **Caveat — scope is exactly conversion-extraction**: Sherlock 1260 F30 (Critical, forged proof drains shared confidential backing) was missed AFTER this refutation was recorded. Composition-correct ≠ forgery-resistant. Always still run M-16 Phase 2.7 (adversarial forgery construction) — this entry refutes only the Enc(0)−Enc(X) shape.
- **Source**: XRPL Sherlock 2026-04 Domain 15 (M-16); amended per Sherlock 1260 post-mortem 2026-06

### RF-03 — "Read-only RPC periphery cannot cause impact" (AMENDED — partially overturned)
- **Scope**: any node-client / consensus codebase with an RPC layer
- **Structural reason (surviving part)**: read-only RPC handlers cannot mutate consensus state, so consensus-integrity / fund-movement claims through pure-read RPC paths remain refuted. (XRPL R-71)
- **Counterexample (overturned part)**: Sherlock 1260 validated **F39 `book_offers`** (RPC read path) as High — wrong data served by a read-only endpoint IS impactful when users/integrators make economic decisions on it. Do NOT use this entry to discard wrong-data RPC findings.
- **Re-check before transfer**: Is the claimed impact (a) state mutation via RPC → still refuted, or (b) incorrect data driving off-chain economic decisions → LIVE, investigate.
- **Source**: XRPL Sherlock 2026-04 (R-71); amended per Sherlock 1260 post-mortem 2026-06

### RF-04 — Bulletproof H_vec[0] == pk_base generator-collision forgery
- **Scope**: mpt-crypto-style BP implementations over libsecp256k1
- **Structural reason**: generator derivation domain-separates the H vector from the public-key base point; the collision needed for the forge is structurally unreachable. (XRPL R-09/R-20/R-68 family)
- **Re-check before transfer**: How does the target derive its BP generators? Hash-to-curve with domain tags → refutation transfers; reused/configurable generators → class LIVE.
- **Source**: XRPL Sherlock 2026-04, Domain 15 (M-16)

### RF-05 — Identity-point / scalar-overflow ingress on proof verification
- **Scope**: mpt-crypto (C, libsecp256k1-based)
- **Structural reason**: ingress validation rejects identity points and out-of-range scalars at deserialization, before any arithmetic. (XRPL R-02/R-04)
- **Re-check before transfer**: Does the target validate points/scalars at PARSE time (vs trusting them into arithmetic)? Libraries that defer validation → class LIVE.
- **Source**: XRPL Sherlock 2026-04, Domain 15 (M-16)

### RF-06 — Issuer flag-clear retroactivity as a SYNC_GAP family
- **Scope**: XRPL MPT/token flags; generalizes to any flag system with fresh consumer reads
- **Structural reason**: consumers re-read flags fresh at use time (no grandfathering / no snapshot at create), so clearing a flag cleanly changes future behavior without stranding state. A 6-flag retroactive-clear sweep found exactly ONE instance where an aggregate counter snapshot broke this (CONF-1) — the rest are by-design. (XRPL R-82, F-47)
- **Re-check before transfer**: Does ANY consumer snapshot the flag/config at create time (asymmetric lock-in, D-42 pattern)? Each snapshot site is a LIVE candidate; fresh-read sites are refuted.
- **Source**: XRPL Sherlock 2026-04, Domain 16 (M-17)

### RF-07 — Mutation-allowed-bit (`lsmfMPT*CanMutate*`) immutability bypass
- **Scope**: XRPL XLS-0094 Dynamic MPT
- **Structural reason**: the mutability tier-bits themselves are structurally excluded from the mutable set — confirmed by 4-agent independent convergence. (XRPL R-83)
- **Re-check before transfer**: In any "flags-controlling-flag-mutability" system, verify the meta-flag is outside its own mutable set. If the meta-flag is itself mutable → class LIVE (and likely Critical).
- **Source**: XRPL Sherlock 2026-04, Domain 16 (M-17)

### RF-08 — Soroban TTL-expiry state loss ("expired entry = deleted data")
- **Scope**: Stellar Soroban v23+
- **Structural reason**: persistent/instance storage ARCHIVES on TTL expiry with values preserved; archived entries are restorable and reads after restore see the original value. "TTL expiry silently zeroes/defaults state" findings are invalid on v23+. (K2 V12 #44792 Invalid-reason corpus)
- **Re-check before transfer**: Soroban protocol version < 23, or TEMPORARY storage (which IS deleted on expiry) → class LIVE for temporary entries only.
- **Source**: K2 Code4rena Stellar 2026-04/05 (M-25 V12 corpus); platform-quirks/stellar.md

### RF-09 — Soroban cross-contract reentrancy
- **Scope**: Stellar Soroban
- **Structural reason**: the Soroban host does not permit reentrant cross-contract calls — `invoke_contract` into a contract already on the call stack traps. Classic EVM-style reentrancy findings are invalid. (K2 HF44 arbitration: engine `invoke_contract` is SAFE)
- **Re-check before transfer**: Only applies to Soroban. On any other runtime (EVM, Solana CPI depth limits notwithstanding), reentrancy analysis proceeds normally.
- **Source**: K2 Code4rena Stellar 2026-04/05 (agent-failure-recovery retro)

### RF-10 — "Public entry point = missing auth" on capability/auth-inside runtimes
- **Scope**: Stellar Soroban (validated); analog on Move
- **Structural reason**: Soroban entry points are public by construction; authorization happens INSIDE via `require_auth`. Flagging a public entry point without tracing the internal auth chain is a known false-positive class (66-entry V12 Invalid corpus is dominated by it).
- **Re-check before transfer**: Trace the internal auth: if `require_auth`/capability check is genuinely absent on a state-mutating path → LIVE finding. The refuted class is "public visibility alone", not "missing auth".
- **Source**: K2 Code4rena Stellar 2026-04/05 (M-25 V12 corpus)

### RF-11 — Cancellable-escrow expiry-boundary races (who-wins-at-boundary)
- **Scope**: XRPL escrow family
- **Structural reason**: with per-ledger invariant time (RF-01) plus canonical transaction ordering, boundary races reduce to deterministic outcomes already covered by the ESC-1/2/3 root-cause family; no NEW class exists at the boundary itself. (XRPL R-70)
- **Re-check before transfer**: On chains where ordering is bidder-controlled (MEV) or time is sub-block, boundary races are LIVE — this refutation leans on BOTH per-ledger time and canonical ordering.
- **Source**: XRPL Sherlock 2026-04, Domain 19 (M-15)

### RF-12 — EVM-style lost-update race on a Sui/Move shared-object field
- **Scope**: Sui Move (shared objects); analog caution for any consensus-serialized object runtime
- **Structural reason**: a transaction taking a shared object as `&mut` acquires exclusive access; Sui sequences all transactions touching that object through consensus into a total order and executes them one at a time. Two transactions cannot interleave a read-modify-write on the same shared object, so the "both read the old counter, both +1, net +1 instead of +2" race is impossible. Owned objects are stronger still (only the owner mutates, fast path).
- **Re-check before transfer**: Is the conflicting read and write in the SAME transaction (atomic — no race) or DIFFERENT transactions (this is cross-tx **staleness**, not a race — LIVE only if you can prove an attacker-controlled window AND the stale value gates value movement)? On non-serialized runtimes (EVM, raw multithreaded state) the class is LIVE.
- **Caveat**: Sui *equivocation / object-version contention* (liveness/grief when a sender double-spends an owned-object version) is a real and DISTINCT concern — do not use this entry to dismiss it.
- **Source**: v1.21.0 blind benchmark (`sui-shared-object-race`); see `platform-quirks/sui.md` #1

## How agents use this index

1. **At hypothesis generation** (breadth/depth): grep this file for class keywords before writing the hypothesis into the work queue. On hit → read the entry → verify the structural reason against the CURRENT target → either discard (reason holds; cite `RF-NN` in the refutation log) or proceed (reason absent; note "RF-NN does not transfer because …").
2. **At post-audit growth**: promote new R-entries from the project-local manifest here ONLY if (a) class-level, (b) the structural reason is stated, (c) a re-check precondition is written. Raw project-specific refutations stay in the project manifest.
3. **On contradiction**: apply the Amendment rule (see RF-03) — narrow, never delete.
