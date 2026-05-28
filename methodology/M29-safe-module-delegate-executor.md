# M-29: Safe Module / Delegate-Executor / Arbitrary-Path Authorization Audit

> **Origin**: SquidRouter hack (2026-05, ~$3.07M DAI extracted). Attacker called `executeSameChainActions()` on victim Safes via the `DelegateBundler` path, impersonating an authorized delegate. Module executed arbitrary Uniswap V3 swaps against attacker-deployed token "u" / pre-seeded UniV3 pools. The bug class: a privileged execution wrapper where the auth gate on the outer (bundler) path did not match the auth assumption of the inner (per-Safe) action. Permissionless attack — no keys compromised, no admin action required.
>
> **Trigger** (mechanical): emit `delegate-executor-map.md` if the recon grep finds any of these tokens in EVM source:
> - `execTransactionFromModule(` — Safe Module pattern (caller-supplied target + value + data + operation)
> - `delegatecall(` from a public/external function whose target is caller-supplied
> - `SafeProtocolManager.executePlugin` / `Safe.execTransactionFromModuleReturnData`
> - `IExecutor.execute(address target, bytes data, uint256 value)` (and lookalikes)
> - `function .*\(.*address.*target.*bytes.*data` where the function is `external` or `public`
> - Signature-verified "executor" pattern: `verifyDelegateSignature`, `isAuthorizedDelegate`, `processDelegatedOrder`, `executeFromExecutor`, `executeMetaTransaction`
> - 1inch / 0x / Squid / Li.Fi router-on-behalf-of patterns: `swapOnBehalf`, `executeRouter`, `executeBundle`, `multiCallWithSelectorAndContext`
>
> **Yield class**: top-tier. Squid-class bugs are direct theft, permissionless, single-tx, no admin compromise. Maps cleanly to the strict "Critical / direct theft / high likelihood" filter. Historical comparable findings: WintermuteV1 (2022), Multichain (2023), Squid (2026).

---

## The pattern

A contract that lets one party (the **executor** / **bundler** / **module**) perform privileged actions on behalf of another party (the **principal** / **Safe** / **benefactor**). The principal pre-grants execution authority either:

- **Module install**: the Safe (principal) calls `enableModule(addr)`, the module gets unilateral `execTransactionFromModule` privilege
- **Signature delegation**: the principal signs an off-chain order; on-chain, the executor submits the signature for verification
- **On-chain allowlist**: principal sets `authorizedExecutor[X] = true` once; X can act forever

Three checks must ALL pass for an exec call to be safe:

1. **Auth check**: does the executor (`msg.sender`) actually have the principal's authorization right now?
2. **Action binding**: is the specific action (target + calldata + value) bound to the principal's authorization, not just "any action by any executor"?
3. **Path validation**: if the action involves an external call to a DEX/protocol, is the target/path validated against an allowlist, OR is the slippage bounded by an independent oracle (so the path can be untrusted but the outcome can't)?

The Squid bug failed check #1 OR #2 (depending on the exact root cause variant). Even if #1 had been right, #3 was also broken — the swap router target and pool path were caller-supplied with `amountOutMinimum = 1`.

---

## Step 1 — Mechanical enumeration

For every contract in scope, list every `external` and `public` function whose execution can result in `address(safe).call(...)` or `delegatecall(...)` or `ISwapRouter(target).exactInputSingle(params)` where the target is not a hardcoded constant.

For each such function, write:

| Function | Auth gate(s) | Auth subject (principal) | Action params (caller-supplied) | External target |
|----------|--------------|--------------------------|---------------------------------|-----------------|
| `executeSameChainActions(...)` | `verifySig(sig, hash)` | Safe in the order data | actions[], path[], amountIn, amountOutMin | UniV3 router (caller-supplied?) |

**Rule**: If the auth subject is "the principal whose funds are at risk" but msg.sender is allowed to be anyone (because the auth check is signature-based, not msg.sender-based), this is a delegate-executor pattern. Audit the signature.

If the auth subject is `msg.sender` directly but the function makes external calls with caller-supplied targets, this is an arbitrary-CPI/path pattern. Audit the path validation.

---

## Step 2 — Auth-gate inversion test

For each delegate-executor function, ask: **can I construct a calldata that passes the auth gate while pointing to a different principal's funds?**

Concrete tests:

1. **Hash binding check**: does `hash` include the principal's address (Safe address / benefactor address)? Use Foundry to compute `verifyOrderHash(orderForSafeA)` vs `verifyOrderHash(orderForSafeB)`. If the hash is identical when only the Safe address differs (because the Safe is encoded outside the typehash), a signature on order A is replayable against Safe B.

2. **Nonce scope check**: is the nonce keyed `mapping(address principal => uint256 nonce)` or just `uint256 globalNonce`? Global nonces are replayable across principals.

3. **EIP-1271 callee check**: when `signatureType == EIP1271`, who's the contract called for `isValidSignature`? Is it the principal or an attacker-supplied address? An attacker who can specify the EIP-1271 signer can deploy a contract that returns the magic value for any hash.

4. **Outer-wrapper auth check**: does the BUNDLER (the outer function that the relayer calls) have its own auth gate? Often the inner verifyOrder is correct, but the bundler that loops over [order_a, order_b, ...] forgets to gate "who can call me at all". This is the Squid bug shape.

5. **Cross-tier replay**: if both EIP-712 and EIP-1271 paths exist, can a hash signed for one type be replayed via the other? Check that `signatureType` is part of the typehash.

For each test, write a Foundry PoC that constructs the attacker calldata and runs against a mainnet fork. The standard for CONFIRMED is `[FORK-PASS]` per `rules/fork-poc-execution.md`.

---

## Step 3 — Path-validation test

For each external-call site with caller-supplied target/calldata, ask: **can I direct the call to a contract I control?**

Concrete tests:

1. **Target allowlist**: is `target` checked against a hardcoded constant or a governance-controlled allowlist? If not, the target can be attacker-controlled.

2. **Selector allowlist**: is the first 4 bytes of `data` checked against an allowlist of approved selectors (e.g., only `exactInputSingle(bytes)`)? If `data` is opaque, the attacker can call any function on the target with any args.

3. **Pool/path validation**: if the call is a swap, is the pool key validated? Constant pool keys are safe. Caller-supplied pool keys with `tickSpacing/hooks` controllable by the attacker are not — attacker pre-deploys a malicious pool with whatever fee/tick math they want.

4. **Slippage bound**: is `amountOutMinimum` bounded by an independent oracle? If the user/executor can set `amountOutMinimum = 0` or `amountOutMinimum = 1`, the swap accepts any output regardless of true market price.

5. **Token decimal verification**: if the destination token is caller-supplied, is its decimal value sanity-checked? (Related: caller-supplied token with `decimals() = 0` causes downstream math to under/overflow.)

The Squid bug failed #1 (target unchecked), #3 (pool key caller-supplied), and #4 (no oracle bound on amountOutMinimum). Any ONE of these defended properly would have prevented the drain.

---

## Step 4 — Cross-class compose

Combine Step 2 + Step 3:

| Step 2 verdict | Step 3 verdict | Combined risk |
|----------------|----------------|---------------|
| Auth defended | Path defended | Safe |
| Auth defended | Path open | Self-rug only — principal can sabotage themselves (Informational) |
| Auth open | Path defended | Drain principal to whatever the path allows (High) |
| **Auth open** | **Path open** | **Critical — Squid bug shape** |

When both fail, severity is **Critical** under any reasonable filter — it's direct theft, permissionless, single-tx, no admin compromise.

---

## Step 5 — Bundler-specific check

A "bundler" is a wrapper function that loops over per-principal actions:

```solidity
function executeBatch(Order[] calldata orders, bytes[] calldata sigs) external {
    for (uint i = 0; i < orders.length; i++) {
        _executeOne(orders[i], sigs[i]);  // each call has its own auth check
    }
}
```

Two failure modes specific to bundlers:

1. **The bundler itself has no auth**: anyone can call `executeBatch`. The per-order `_executeOne` must be self-defending against an arbitrary `msg.sender`. If `_executeOne` assumes `msg.sender` is a trusted relayer, the bundler grants drain to anyone.

2. **Order-to-order sequencing**: if orders share state (e.g., a global flash-loan flag), an attacker can craft an order sequence that satisfies each order's individual check but violates the aggregate invariant. Squid's DelegateBundler reportedly used a per-Safe execution context that was reused across orders without reset.

For each bundler, simulate calling it as an unprivileged EOA with crafted orders. If any action goes through, the bundler is broken.

---

## Step 6 — On-chain detection (post-deploy)

For deployed contracts, a stake-pool-style verification: pull a historic successful tx, mutate ONE field at a time (msg.sender → unauthorized EOA, target → attacker-controlled, signature → bit-flipped), call `eth_simulateCall` or `eth_estimateGas`, observe revert reasons. The methodology is identical to the Solana `simulateTransaction` approach (see `prompts/solana/phase4b-runtime-templates.md` for the Solana equivalent).

For EVM specifically, use the eth_simulateCallV1 endpoint with state overrides:

```python
# Pull historic tx
# Mutate field
# eth_simulateCallV1 with stateOverrides={msg.sender: unauthorized_addr}
# Read result/revert reason
```

This is a 30-minute confirmation per attack vector, comparable to the LEAD-3/4/5 Solana workflow.

---

## Case study 2: Alchemist Aludel v1 (2026-05) — recipient unbound by unlock signature

Found during a TVL-scanner audit batch. The v1.16 detector grep MISSED this contract because it used Geyser/Aludel naming (`unstakeAndClaim`, `getPermissionHash`, `LOCK_TYPEHASH`, `UNLOCK_TYPEHASH`) instead of Squid naming. v1.17 extends the grep to capture this family.

The pattern:

```solidity
// Aludel.sol L916
function unstakeAndClaim(
    address vault,
    address recipient,     // ← attacker-supplied
    uint256 amount,
    bytes calldata permission
) external {
    _validateAddress(recipient);  // sanity-only: not zero/self/system

    // permission validates the unlock against UNLOCK_TYPEHASH
    // UNLOCK_TYPEHASH = keccak256("Unlock(address delegate,address token,uint256 amount,uint256 nonce)")
    // ← recipient is NOT in the typehash

    // ... reward calculation ...
    IERC20(rewardToken).transfer(recipient, rewardAmount);  // L1011/L1019/L1022
}
```

The bug: the unlock signature binds `delegate + token + amount + nonce`, but `recipient` is a free parameter. Anyone observing a victim's unstake transaction in the mempool can:

1. Extract the `permission` blob from the victim's pending tx
2. Front-run with `recipient = attacker_addr` (same `permission`, same `amount`, same `vault`)
3. The vault accepts the signed permission (typehash check passes)
4. Rewards flow to attacker instead of the victim

This is the same root cause family as Squid — **action binding failure**. The signature authorizes "unstake 1000 tokens" but the wrapper function lets the caller decide where those tokens go.

Why the v1.16 detector missed it:
- No `executeOnBehalf`, `executeBundle`, `executeBatch` in the source
- No `swapOnBehalf`, `executeOnSafe`, `delegateBundler`
- Used Geyser-inherited naming: `unstakeAndClaim`, `lockAndStake`, `rageQuit`, `IUniversalVault`

v1.17 extends the Section B grep with: `getPermissionHash`, `calculateLockID`, `onlyValidSignature`, `UNLOCK_TYPEHASH`, `LOCK_TYPEHASH`, `IUniversalVault`, `IRageQuit.rageQuit`, `unstakeAndClaim`, `lockAndStake`, `rageQuit`.

Detection rule for the recipient-unbound variant: if a public function takes a `recipient` (or `to`, `beneficiary`, `dest`) parameter AND validates a signature whose typehash does NOT include that parameter, flag as **Critical** under Step 2 hash-binding check.

Severity calibration: this specific Alchemist case is **Low** under the user's filter (sub-$100K extractable per vault, requires victim to first sign+broadcast). However, the **bug class** (recipient unbound by signature) is High-to-Critical when (a) per-vault TVL > $100K, or (b) the function is called via bundler/relayer where the victim does not see the front-run.

---

## Origin case study: Squid

The Squid attack was a textbook auth-gate failure compounded by path-validation failure:

1. `DelegateBundler.executeSameChainActions(...)` had a per-Safe loop that called `module.executeOnSafe(safe, target, data)`
2. The per-Safe auth check verified a signature against `verifyDelegateSignature(safe, delegate, sig)` where `delegate` was an `isAuthorizedDelegate[delegate]` lookup
3. The bug: the outer bundler had no check that msg.sender was an authorized relayer, AND the signature verification accepted any signature recoverable to ANY `delegate` in the allowlist (with delegate-rotation timing window), AND the loop's per-Safe `target` was caller-supplied with no allowlist
4. Attacker: built a Foundry script, looped over every Safe with the Module installed, called `executeSameChainActions` with `target = UniV3 router`, `data = swap(safe_USDC → attacker_pool → 'u')`, `amountOutMinimum = 1`. Module dutifully executed each swap. Safe's USDC went into the attacker's pre-seeded pool. Attacker drained the pool.

If any single one of the three checks above had been right, the attack fails:
- Right auth gate → bundler reverts on unauthorized caller
- Right action binding → signature only valid for one specific target+calldata, not any swap
- Right path validation → router/pool allowlist rejects attacker's pool

---

## Mitigation patterns (for engineers)

If you ship a Safe Module or delegate-executor pattern, the secure shape is:

```solidity
contract YourModule {
    mapping(address safe => mapping(address delegate => bool)) public authorizedDelegate;

    function executeOnBehalf(
        address safe,
        ApprovedAction calldata action,  // pre-approved target+selector tuple
        Signature calldata sig
    ) external {
        // 1. Bundler-level auth (optional but recommended)
        require(authorizedRelayer[msg.sender], "not relayer");

        // 2. Hash includes safe + action + nonce + chainId + this contract
        bytes32 hash = _hashTypedDataV4(_orderHash(safe, action, nonces[safe]++));

        // 3. Signature recovers to an authorized delegate FOR THIS SAFE
        address signer = ECDSA.recover(hash, sig);
        require(authorizedDelegate[safe][signer], "bad delegate");

        // 4. Action is on an allowlisted target with an allowlisted selector
        require(_isAllowedAction(action), "bad action");

        // 5. Execute through Safe
        ISafe(safe).execTransactionFromModule(action.target, action.value, action.data, Enum.Operation.Call);
    }
}
```

The Squid implementation reportedly missed at least step 1 and step 4.

---

## Trigger grep (used by `build_recon_maps.sh`)

For EVM:

```bash
# A. Safe Module pattern
grep -rnE "execTransactionFromModule\b|\b0x468721a7" "$SRC" 2>/dev/null

# B. Delegate-executor pattern (v1.17: extended with Geyser/Aludel naming)
grep -rnE "(executeOnBehalf|executeMetaTransaction|executeBundle|executeBatch|delegatedCall|verifyDelegate|isAuthorizedDelegate|onbehalfof|swapOnBehalf|executeOnSafe|executeFromExecutor|executeSameChain|delegateBundler|processDelegatedOrder|relayedExecute|getPermissionHash|calculateLockID|onlyValidSignature|UNLOCK_TYPEHASH|LOCK_TYPEHASH|IUniversalVault|IRageQuit\.rageQuit|unstakeAndClaim|lockAndStake|rageQuit)" "$SRC" -i 2>/dev/null

# C. Arbitrary-target call site
grep -rnE "(target|to)\.call\(|(target|to)\.delegatecall\(|ISwapRouter\([^)]+\)\.exactInput|IPoolManager\([^)]+\)\.swap|IUniversalRouter\([^)]+\)\.execute" "$SRC" 2>/dev/null

# D. Slippage = 0/1 patterns (red flag in combination with A/B/C)
grep -rnE "amountOutMinimum[\s=:]+[01][^0-9]|minAmountOut[\s=:]+[01][^0-9]" "$SRC" 2>/dev/null
```

Output goes to `$OUT/delegate-executor-map.md`. Set flag `SAFE_MODULE_OR_DELEGATE_EXECUTOR = true` if A or B hits. Set flag `ARBITRARY_PATH_EXECUTION = true` if C hits AND not all targets are immutable. Both flags raise severity ceiling for any finding on those functions to Critical.

---

## When to apply

This methodology runs whenever the recon flag `SAFE_MODULE_OR_DELEGATE_EXECUTOR` or `ARBITRARY_PATH_EXECUTION` is set. The `access-control-agent`, `periphery-agent`, and `multi-step-operation-safety` niche (Plamen-compatible) should reference this methodology in their prompts when the flag is active.

For contracts that ship a Safe Module specifically: treat the entire contract as Critical-class. Every public function becomes drain-equivalent if its auth gate fails. The audit budget for such contracts should be 1.5-2× a normal contract of the same LOC.
