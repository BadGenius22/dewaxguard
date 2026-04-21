# M-03: Inverse-Trust-Direction Lens

**Origin**: XRPL Sherlock April 2026, Domain 4 (derived from T-08 trust decision + ESC-1/ESC-2 findings).

**One-line**: For every privileged-party operation, probe the opposite trust direction — can an untrusted party defeat or block it?

## Trigger

Apply whenever you encounter:
- An admin / issuer / owner / authority operation (burn, freeze, clawback, destroy, upgrade, pause).
- Any trust-model statement like "trusted actor X will not maliciously do Y" — this creates a blind spot about what the *untrusted* actor can do.
- Compliance-style primitives (KYC revocation, sanctioned-account seizure, regulatory burn).

## Process

1. **Enumerate** the privileged-party operations on the surface under review.
2. **For each operation P**: identify the trusted actor T, and the untrusted actors U (holders, users, callers).
3. **Ask**: "Can any U take a cheap, legitimate-looking action that defeats, blocks, or inverts P's intended effect?"
4. **Validate** with a concrete state sequence: U-action → T-action → P outcome is wrong / no-op / griefed.
5. **Cost-check**: the U-action must be cheap (≤ a few tx fees) and legitimate (public APIs only).

## Cross-language mapping

| Chain | Example privileged operation | Inverse-direction attack |
|-------|------------------------------|--------------------------|
| **EVM / Solidity** | Compliance token `forceTransfer(holder, target, amount)` | Holder pre-approves all balance to a non-KYC contract wrapper; forceTransfer acts on a now-zero balance |
| **Solana / Rust** | SPL Token2022 `freeze_account(authority, account)` | User transfers balance to a PDA-owned escrow; freeze_account freezes an empty ATA |
| **Move / Aptos** | `coin::burn_from<T>(admin, account, amount)` | Holder wraps `Coin<T>` in a Capability-gated vault; burn_from hits only a thin wrapper |
| **Soroban / Stellar** | `clawback_claimable_balance(issuer, balance_id)` | User locks assets with `auth_revoked` conditions; clawback now requires revoked auth |
| **C++ / XRPL** | `Clawback(issuer, MPT, holder)` | Holder escrows MPT with uncancellable crypto-condition; accountHolds returns 0 → clawback fails (ESC-1, validated) |

## Anti-patterns

- Don't apply when the privileged op is a pure convenience (no invariant depends on it succeeding). M-03 is valuable when the op is **load-bearing** for a compliance/safety/cleanup invariant.
- Don't double-count. If a finding already says "admin maliciously uses compliance feature", M-03 adds nothing. M-03 is specifically about INVERSE direction: an untrusted party defeats a trusted actor's legitimate use.
- Don't mistake "by design" for "not a bug". Many protocols describe their compliance layer as "trusted actor uses it correctly" — the M-03 question is "what if the trusted actor is honest but ineffective?"

## Validated findings

| ID | Protocol | Privileged op | U-action |
|----|----------|---------------|----------|
| ESC-1 | XRPL MPT | Issuer Clawback | Holder escrows entire balance with uncancellable condition |
| ESC-2 | XRPL MPT | Issuer MPTokenIssuanceDestroy | Holder creates dust escrow on 1 unit |
| ESC-3 | XRPL MPT Vault | Asset-issuer VaultClawback | Holder escrows vault shares with uncancellable condition |
| CONF-1 | XRPL Confidential MPT | Issuer MPTokenIssuanceSet (CLEAR CanConfidentialAmount) | Holder does Convert→ConvertBack round-trip leaving encrypted-zero residuals |

## Related methodology

- **M-08** generalizes M-03 into the holder-plants-trap template (every M-08 finding is also an M-03, but M-08 specifies the state-planting mechanic).
- **M-09** (SYNC_GAP detection) is orthogonal — probes aggregate/per-entity asymmetry, not trust direction.
- **M-07** post-finding sweep applies once M-03 yields one finding — fan out to related privileged ops.
