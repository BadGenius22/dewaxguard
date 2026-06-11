---
id: M-16
name: zk-proof-bundle-composition
trigger_type: code
trigger_grep: "bulletproof|range[_ ]?proof|groth16|\bplonk\b|halo2|pedersen|fiat[_-]?shamir|schnorr|elgamal|\bsnark\b|zk[_ ]?(proof|snark|verif)|circom|\bnoir\b|sigma[_ ]?protocol|equality[_ ]?proof"
trigger_languages: [all]
applies_to_protocol_types: [zk]
---
# M-16 — ZK-Proof-Bundle Composition Audit

> **Purpose**: systematic methodology for auditing any protocol that composes ≥2 zero-knowledge primitives (sigma + range proof, sigma + linkage, equality + range, verifier-derived public commitments) OR any protocol where a cryptographic bundle wraps multiple Fiat-Shamir transcripts under a single operation.
>
> **Status**: first validated on XRPL April 2026 audit (Domain 15, 8-agent breadth, 2026-04-24). Populated ~50 composition-matrix cells across 4 rippled-reachable + 3 unreachable bundles. 0 Medium+ submissions but 6 cross-language meta-patterns validated against 6,364 LoC C cryptographic library.
>
> **Cross-language**: applies to EVM (Aztec, Railway, zkBob, zkSync confidential, Groth16/Plonk verifiers), Solana (light-protocol, Elusiv), Aleo (record programs), Noir/Circom (range-proof circuits), Move (future Sui/Aptos native ZK verifiers), any Fiat-Shamir sigma/range-proof composition.

---

## Trigger

Invoke this methodology when the protocol under audit has ANY of:

1. **Two or more ZK primitives composed** in a single operation — e.g., sigma protocol + Bulletproof range proof, sigma + linkage proof, Schnorr PoK + equality proof, Groth16 + outer wrapper.
2. **Verifier-derived public commitments** — the verifier computes a commitment (e.g., `pc_rem = PC - amount*G`) from inputs and feeds it to a downstream primitive's transcript.
3. **Multi-recipient / multi-party proofs** — e.g., shared-randomness ElGamal across N recipients, multi-auditor confidential transfers.
4. **Paired transactors** — tx types that come in pairs where each operation's context hash format MUST distinguish from its sibling (Send/ConvertBack, Deposit/Withdraw, Stake/Unstake, Lock/Unlock).
5. **Cryptographic primitive library with layered consumer** — the protocol links a separate crypto library (e.g., `libsecp256k1`, `arkworks`, `bellman`, `circom-compat`) and may have orphan exported primitives.

---

## Phase 0 — Orphan-Public-API Reachability Check (FIRST FILTER)

Before investing depth budget on any primitive's soundness, **verify consumer-layer reachability**.

### Steps

1. Enumerate every public function exported by the primitive library (e.g., `grep -E "^[a-z_0-9]+\s*\(" include/*.h`).
2. For each exported symbol, grep the CONSUMER layer (protocol code) for any invocation.
3. Also grep sibling bundle layers — e.g., higher-level bundle wrappers that may call the primitive internally.
4. **Zero-caller primitives → LEGACY/DEAD-CODE**:
   - Any soundness bug confined to a zero-caller file cannot be PoC'd via public transactions.
   - Such findings are T-07-ineligible in Sherlock-style contests ("coded PoC mandatory").
   - Document as Informational only; skip deep soundness analysis.

### Concrete example (Domain 15 / mpt-crypto)

```bash
grep -rn "secp256k1_elgamal_pedersen_link\|prove_equality_shared_r\|verify_equality_shared_r" \
     rippled/src/ mpt-crypto/src/proof_compact_*.c
# → 0 callers
```

Three files (1161 LoC total) were identified as orphan public API:
- `proof_link.c` (407 LoC)
- `equality_proof.c` (345 LoC)
- `proof_same_plaintext_multi_shared_r.c` (409 LoC)

Header comment at `secp256k1_mpt.h:214` documents linkage API as "Legacy Variant B format; superseded by compact proof APIs. Removed in PR #22." Any kuprum-reported bug in these files (mpt-crypto#37/#38/#43/#45) cannot be exploited via rippled transactions — saved ~20% of depth budget.

### Cross-language applicability

| Platform | Where orphan APIs hide |
|---|---|
| **EVM** | Verifier precompiles unused by production contracts; exported functions in OpenZeppelin-style libraries |
| **Solana** | Exported entrypoints that aren't invoked by the primary instruction dispatcher; legacy `instruction.rs` variants |
| **Aleo / Noir / Circom** | Template circuits shipped but not instantiated by any `aleo-program` / `nargo.toml` deployment |
| **Move (Sui / Aptos)** | Public functions in a published package that no consumer module calls |

### Efficiency gain

Skipping deep soundness analysis on unreachable primitives **preserves audit depth budget for reachable code**. Validated 3x in Domain 15.

---

## Phase 1 — Build the Composition Matrix

For every rippled-reachable bundle, populate cells across 8 invariant dimensions × N primitives.

### 8 invariant dimensions

| # | Dimension | Question |
|---|---|---|
| 1 | **Transcript completeness** | Does every public statement variable appear in the Fiat-Shamir challenge hash? Does it ALSO appear in any deterministic-nonce statement_hash? Any field dropped between prover and verifier? |
| 2 | **Domain separation** | Is every tag unique? Any tag a prefix of another? Enumerate via `grep -E 'EVP_DigestUpdate.*"[A-Z_]{5,}"'` to catch inline literals, not just documented tags. |
| 3 | **Primitive composition** | When bundle X uses primitives A+B+C, does A's verification assume something B/C doesn't enforce? Are shared variables (Pedersen commitments, public keys) passed consistently to all primitives? |
| 4 | **Cross-recipient / cross-user witnesses** | If prover knows other witnesses (other holders' keys, old balances, auditor state), can they forge one proof while others remain sound? |
| 5 | **Boundary values** | Zero witness, zero amount, maxed amount, identity point, `r=0` mod n, compromised key, expired ledger, first-depositor, zero-supply. Test each at prover AND verifier side. |
| 6 | **Binding across operations** | Does the proof's context bind to specific sender's current balance version? Can a proof be replayed across txs? Across contracts? Across chains? |
| 7 | **Error-path resource leaks** | `malloc`/`free` completeness on `goto fail` paths. `EVP_MD_CTX`/`EVP_MAC_CTX` cleanup. Heap sizes attacker-controlled? Stack residue of secrets? |
| 8 | **Reject-valid / accept-invalid asymmetry** | Prover-side overly strict rejection (DoS class) vs verifier-side overly lax (soundness class). Which direction does the library prefer? |

### Example populated cells (mpt-crypto ConvertBack bundle)

| Cell | Status | Evidence |
|---|---|---|
| Transcript completeness (sigma) | VERIFIED SAFE | All (pk_A, B1, B2, PC_b) hashed |
| Domain separation | VERIFIED SAFE | `"CMPT_CONVERTBACK_SIGMA"` unique |
| Primitive composition (sigma ∧ BP) | VERIFIED SAFE | `pc_rem = PC_b - amount*G` verifier-derived, BP binds pc_rem |
| Boundary: b=0 (Enc(0)-Enc(X) case) | REFUTED exploitable | BP rejects `b - amount mod n ≈ 2^256 > 2^64` |
| Amount binding | VERIFIED SAFE (novel) | Amount NOT in sigma BUT bound via BP's pc_rem transcript — two-primitive pattern |
| Error-path leaks | VERIFIED SAFE | No heap alloc in sigma; BP verifier has ❌ PERIPH-M1 |
| Reject-valid / accept-invalid | DUP kuprum#37/#39 | Amount=0 prover-side DoS (completeness class); no accept-invalid |

---

## Phase 2 — Apply 6 Cross-Language Meta-Patterns

### 2.1 Verifier-derived remainder commitment pattern

**Principle**: for any primitive proving `b ≥ amount` where `b` is encrypted/committed and `amount` is revealed, the verifier MUST derive the remainder commitment itself rather than accepting a prover-supplied remainder.

**Anti-pattern**: accepting `pc_rem` from the transaction payload and running a range-proof on it directly. Prover can claim a smaller `amount` than `PC_b - pc_rem` implies.

**Correct pattern**: verifier computes `pc_rem = PC_b - amount*G` from transaction-revealed `amount` and SLE-read `PC_b`. Range-proof binds verifier-derived pc_rem.

**Example** (mpt-crypto): `mpt_compute_convert_back_remainder` at `mpt_utility.cpp:739-788` computes `pc_rem` deterministically before passing to BP verifier.

**Cross-language**:
- **EVM** (Aztec, Railway, zkBob): confidential-transfer contracts that verify range proofs over user-claimed amounts MUST compute remainder on-chain.
- **Solana light-protocol**: compressed-state verifiers derive remainder commitments during verification.
- **Circom / Noir / Aleo**: range-proof circuits should have remainder as public INPUT (computed by outer verifier).

### 2.2 Two-primitive amount-binding

**Principle**: amount binding does NOT need to be in the sigma's FS transcript if it is bound via the downstream primitive's transcript through a verifier-computed variable.

**Anti-pattern FP**: falsely reporting "sigma transcript missing amount" as a finding when BP (or other downstream primitive) binds amount via shared variables.

**Correct check**: trace the amount through EVERY primitive in the bundle. If ANY primitive's transcript binds a variable that uniquely determines amount (e.g., `pc_rem` in ConvertBack), amount-binding is sound.

**Prevents false positives**: Domain 15 Economic Security agent EC-2 — "amount missing from sigma context_id" is NOT a bug because BP's pc_rem transcript binds amount indirectly.

### 2.3 Orphan-public-API reachability check

See Phase 0. This is a first-filter optimization.

### 2.4 Completeness-vs-soundness tradeoff

**Principle**: libraries that prefer rejecting valid inputs (prover-DoS class) over accepting invalid inputs (soundness-break class) are defensively correct but produce a characteristic bug spectrum — every bug migrates to the completeness dimension.

**Evidence** (mpt-crypto):
- F-05 discipline: universal `seckey_verify` at every scalar ingress blocks scalar-overflow-malleability.
- Cost: edge-case witnesses (amount=0, balance=0, nonce-reduced-to-0) cause prover rejection.
- kuprum mpt-crypto#37, #38, #39, #41, #51 — ALL completeness class.
- **Zero kuprum entries** in the soundness class.

**Audit implication**:
- When a library's F-05-style discipline is confirmed → prioritize soundness-direction probes.
- Most contests rate soundness bugs higher (theft vs DoS). A reject-valid bug is typically Low; an accept-invalid bug is typically Critical.

**Cross-language**:
- **EVM Solidity**: libraries that revert on invalid inputs (OpenZeppelin's SafeMath) exhibit the same spectrum.
- **Solana**: Anchor programs with thorough account-validation produce the same spectrum.
- **Move**: aborts-on-precondition-fail produces the same spectrum.
- **Rust/Go backend code with `Result<T, E>`**: functions that return `Err` on edge cases produce the same spectrum.

### 2.5 Prover-verifier seckey_verify symmetry seam

**Principle**: prover/verifier asymmetry in ingress validation creates the completeness-class bug spectrum. Every scalar read by VERIFIER from proof bytes is seckey_verified; every scalar built by PROVER from sums/products of blindings and FS challenges is serialized directly without validation.

**Bug pattern**:
- `tau_x = tau2*x^2 + tau1*x + sum_j z^(j+2)*r_j` (BP prover — not seckey_verified before serialization)
- `mu = alpha + rho*x` (BP prover — same)
- `z_m = beta + e*m` (compact sigma prover — same)

**Consequence**: ~1/n ≈ 2^{-256} probability per scalar that prover produces a zero that verifier rejects → completeness DoS. kuprum#37/#38/#39/#41 are instances.

**Audit checklist**: diff prover-side scalar assembly vs verifier-side ingress validation side-by-side for every bundle.

**Cross-language**: any sigma-protocol prover with `response = blinding + challenge * witness` can coincidentally yield response==0.

### 2.6 Paired-transactor binding comparison

**Principle**: for tx types that come in pairs (Send/ConvertBack, Convert/Clawback, Deposit/Withdraw, Stake/Unstake), systematically compare context-hash construction side-by-side to catch asymmetric binding decisions.

**Method**: tabulate the serializer layout of each paired transactor:

| Tx type | Position-1 | Position-2 | Position-3 | Position-4 | Position-5 | Position-6 |
|---|---|---|---|---|---|---|
| Send | txType=88 | sender | issuance | seq | **dest** | version |
| ConvertBack | txType=87 | acct | issuance | seq | **acct-placeholder** | version |
| Clawback | txType | issuer | issuance | seq | **holder** | **0-hardcoded** (kuprum#6875) |
| Convert | txType | acct | issuance | seq | **acct-placeholder** | 0 |

**Red flag**: any future path that puts `acct` as placeholder but also introduces a NEW second-party field that could replay.

**Cross-language**:
- **EVM confidential ERC-20 tokens**: pair of `withdraw` and `deposit` functions should have analogous context separation.
- **Solana**: `initialize` + `close` instruction pairs should not share a context hash.
- **Move**: `lock` + `unlock` module functions should have distinct context seeds.

### 2.7 Adversarial forgery construction (soundness, not just composition)

**Principle**: Phases 0–2.6 audit how primitives COMPOSE and whether they are REACHABLE. They do not, by themselves, attempt to BREAK soundness. A composition can be well-formed and still unsound if a malicious prover can produce a transcript the verifier accepts while the claimed relation is false. **Composition-correct ≠ forgery-resistant.**

**Origin (gap)**: Sherlock 1260 XRPL post-mortem. M-16's Domain-15 run concluded the mpt-crypto bundle was "sound modulo known completeness issues" and submitted 0 Medium+. The contest's single largest confidential-MPT finding was **F30** (Critical, 15 finders): *a malicious confidential MPT holder drains shared confidential backing from other holders via forged proofs.* The composition matrix had no explicit "construct the forgery" step, so the soundness break was never attempted.

**Mandatory method** — for each verifier, ASSUME a malicious prover and try to build an accepting-but-false transcript:

1. **Conservation relation**: state the value-conservation / ownership invariant the proof enforces (e.g. "outputs sum to inputs", "spender owns the spent commitment", "no new supply minted") as an equation over the public commitments.
2. **Shared / pooled backing** (the **F30** shape): if multiple users' confidential balances share a common backing pool, issuance aggregate, or outstanding-amount accumulator, check whether one user's proof can satisfy the verifier while moving value belonging to the SHARED pool or to ANOTHER holder. Forged-proof-drains-shared-backing is the highest-severity ZK class — test it explicitly, do not infer soundness from composition correctness.
3. **Witness independence**: can the prover choose a witness (blinding, challenge precursor, point) that makes a binding check pass vacuously? (point-at-infinity, zero response, identity commitment, equal-and-opposite blindings).
4. **Verifier-derived value reuse**: where the verifier DERIVES a value (`pc_rem = PC - amount*G`) and feeds it downstream, can the prover pick inputs so the derived value collides with an unrelated valid commitment?
5. **Construct the PoC**: if any of 2–4 yields a candidate, build the forged proof with the real library (`mpt_utility`-equivalent) and show the verifier returns success on a relation-violating input. A forgery the real verifier accepts is `[POC-PASS]` ground truth.

**Output**: for every verifier, a row — `relation | forgery attempt | verifier verdict | conservation broken? (Y/N)`. A "sound" verdict REQUIRES the forgery attempt to be tried and to fail, not merely "composition looks correct."

---

## Phase 3 — 8-Question Cell Probe Template

For every `(bundle × primitive × invariant)` cell the auditor reaches, answer:

### Q1 — Transcript completeness

- Every public statement variable in Fiat-Shamir challenge hash?
- Every public statement variable in deterministic-nonce statement_hash?
- Prover and verifier hash identical input sequences?
- Any conditional-hash-input patterns (`if (context_id) hash(ctx)`)? If yes, document caller discipline.

### Q2 — Domain separation

- All FS tags unique across library?
- Grep ALL inline string literals adjacent to `EVP_DigestUpdate` / `sha256` / `blake2b` — not just documented tags.
- Pairwise tag divergence at or before byte 16 (to ensure SHA-256 content-binding splits immediately)?

### Q3 — Primitive composition

- When bundle X uses A+B+C, shared variables passed consistently to all?
- Does A's verification assume something B/C doesn't enforce?
- Verifier-derived vs prover-supplied public commitments (apply D-37)?

### Q4 — Cross-recipient / cross-user witnesses

- Multi-party witness: shared randomness, multi-auditor, multi-signer?
- Content-binding sufficient for known `n`?
- Attacker-controlled `n`?

### Q5 — Boundary values

- Zero witness (sk=0, amount=0, balance=0, r=0 mod n)
- Maxed witness (amount=2^64-1, etc.)
- Identity point (pc_rem=O, commitment=O)
- First-depositor / zero-supply
- Round-to-zero in division
- Overflow at MAX

### Q6 — Binding across operations

- context_id / context_hash binds tx-type, account, sequence, balance-version?
- Replay across txs blocked (via seq consumption)?
- Replay across chains blocked (via chain-id or network-id binding)?
- Replay after key rotation blocked (via pubkey binding)?

### Q7 — Error-path resource leaks

- All `malloc` paired with `free` on EVERY `goto fail` / `return -1` path?
- Unified `cleanup:` label used (safer) or mixed per-path frees (error-prone)?
- Attacker-controlled heap sizes (e.g., `n` parameter)?
- `OPENSSL_cleanse` on secret scalars in stack?
- EVP_MAC / EVP_MD return values checked?

### Q8 — Reject-valid / accept-invalid asymmetry

- Does verifier accept any clearly-invalid proof?
- Does prover reject any clearly-valid witness?
- Apply completeness-vs-soundness meta-pattern (2.4) — categorize every flagged bug.
- Soundness-class bugs typically Critical; completeness-class typically Low.

---

## Phase 4 — Dedup & Severity Calibration

### Dedup layers (per M-10 methodology)

1. **Known-issue layer**: grep contest-provided known-issue index (kuprum-style) for related vulnerability classes.
2. **Prior-audit layer**: check any prior independent audits (Halborn, FYEO, Trail of Bits) of the same library.
3. **Framework-protected layer**: check if finding is blocked by an existing framework-fact (F-03 identity handling, F-05 ingress validation, etc.) or refuted class (R-02 ElGamal identity, R-09 BP H_vec[0] collision, etc.).

### Severity calibration

Apply the completeness-vs-soundness filter:
- **Accept-invalid (soundness)**: Critical/High if it enables theft, arbitrary state modification, or privilege escalation.
- **Reject-valid (completeness)**: Low/Medium DoS unless the rejection is easy-to-trigger with zero attacker cost.
- **Reachability**: confirm T-07 PoC feasibility via rippled-tx or equivalent public-API path. If unreachable → Informational.

---

## Anti-patterns (when NOT to apply M-16)

1. **Single-primitive protocols** — if the protocol uses only ONE ZK primitive (e.g., Groth16 only, no outer wrapper), M-16 provides less value. Use M-09 (SYNC_GAP) or per-primitive checklist instead.
2. **Non-ZK cryptography** — protocols that only use hash-based commitments (Merkle trees), signatures, or symmetric crypto don't benefit from the composition-matrix structure.
3. **Greenfield ZK circuits with no deployed consumer** — for early-stage Circom/Noir circuits not yet integrated into a production verifier, M-16's reachability phase fails (nothing is "reachable"). Use standard ZK-circuit audit instead.

---

## Validated findings

| Audit | Date | Outcome | Cells populated | New meta-patterns |
|---|---|---|---|---|
| XRPL April 2026 Domain 15 (mpt-crypto) | 2026-04-24 | 0 Medium+ submissions; 1 Low candidate (PERIPH-M1 HOLD); all 8 hypotheses in scope-hint refuted or dup | ~50 cells across 4 reachable + 3 unreachable bundles | 6 meta-patterns (this template) |

---

## Cross-language applicability table

| Meta-pattern | EVM | Solana | Aptos / Sui | Aleo / Noir | Circom |
|---|---|---|---|---|---|
| Verifier-derived remainder (D-37) | Confidential tokens (Aztec, zkBob) | light-protocol compressed state | Native ZK (future) | Record programs | Range-proof circuits |
| Two-primitive amount-binding (D-38) | Multi-primitive bundles (sigma + BP in L2) | Elusiv bundles | Future Sui Move ZK | Combined proofs | Circom's multi-template composition |
| Orphan-public-API (D-35) | OZ unused functions; verifier precompiles | Exported entrypoints not in IDL | Public module functions unused | Deployed records with no caller | Template circuits not in `main.circom` |
| Completeness-vs-soundness (T-11) | Solidity reverts on edge; SafeMath spectrum | Anchor account-validation reject-class | Move abort-on-precondition | Leo semantic-type errors | Circom constraint-satisfaction edge cases |
| Prover-verifier seckey_verify seam (F-39) | Circom witness gen vs verifier | Solana prover-side scalar checks | Native prover APIs | Aleo snark prover | Circom witness assembly |
| Paired-transactor comparison (F-42) | `withdraw`/`deposit` pairs | `initialize`/`close` pairs | `lock`/`unlock` modules | Open/close record templates | Paired proof circuits |

---

## Contribution guide

When a new audit validates a new meta-pattern or finds a composition-matrix cell that reveals a bug class, append to the "Validated findings" table and extend the cross-language applicability table.
