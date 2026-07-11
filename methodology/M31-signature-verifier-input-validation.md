---
id: M-31
name: signature-verifier-input-validation
trigger_type: code
trigger_grep: "bls12|bn254|bn128|alt_bn128|pairing|ec_?pairing|ecpairing|blst|milagro|subgroup|clear_cofactor|point_at_infinity|g1affine|g2affine|is_on_curve|aggregate.?signature|bls_verify|verify_aggregate|ecrecover"
trigger_languages: [all]
applies_to_protocol_types: [any]
recon_flags: [PAIRING_VERIFIER, BLS_AGGREGATE_SIG, ZK_PRECOMPILE, ORACLE_FEED_VERIFIER]
---

# M-31 — On-Chain Signature-Verifier Soundness: Zero / Identity / Subgroup Input Validation

> **Purpose**: systematic methodology for auditing whether an on-chain **verifier** of a cryptographic signature or proof (pairing-based BLS, BN254 / BLS12-381 precompile calls, `ecrecover`, ed25519, ZK verifiers) actually **validates its inputs before trusting the result**. The failure class: a verifier that skips non-zero / non-identity / subgroup / sentinel-return checks accepts a *mathematically valid but semantically meaningless* check as proof of a valid signature. This is the verifier-INTEGRITY lens, distinct from M-30 (signature-BINDING / replay) and M-16 (ZK-proof COMPOSITION).
>
> **Origin**: Bonzo Lend incident, Hedera mainnet (2026, ~$10M). Attacker submitted a price update to the Supra oracle's contract carrying a **zeroed BLS signature `[0,0]`** instead of a valid committee signature. BLS verification is a pairing equation `e(signature, G2_generator) == e(H(message), committee_pubkey)`; with **both signature and pubkey the point-at-infinity (identity)**, both sides collapse to the identity in the target group — `e(0, G2) == e(H(m), 0)` → `1 == 1` → **true**. Hedera's pairing precompile (system contract `0.0.8`) correctly answered "the equation holds"; the verifier wrongly read that as "valid committee signature." A ~$2 collateral deposit, priced ~12 orders of magnitude too high, borrowed ~$9.05M. Root cause: **the verifier never checked that the signature and key inputs were non-zero and in-subgroup first.** Source: https://bonzo.finance/blog/bonzo-lend-incident-report-oracle-provider-exploit
>
> **Cross-language**: EVM (`ecPairing` precompile `0x08` BN254; EIP-2537 BLS12-381 precompiles; `ecrecover` returning `address(0)` on failure), Solana (`alt_bn128_pairing` syscall; `bls12_381` / `blst` crates), Cosmos / Go (tendermint / consensus BLS aggregate sigs), Sui (`sui::bls12381`), Aptos (`aptos_std::crypto_algebra` + `bls12381`).

---

## Trigger

Invoke when recon detects ANY of:
- A **pairing / BLS verifier**: calls to a pairing precompile (`ecPairing` `0x08`, EIP-2537, `alt_bn128_pairing`), or a BLS library (`blst`, `milagro`, `bls12381`, `crypto_algebra`), or aggregate-signature verification.
- A **ZK / SNARK verifier** that feeds curve points to a pairing check (Groth16/Plonk verifiers built on the same precompiles).
- `ecrecover` / `ECDSA.recover` whose return value is used without an `address(0)` reject (the EVM instance of "verifier returns a valid-looking sentinel for invalid input").
- An **oracle / bridge / light-client** that CONSUMES a feed whose authenticity rests on such a verifier — the trust boundary this bug lives on.

`match_methodologies.sh` fires this template on the `trigger_grep` above; the methodology-adversary step DEMOTEs it if no curve/pairing/verify primitive is structurally present.

---

## The soundness table (core method)

For EVERY verifier, tabulate **what it checks on its inputs BEFORE the pairing/recover** vs **what it MUST check to be sound**. Read the verifier source, never the docs.

| Soundness check | Present before the pairing/recover? | Bypass if missing |
|---|---|---|
| **Non-zero / non-identity** on signature AND public key | | zero/identity inputs make `e(0,·)==e(·,0)` → `1==1` trivially true (← **Bonzo**) |
| **Subgroup membership** (point in the prime-order subgroup, not small-order/cofactor) | | small-order point forges a passing pairing; invalid-curve attack |
| **On-curve** check (point satisfies the curve equation) | | off-curve point corrupts the pairing result |
| **Sentinel-return handling** (`ecrecover` returns `address(0)` on malformed sig) | | recovered signer `== address(0)`; if an uninitialized signer/committee is also zero → "anyone" passes |
| **Semantic vs mathematical result** (equation-holds ≠ valid-committee-signature) | | verifier conflates "precompile returned true" with "authentic signer," accepting a meaningless-but-valid equation |
| **Committee / key provenance** (pubkey is the real committee key, not attacker- or zero-supplied) | | attacker supplies the key that makes their own signature verify |

**Rule**: any check the verifier's guarantee depends on but does NOT perform before trusting the result is a soundness seam. For each missing check, construct the concrete bypass with degenerate inputs (zero, identity, small-order, off-curve, `address(0)`).

---

## STEPs

1. **Locate** every verify call site (grep the pairing/BLS/`ecrecover` primitives) and read the exact bytes/points fed to the precompile or recover.
2. **Fill the soundness table** per verifier — check-by-check from source, in the order they run relative to the pairing/recover call.
3. **Zero/identity test** (the Bonzo shape): substitute the point-at-infinity for signature and/or pubkey. Does the pairing collapse to `1 == 1`? Is the zero input rejected *before* the pairing? `[BOUNDARY: sig=0, pubkey=0 → pairing==identity==true]`.
4. **Subgroup/small-order test**: is `is_in_subgroup` / `clear_cofactor` / cofactor-multiplication applied to every untrusted point before use? BN254 has trivial cofactor on G1 but not G2; BLS12-381 needs explicit subgroup checks on both.
5. **Sentinel test** (`ecrecover`): is the return compared against `address(0)` (or the expected signer set) before it is trusted? Cross-check whether any privileged/committee address could itself be zero/uninitialized.
6. **Consumer defense-in-depth** (the trust-boundary half): if a downstream protocol relies on this verifier for an oracle price / bridged message / attestation, does the CONSUMER independently bound the result (sanity min/max, per-update deviation cap, second source)? A verifier bug becomes a total loss ONLY when the consumer trusts it unconditionally. See attack-vector **#174** (Missing Oracle Price Bounds) and **#267** (verifier-side detect entry).
7. **PoC**: construct the degenerate-input submission (zeroed signature, small-order point, or `address(0)` recover) and assert the verifier returns true / the downstream action succeeds.

---

## Cross-language mapping

| Dimension | EVM | Solana | Sui / Aptos | Cosmos / Go |
|---|---|---|---|---|
| Pairing primitive | `ecPairing` `0x08` (BN254); EIP-2537 (BLS12-381) | `alt_bn128_pairing` syscall; `blst` | `sui::bls12381::bls12381_min_pk_verify`; `aptos_std::crypto_algebra` | `blst` / `gnark-crypto` in consensus |
| Zero/identity bypass | identity G1/G2 points → trivial pairing (**Bonzo** shape) | identity point in `alt_bn128` input | identity element of the algebra | zero aggregate sig / zero apk |
| Subgroup check | manual G2 subgroup check (precompile does NOT do it pre-EIP-2537 semantics) | caller must cofactor-clear | `crypto_algebra` requires explicit checks | `subgroupCheck` on deserialized points |
| Sentinel-return | `ecrecover` → `address(0)` on failure | — | — | recover error vs zero-value |

---

## Anti-patterns (FP gates)

- A verifier that calls a library which internally performs subgroup + non-identity checks (e.g. `blst`'s `*_in_g1/g2` validated deserialization, or EIP-2537 precompiles which subgroup-check by spec) is sound — don't flag the missing *explicit* check when the library guarantees it. Verify the library path actually validates, not just deserializes.
- `ecrecover` whose result is immediately compared to a known non-zero expected signer (`require(recovered == expectedSigner)`) is safe against the `address(0)` sentinel — the zero-return can't match a non-zero expected address.
- BN254 G1 has cofactor 1 — a missing G1 subgroup check on BN254 is NOT exploitable (only flag G2 / BLS12-381 / other-curve subgroup gaps).
- This is a VERIFIER-side template. If the audited protocol only *consumes* an external feed and does not implement the verifier, the finding is consumer-side (attack-vector #174 sanity bounds), not a M-31 verifier bug — scope it correctly and don't over-escalate a third party's verifier as the audited protocol's Critical.

## Related

- **M-30** (signature-binding / replay) — checks whether a *valid* signature is bound to its context; M-31 checks whether an *invalid/degenerate* input is rejected before verification. Co-fire on `ecrecover`.
- **M-16** (ZK-proof-bundle composition) — Phase 2.7 adversarial forgery construction overlaps when the ZK verifier is pairing-based; M-31 is the input-validation (zero/subgroup) sublens.
- Attack-vector **#174** (Missing Oracle Price Bounds) and **#267** (pairing/BLS verifier zero-input bypass) — the consumer-side and verifier-side detect entries this methodology pairs.

## Validated findings

- Bonzo Lend / Supra oracle (external incident, 2026, ~$10M): STEP 3 zero/identity test → zeroed BLS signature `[0,0]` + zero committee key → trivial pairing → verifier returns true → oracle price inflated ~1e12x → ~$9.05M borrowed against ~$2 collateral. Methodology added to close the class (verifier-side); consumer-side already covered by attack-vector #174 sanity bounds.
