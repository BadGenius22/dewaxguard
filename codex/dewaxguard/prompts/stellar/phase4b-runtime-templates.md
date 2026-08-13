# Phase 4b: Runtime/VM-Specific Attacks — Stellar/Soroban

> **Runtime**: Soroban VM (WebAssembly-based, Stellar network)
> **Agent**: depth-runtime
> **Focus**: Soroban storage model, state archival, custom account auth, cross-contract calls, TTL economics
>
> **🚨 REQUIRED READING**: Before starting, the agent must read `~/.agents/skills/dewaxguard/platform-quirks/stellar.md`. The entry #1 (State Archival ≠ Deletion) corrects a misconception that has historically produced invalid findings. Every runtime analysis must internalize this before tracing TTL-related attack paths.

---

## CRITICAL PLATFORM BEHAVIOR RECAP

**State archival vs deletion** (applies to every check below):

| Tier | On TTL Expiry | Subsequent Access |
|------|--------------|-------------------|
| **Instance** | Archived — value preserved | Transaction fails at apply unless `RestoreFootprintOp` included. Restoration returns original value. |
| **Persistent** | Archived — value preserved | Transaction fails at apply unless `RestoreFootprintOp` included. Restoration returns original value. |
| **Temporary** | **Deleted** — actual disappearance | `storage.temporary().get()` returns `None`. `#[default]` fallback applies. |

The `#[default(x)]` fallback only runs for keys that were **never written**. It does NOT run for archived keys.

**This means**: every "expires to default enabling X" attack on persistent/instance storage is **invalid** on Stellar. The entry is archived with its value intact; restoration preserves the value; the attack fails.

---

## SYSTEMATIC CHECKS

### A) Storage Tier Classification and Coupling

```bash
grep -rn "#\[instance(\|#\[persistent(\|#\[temporary(" contracts/ --include="*.rs" | grep -v target | grep -v tests/
```

For each storage entry, document: tier, default value, coupled entries.

**Valid coupling concerns (only temporary storage expiry can desync)**:
- Persistent/instance state gated by a **temporary** flag → temporary deletes → state stranded or unguarded
- Persistent pending operation + temporary lock → lock deletes → operation proceeds without lock

**Invalid coupling claims (do NOT report)**:
- ❌ Instance counter + persistent entries "desync" because persistent expires — both archive with preserved values
- ❌ Persistent nonce expires to 0 enabling replay — nonce is archived, value preserved
- ❌ Persistent allowlist entry expires to false — entry archived, value preserved
- ❌ Persistent sentinel (e.g., `RECEIVED_MESSAGE_HASH`) expires to `None` — sentinel archived, value preserved

### B) Custom Account Interface (`__check_auth`)

```bash
grep -rn "__check_auth\|CustomAccountInterface" contracts/ --include="*.rs" | grep -v target | grep -v tests/
```

For each `__check_auth` implementation:
1. **Auth context validation**: Does it correctly handle `Context::Contract` vs `Context::CreateContractHostFn`? Does it enforce the expected number of contexts (1 for single call, 3 for upgrade)?
2. **Replay protection**:
   - Is a hash/nonce consumed after verification?
   - **Where is the replay protection stored?** If persistent storage without TTL extension, the entry will be archived. Note: archival preserves the value, so the replay check still works **after restoration**. However, if the attacker can find a way to submit the replay transaction without referencing the archived entry in their footprint, the check is bypassed. Analyze whether this is possible.
   - Is the stored hash bound to the network (includes `env.ledger().network_id()` or similar)? If not, cross-network replay is possible.
3. **Expiration bounds**: Is there an **upper bound** on the signed payload's expiration timestamp? If the code accepts `u64::MAX`, signers can accidentally create long-lived signatures.
4. **Panic propagation**: Panics inside `__check_auth` deny the operation (equivalent to returning `Err`). This is acceptable and often intentional — do NOT report `.unwrap()` in `__check_auth` as a DoS finding.
5. **Signature verification**: secp256k1 s-value normalization (EIP-2), recovery ID range, sorted signer ordering, signature malleability.
6. **Admin bypass**: Some implementations (like DVN `set_admin`) deliberately skip admin signature verification for specific operations — this is by design per the invariant "DVN can set Admin through signed payload without Admin's permission." Do NOT report these as findings unless the protocol's README does not document the bypass.

### C) Cross-Contract Calls

```bash
grep -rn "env\.invoke_contract\|Client::new\|client\." contracts/ --include="*.rs" | grep -v target | grep -v tests/
```

1. **Target hardcoded vs dynamic**: Is the target address known at compile time or passed as parameter? Dynamic targets need validation.
2. **Return value validation**: Are return values bounded? A called contract returning `i128::MAX` can overflow accumulators in the caller.
3. **Authorization propagation**: Does the caller's `require_auth` carry into the called contract correctly?
4. **Reentrancy**: Soroban prohibits same-call reentrancy (cannot re-enter while executing). However, cross-contract state dependencies still matter — if contract A calls B, and B modifies shared state that A reads afterward, the assumption may be stale.
5. **DoS by revert**: A called contract (e.g., a fee library) that panics on specific inputs can grief the caller. Critical if the caller is unable to bypass the failed external call.

### D) Token Client (`TokenClient` / SAC Wrappers)

```bash
grep -rn "TokenClient\|token::Client\|StellarAssetClient" contracts/ --include="*.rs" | grep -v target | grep -v tests/
```

1. **Balance-based fee detection**: If the contract reads `token.balance(self)` to determine supplied fees, analyze whether donations, residual balances, or concurrent transfers can manipulate the detected amount.
2. **Transfer vs transfer_from**: Soroban tokens require `require_auth` from the `from` address. Verify which addresses authorize which transfers.
3. **Recover function (if present)**: A `recover_token` admin function can drain the contract. Classify as trusted-actor risk, not a vulnerability unless the owner is not clearly privileged.
4. **Native vs SAC wrapped vs custom**: Native XLM behaves differently from SAC-wrapped classic assets and from custom Soroban tokens. Decimals, authorization flags, and clawback capabilities vary.
5. **Refund flow**: After a transfer, does the contract refund excess correctly? Is the refund target validated (not zero, not uninitialized account)?

### E) TTL Configuration Safety

```bash
grep -rn "set_ttl_configs\|freeze_ttl_configs\|extend_ttl\|TtlConfig" contracts/ --include="*.rs" | grep -v target | grep -v tests/
```

1. **`set_ttl_configs(None)` reachability**: If callable without `freeze_ttl_configs()` already applied, the admin can disable auto-extension. Impact: users must manually restore archived entries (restoration cost DoS), NOT data loss.
2. **Minimum TTL enforcement**: Is there a floor on `extend_to`? If not, admin can set near-zero TTL, forcing constant restoration overhead.
3. **`freeze_ttl_configs()` timing**: Called in constructor? Post-init admin call? If admin-callable, note who holds the freeze capability.
4. **Auto-extension coverage**: Which storage entries auto-extend on access vs require manual extension? Write-once-never-read entries will certainly be archived and will cost users restoration fees — not a "vulnerability" per se, but a UX/economic concern.

### F) Storage Read Limit (200 per Transaction)

Soroban enforces a hard limit of 200 storage reads per transaction.

1. **Unbounded iteration**: Any loop that reads storage entries one-by-one must have a bound. If the bound can exceed 200, the function is DoS-able by growth.
2. **Bounded data structures**: Check constants like `PENDING_INBOUND_NONCE_MAX_LEN`, `MAX_DVNS`, etc. Verify they're set below 200 for operations that read them.
3. **Cross-contract calls**: Each CPI-equivalent can trigger additional reads in the callee. Sum must not exceed 200 for any tx.

### G) Upgrade Safety

```bash
grep -rn "update_current_contract_wasm\|upgrade\|migrate" contracts/ --include="*.rs" | grep -v target | grep -v tests/
```

1. **Auth model**: Who can trigger the upgrade? Owner, multisig, designated upgrader?
2. **Migration logic**: Does the upgrade handle storage schema changes? Missing migration = stale data interpreted under new schema.
3. **no_migration pattern**: Some contracts explicitly declare `no_migration`. Verify this is safe (schema doesn't change).
4. **Upgrader address validation**: If an upgrader contract is used, validate its address is not zero, not self, not arbitrary.

### H) Ledger Time / Sequence Dependencies

1. **Ledger timestamp drift**: `env.ledger().timestamp()` can vary slightly between ledgers.
2. **Sequence-based vs time-based checks**: Sequence is more predictable; timestamp is subject to validator drift.
3. **Expiration semantics**: `expiration <= timestamp` vs `expiration < timestamp` — off-by-one at the exact boundary.

### I) Pull-Mode Delivery (LayerZero-Style)

If the contract uses pull-mode delivery (recipient calls `clear` / `receive` instead of the endpoint pushing):

1. **Idempotency**: If a message is cleared once, can the recipient call `clear` again? Should it be blocked?
2. **Hash verification**: Does the recipient verify the payload hash matches the stored hash for the nonce?
3. **Nonce ordering**: Can messages be cleared out of order? Can a message be skipped entirely (permanently lost)?
4. **State machine**: Verified → Cleared → Received. Each transition should be one-way.

---

## DEEP ANALYSIS QUESTIONS

1. **For each coupled state pair**: Is any side in **temporary** storage? If yes, trace what happens when the temporary side deletes. If no, do NOT trace TTL-based desync.
2. **For each `__check_auth` implementation**: Walk through all 6 checks in section B. Pay special attention to replay protection storage tier.
3. **For each cross-contract call**: Can the callee manipulate the caller's accounting by returning unbounded or negative values?
4. **For each `TokenClient` usage**: Can donation, residual balance, or authorization manipulation create false readings of supplied amounts?
5. **For any unbounded iteration**: Compute worst-case storage reads. Compare to 200. Reject if within bounds.
6. **For any TTL-related finding**: Double-check against the "Invalid Finding Patterns" in `platform-quirks/stellar.md`. If it matches any invalid pattern, withdraw before submission.

---

## Mandatory Pre-Submission Gate

Before writing any finding to the inventory, answer:

1. Does this finding assume "persistent/instance storage expires to default"? → If yes, **invalid**, withdraw.
2. Does the PoC use `remove_*()` or `set_sequence_number(past live_until)` for persistent storage? → The PoC does not match production; withdraw or reframe.
3. Is the finding framed as "restoration cost / liveness" or "temporary storage expiry"? → These are the valid TTL framings.
4. For `__check_auth` findings: does the stored replay protection use persistent storage? If yes, remember: archived ≠ deleted. The check still works after restoration. The only valid attack is if the replay transaction can avoid referencing the archived entry in its footprint.
