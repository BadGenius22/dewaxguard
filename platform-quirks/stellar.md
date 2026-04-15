# Stellar / Soroban Platform Quirks — Critical Reference

> **READ THIS BEFORE ANY STELLAR AUDIT.** This document corrects common misconceptions that lead to invalid findings. Every rule, scanner, depth template, and verification prompt in the Stellar skill tree references this.

---

## 🚨 #1 — State Archival ≠ Deletion (The One That Cost Us 1H + 2M)

### What Auditors Often Assume (WRONG)

> "When a persistent storage entry's TTL expires, subsequent reads return the `#[default(x)]` value. Therefore, a nonce stored as `true` becomes `false` after 30 days, enabling replay attacks."

### What Actually Happens (CORRECT)

Stellar's persistent and instance storage use **state archival**, not deletion:

1. **TTL expiry archives the entry** with its original value preserved. The entry is **not deleted**.
2. **Transactions that reference an archived entry fail at the apply stage**, before the contract code runs. The `storage.get()` call inside the contract never executes.
3. **To access an archived entry, the transaction must include a `RestoreFootprintOp`.** Restoration brings back the **original value**, not the default.
4. **The `#[default(x)]` fallback only runs for keys that were genuinely never written**, not for archived keys.

### Tier-by-Tier Behavior

| Tier | On TTL Expiry | Subsequent Access |
|------|--------------|-------------------|
| **Instance** | Archived (value preserved) | Transaction fails at apply unless `RestoreFootprintOp` included. Restoration returns original value. |
| **Persistent** | Archived (value preserved) | Transaction fails at apply unless `RestoreFootprintOp` included. Restoration returns original value. |
| **Temporary** | **Deleted** (the only tier that actually disappears) | `storage.temporary().get()` returns `None`. `#[default]` fallback applies. |

### Evidence

- **Stellar CAP-46-12 (State Archival)**: Specifies archive-restore semantics for persistent entries.
- **Project test code**: LayerZero's own `macro-integration-tests/tests/runtime/storage/ttl_extension.rs` only advances the ledger sequence to `live_until - threshold` for persistent storage (to test auto-extension). It **never** advances past `live_until` for persistent storage. The only tests that advance past `live_until` are for **temporary** storage (`two_step_transfer.rs`). This pattern — test only temporary past live_until — encodes developers' knowledge that persistent storage does not delete.
- **Test environment pitfall**: `env.storage().persistent().remove()` in tests produces `None`/default on read — but this does **not** match production. On mainnet, an archived entry preserves its value and blocks the transaction until restoration.

### Invalid Finding Patterns (DO NOT REPORT)

These patterns assume persistent/instance storage deletes on expiry. They are **technically wrong** and will be rejected by any competent judge:

1. ❌ "Persistent nonce expires to 0 → replay attack"
2. ❌ "Persistent admin address expires to zero address → ownership lost"
3. ❌ "Persistent allowlist entry expires to false → ACL bypass"
4. ❌ "Persistent sentinel expires to None → invariant violated"
5. ❌ "Persistent config entry expires to default → DoS"
6. ❌ "Instance counter + persistent entries desync because persistent entries expire"
7. ❌ "Write-once-never-read persistent entry causes data loss after 30 days"
8. ❌ "Auto-TTL extension failure causes persistent data loss"

Every one of these is based on the "persistent → default on expiry" misconception. **None of them can occur on mainnet.**

### Valid Framings (REPORT THESE INSTEAD)

The real concerns with archival are **restoration cost** and **liveness**, not data loss:

1. ✅ "Write-once-never-read persistent entry forces users to pay restoration fees to access it after 30 days" — **restoration cost DoS**
2. ✅ "`set_ttl_configs(None)` disables auto-extension, forcing all users into manual restoration" — **admin-forced cost burden**
3. ✅ "Minimum TTL not enforced — admin can set TTL to 1 ledger, causing constant restoration overhead" — **admin TTL sabotage**
4. ✅ "Temporary storage holding security-critical state" — **genuine data loss** (temporary is the only tier that deletes)
5. ✅ "Temporary entry coupled with persistent/instance state — temporary expires, persistent is orphaned" — **cross-tier desync, only valid with temporary**

### PoC Requirements

A PoC that simulates archival via `remove_*()` or `set_sequence_number(live_until + 1)` on persistent storage is **testing a scenario that cannot occur on mainnet**. Such PoCs do not prove the vulnerability — they prove a test-environment behavior that doesn't match production.

**Valid PoCs**:
- PoCs for temporary storage expiry (the test env correctly simulates this)
- PoCs for restoration cost impact (requires measuring the cost on Stellar testnet/mainnet)
- PoCs for TTL config sabotage (set_ttl_configs(None) is callable; impact is cost, not data loss)

**Invalid PoCs**:
- PoCs that remove persistent entries to "simulate expiry" — remove ≠ archive
- PoCs that advance the ledger past `live_until` for persistent/instance storage — the test env does not correctly simulate archival for these tiers

---

## #2 — No Reentrancy (but Cross-Contract State Still Matters)

Soroban's VM prohibits reentrancy: a contract cannot be re-entered while it is already executing. This is strict — no same-call reentrancy is possible.

**However**, this does NOT mean cross-contract state issues disappear:

- Contract A calls Contract B, which reads or writes shared state
- Contract A's assumptions about state may be invalidated by B's mutations
- Cross-contract auth flow (via `require_auth` + `__check_auth`) has its own ordering concerns

**Do not dismiss state consistency bugs** because "reentrancy is impossible on Soroban." Dismiss only **direct reentrancy** patterns.

---

## #3 — Storage Read Limit (200 per Transaction)

Every Stellar transaction has a hard limit of **200 storage reads** per transaction. This affects:

- Iteration over collections stored in persistent storage
- Verification flows that read many DVN confirmations
- Any function that scales with the number of users/entries

Findings involving unbounded iteration should compute worst-case read counts and compare to 200. Bounded data structures (like `PENDING_INBOUND_NONCE_MAX_LEN = 256`) need to be checked against this limit.

---

## #4 — Custom Account Interface (`__check_auth`)

Contracts can implement `__check_auth` to act as custom accounts (smart wallets, multisig). When such a contract is the target of `require_auth()`, the runtime calls `__check_auth` instead of verifying a traditional signature.

**Critical properties**:

1. **`__check_auth` runs inside the auth framework**, not as a normal contract function
2. **Panics in `__check_auth` deny the operation** — so using `unwrap()` / `expect()` on safe operations is acceptable
3. **Replay protection is the implementer's responsibility** — the runtime does not track used signatures
4. **The `signature_payload: Hash<32>` parameter IS network-bound** (includes network passphrase) — but only if the implementation uses it for signature verification. Custom hashes (like `hash_call_data`) computed separately are NOT network-bound unless explicitly constructed to include the network ID.

---

## #5 — Bytes32 Address Conversion

Stellar uses variable-length addresses (Account ID or Contract ID). LayerZero and similar cross-chain protocols use fixed `bytes32`. Conversion requires care:

- `Address::from_payload(env, AddressPayload::ContractIdHash(bytes))` — contract address from bytes
- `Address::from_payload(env, AddressPayload::AccountIdPublicKeyEd25519(bytes))` — account address from bytes
- **These are different!** Converting a 32-byte payload to a `ContractIdHash` when it actually represents an account produces an address that does not exist and cannot be delivered to.

Findings about bytes32 conversion should check: does the receiving side reconstruct the address using the correct payload type? If always `ContractIdHash`, then messages to account-type receivers are silently misrouted.

---

## #6 — `#[only_auth]` and Auth Context

The `#[only_auth]` macro injects `env.current_contract_address().require_auth()` at the start of the function. For contracts with `#[ownable]`, this resolves to the owner; for contracts with `#[multisig]`, it resolves to the contract itself (self-owning via `__check_auth`).

When testing auth bypass, remember:
- `mock_all_auths()` bypasses `__check_auth` entirely — cannot be used to prove auth bypass
- `try_invoke_contract_check_auth()` tests `__check_auth` directly but does not execute the dispatched calls
- There is **no** test API that combines both (real auth + real execution for custom account contracts)

This is a test infrastructure gap. PoCs for custom account auth must be split into two parts: (A) auth check via `try_invoke_contract_check_auth`, (B) impact demonstration via `mock_all_auths`.

---

## #7 — No Flash Loans (Currently)

Stellar does not have native flash loans. There is no atomic borrow-repay primitive that allows a user to temporarily hold large amounts of tokens within a single transaction. R15 (flash loan preconditions) from the generic rules does not apply.

---

## #8 — Overflow Checks Default

Rust's `overflow-checks = true` is commonly set in release profile. Integer overflow panics rather than wrapping. This means overflow findings should check:

1. Is `overflow-checks = true` in the release profile of `Cargo.toml`? → If yes, overflow is DoS (panic), not a wrap bug.
2. Are explicit `checked_add` / `saturating_add` patterns used? → Graceful handling.
3. Are `as u64` / `as u128` casts present? → These truncate silently (no overflow check applies to casts).

---

## Checklist for Every Stellar Audit

Before reporting any TTL/storage-related finding, confirm:

- [ ] The finding does NOT assume "persistent/instance expires to default" (wrong — they archive with preserved values)
- [ ] If the finding involves persistent/instance storage TTL, it is framed as **restoration cost / liveness**, not data loss
- [ ] If the finding involves temporary storage, the test env correctly simulates its deletion
- [ ] The PoC, if any, does not rely on `remove_*()` or `set_sequence_number(past live_until)` to simulate persistent expiry
- [ ] The finding has been checked against the "Invalid Finding Patterns" list in #1 above

---

## Source of Truth for Future Lessons

When future audits discover new platform quirks, **add them here**. This document is the accumulated pain of past misses. Every entry represents hours of wasted work that a 2-minute read could have prevented.

**History of lessons**:
- 2026-04 LayerZero audit: Misunderstood state archival as deletion. Wrote 3 findings (1H + 2M) based on "persistent → default on expiry." All invalid. Added #1 above.
