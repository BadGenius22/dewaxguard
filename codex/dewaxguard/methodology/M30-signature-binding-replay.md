---
id: M-30
name: signature-binding-replay
trigger_type: code
trigger_grep: "ecrecover|ecdsa\.recover|signaturechecker|isvalidsignature|eip-?712|domainseparator|\bpermit\b|permit2|eip-?3009|eip-?2612|useroperation|ed25519|secp256k1|batchsigner|multisign|checksign|signingprefix|signdoc"
trigger_languages: [all]
applies_to_protocol_types: [any]
recon_flags: [SIGNATURE_BOUND_AUTH, CROSS_CHAIN_REPLAY_SMELL]
---

# M-30 — Signature-Binding / Replay / Domain-Separation Audit

> **Purpose**: systematic methodology for auditing whether every authorization artifact (signature, multisig blob, batch-signer, meta-tx permit, attestation, voucher) is **bound** to the exact context it authorizes — signer, signing-for account, envelope, chain, tx-type, nonce, expiry, value parameters — such that it cannot be **replayed** or **lifted** into a different context.
>
> **Origin**: Sherlock 1260 XRPL April 2026 **post-mortem** (2026-06-04). The pipeline read the Batch transactor (`deep_read_Batch.md`) but never ran a signature-replay lens, and missed **F4** (Critical — Batch tx replay: the `BatchSigner` blob is a bearer token, portable across outer envelopes; 13 finders) and **F3** (High — Batch multi-sign preimage fails to bind the signing-for account → cross-account signature replay; 9 finders). **Zero prior coverage of the class.** Found-GAP origin (cf. M-29 false-negative origin).
>
> **Cross-language**: EVM (EIP-712 / permit / EIP-2612, meta-tx relayers, Safe module sigs, EIP-1271), Solana (ed25519 sysvar instruction, off-chain message signing), XRPL (Batch `BatchSigner`, multisign `Signers`), Move/Aptos (BCS-signed payloads, multi-agent txs), Cosmos (`SignDoc` / ADR-036).

---

## Trigger

Invoke when recon detects ANY of:
- A custom multi-signer / batch / bundle envelope where one inner signature authorizes an action (`BatchSigner`, `Signers`, multicall-with-sig, Safe `execTransactionFromModule`).
- An off-chain-signed payload consumed on-chain: permit / EIP-712 / EIP-2612, meta-transaction, gasless relay, attestation, voucher, claim ticket.
- `ecrecover` / `ed25519_verify` / `secp256k1_verify` / `checkSign` / EIP-1271 `isValidSignature`.
- Any "signature presented by a party other than the signer" flow (relayer, bundler, sponsor, delegate submits on behalf).

`build_recon_maps.sh` section (m) emits `signature-binding-map.md` with machine-readable `SIGNATURE_BOUND_AUTH=true` + `CROSS_CHAIN_REPLAY_SMELL` diagnostic when the above patterns are present. EVM gets rich coverage (ecrecover/ECDSA/SignatureChecker/EIP-712/permit/Permit2/EIP-3009/ERC-4337); Solana/Stellar/Aptos/Sui/C++ get a generic verify-primitive grep (ed25519/secp256k1/BatchSigner/multisign) — cross-language, unlike the EVM-only M-29 detector.

---

## The binding table (core method)

For EVERY signature/auth artifact, tabulate **what the signed preimage actually commits to** vs **what it MUST commit to to be replay-safe**. Read the *serializer / typehash / SigningPrefix*, never the docs.

| Binding dimension | In the preimage? | Replay/forgery if missing |
|---|---|---|
| **Signer identity** (whose key) | | impersonation / wrong attribution |
| **Signing-FOR account** (on whose behalf) | | cross-account replay (← **F3**) |
| **Envelope / outer-tx identity** (which batch/bundle/multicall) | | portable bearer token across envelopes (← **F4**) |
| **Chain id / network** | | cross-chain replay |
| **Tx type / selector / action** | | action-substitution (sig for op A reused for op B) |
| **Nonce / sequence** | | straight replay |
| **Expiry / deadline** | | indefinite-validity replay |
| **Value params** (recipient, amount, token, target) | | front-run with attacker-chosen recipient/target (cf. M-29) |

**Rule**: any dimension the action depends on but the preimage does NOT commit to is a replay/forgery seam. For each missing dimension, construct the concrete replay PoC.

---

## STEPs

1. **Enumerate** every verify call site (grep the verify primitives above) and locate the exact bytes hashed/signed (preimage / `SigningPrefix` / typehash / `SignDoc`).
2. **Fill the binding table** per artifact — field-by-field from the serializer.
3. **For each unbound dimension**, ask the 4 replay questions: (a) can the same signature be presented in a different {envelope / account / chain / action}? (b) who can present it? (c) is presenting it permissionless? (d) what does the attacker gain?
4. **Bearer-token test** (the F4 shape): if the signature blob is detached and portable, can a third party lift it from a public / mempool / ledger source and attach it to *their own* envelope to force victim-funded side effects (reserves, tickets, object creation, frozen spendable balance)?
5. **Signing-for test** (the F3 shape): in multi-signer schemes, does the preimage bind the account being signed-for? If signer S can produce a blob that validates as "signed for account A" *and* "signed for account B", flag cross-account replay.
6. **PoC**: construct the replay/forgery with public transactions only; assert the second use succeeds (or the bearer token attaches to a foreign envelope).

---

## Cross-language mapping

| Dimension | EVM | Solana | XRPL | Move / Cosmos |
|---|---|---|---|---|
| Domain separation | EIP-712 `domainSeparator` (name/version/chainId/verifyingContract) | message prefix + program id | `SigningPrefix` / `HashPrefix` per tx-type | `SignDoc` chain-id/account-number (Cosmos); BCS domain tag (Move) |
| Bearer-token replay | detached `permit` lifted from mempool | off-chain sig reused across instructions | `BatchSigner` portable across Batch envelopes (**F4**) | multi-agent signature reused |
| Signing-for binding | EIP-1271 callee vs caller | signer seeds | inner `Account` vs `BatchSigner.Account` (**F3**) | Aptos multi-agent secondary signers |

---

## Anti-patterns (FP gates)

- Single-signer, single-tx, nonce-bound canonical signatures with full domain separation are replay-safe — don't flag.
- If the framework binds chain-id + sequence globally and the new feature inherits it unchanged, the *delta* is what matters — verify the new envelope doesn't introduce an **unbound second-party field** (the F3/F4 trap).
- A signature *intended* to be a reusable capability (documented by-design) is not a replay bug — but verify its scope can't be widened via action/amount/recipient substitution.

## Related

- **M-29** (Safe Module / delegate-executor) — EVM-specific instance of the "signed action with caller-supplied unbound parameter" seam; M-30 is the general cross-language signature-binding lens.
- **M-12** (granular-permission sandbox) — pairs with M-30 when delegated authority is signature-attested.

## Validated findings

- Sherlock 1260 XRPL (post-mortem gap, 0/2 found at audit time): STEP 4 bearer-token test → **F4** (Critical); STEP 5 signing-for test → **F3** (High). Methodology added to close the class.
