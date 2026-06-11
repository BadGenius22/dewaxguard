---
id: M-15
name: expiry-race-matrix
trigger_type: code
trigger_grep: "(cancel|finish|settle|unlock|valid|redeem)[_ ]?(after|until|by|at)|expir(ation|y|es|ed)|\bdeadline\b|\bmaturity\b|\bttl\b"
trigger_languages: [all]
applies_to_protocol_types: [any]
---
# M-15 — Expiry Race Matrix

> **Purpose**: systematic methodology for auditing time-gated state transitions in any protocol that has state objects with expiry / deadline / TTL + interacting operations that can fire in the same block / ledger / slot.
>
> **Status**: first validated on XRPL April 2026 audit (Domain 19, 8-agent breadth, 2026-04-24). Populated ~46 matrix cells across 9 state-object types; 0 Medium+ expiry-race findings surfaced (all refuted — but template structure validated).
>
> **Cross-language**: applies to EVM, Solana, Move, Sui, Cosmos, any L1/L2 with ordered transaction bundles.

---

## Trigger

Invoke this methodology when the protocol under audit has ANY of:

1. A state object (escrow, offer, auction, subscription, loan, vesting schedule, lock, lease) with an `expiration` / `deadline` / `cancelAfter` / `unlockAt` / `settleBy` / `maturity` field.
2. Two or more operations that (a) mutate the state object's lifecycle (cancel, finish, execute, settle, slash, reclaim) and (b) can be submitted by different actors or are permissionless post-expiry.
3. Any batch / bundle / multi-call / multi-instruction mechanism that lets an attacker atomically sequence ops against a time-gated object.
4. Any ordering mechanism where multiple ops targeting the same object can land in the same block / ledger / slot.

---

## Methodology (the 4-question matrix)

For every `(SLE × interacting-op × race-condition)` cell, answer 4 questions:

### Q1 — Who wins at the exact boundary?

At the instant when `currentTime == expiration`:
- Does op A succeed? Does op B succeed?
- Is the comparison `>` (strict) or `>=` (inclusive)?
- Are there multiple comparison helpers in the codebase with different strictness? Do they disagree at the boundary?

**Red flag**: Two ops both "win" at the same boundary (both succeed). Non-deterministic outcome for the contested resource.

**Red flag**: Neither op wins at the boundary (dead zone). The resource is stuck for exactly 1 time unit.

**Validation target**: Winner must be deterministic and economically coherent. "Finish wins at boundary, Cancel wins past boundary" (XRPL Escrow) is coherent — exclusive execution. "Neither wins at boundary" (dead zone) is incoherent — bug.

### Q2 — Can an attacker observe the race?

- Is the outcome predictable from information available to the attacker BEFORE their tx is included?
- Does the attacker need mempool access, consensus-window access, or private peering to predict the winner?
- Is there a public RPC that leaks the outcome prematurely (partial commit, simulation endpoint, optimistic execution)?

**Red flag**: Attacker can predict the winner but the victim cannot (information asymmetry).

**Red flag**: Observable-but-not-triggerable races (Q2=YES, Q3=NO) still enable MEV via private-relay bundling.

### Q3 — Can an attacker trigger the race?

Enumerate ordering mechanisms available to the attacker:

| Mechanism | Attacker control | Platform examples |
|---|---|---|
| **Canonical tx order, same account** | HIGH (attacker chooses sequence numbers) | XRPL seqProxy; EVM nonce; Solana nonce |
| **Canonical tx order, cross-account** | LOW (consensus-random) | XRPL `AccountID XOR parentHash(prev)`; EVM mempool fee priority (attacker controls gas price); Solana leader-dependent |
| **Batch / bundle / multicall** | HIGH (attacker orders inner ops) | XRPL `sfRawTransactions` array; EVM multicall/Flashbots bundle/EIP-2718; Solana instruction array |
| **Cross-chain message / L2 sequencer** | LOW–HIGH (sequencer-dependent) | LayerZero ordering, Optimism sequencer, Arbitrum Nitro |
| **MEV-boost / private relay** | HIGH (fee-market auction) | EVM mainnet Flashbots; Solana Jito bundles |
| **Same-account Batch defense by defender** | HIGH (symmetric to attacker's Batch) | Whatever mechanism attacker uses |

**Red flag**: Attacker has Batch access but defender does NOT (platform disables defender's operation from Batch). Example: XRPL `ttVAULT_CLAWBACK` in `Batch::disabledTxTypes` — attacker (holder) can Batch-replenish; defender (issuer) cannot atomically Batch-Cancel-then-Clawback.

**Red flag**: Ordering mechanism is controllable but the platform doesn't document this; a careless protocol team may assume ordering is random.

### Q4 — Is there profitable outcome asymmetry?

For each possible ordering outcome:
- What does the attacker gain (assets, state, capability)?
- What does the victim lose (assets, state, capability)?
- What is the cost to attempt the race (fees, reserves, gas)?
- What is the cost of failure (fees burned, state rolled back, time wasted)?

**Red flag**: Attacker's gain on WIN >> attacker's cost on LOSS. Race is profitable-in-expectation even at 50/50 odds.

**Red flag**: Victim's loss is large but cost-to-attack is small — attacker can retry indefinitely until they win.

**Red flag**: Asymmetry is self-reinforcing — WIN lets attacker further entrench their position, raising odds for the next round.

**Validation target**: Race is BOUNDED in damage (one-shot only, or costs scale with exploit window) AND recoverable (victim has a safe escape).

---

## Ordering mechanisms to consider (cross-language inventory)

When building the matrix, enumerate ALL ordering mechanisms available on the target platform:

### Generic (any L1/L2)

- **Canonical block-internal ordering** — nonce, sequence number, or deterministic hash ordering.
- **Mempool / pending-pool ordering** — fee priority (EVM), TxQ (XRPL), slot-time priority (Solana).
- **Transaction bundle / batch** — groups multiple ops into atomic unit; attacker usually picks the inner order.
- **Cross-account interleave** — two actors submit to the same block; interleave order determined by platform-specific rules (often hash-based random, sometimes fee-ordered).

### EVM-specific

- **Gas-price auction** — attacker can outbid victim to land first.
- **Flashbots / MEV-boost bundles** — attacker pays block builder directly; bypasses public mempool.
- **EIP-1559 priority fee** — attacker competes on `maxPriorityFeePerGas`.
- **Multicall / Permit2 / EIP-2718 envelope** — attacker composes multiple ops atomically.
- **Delegatecall / proxy re-entrancy** — attacker can interleave state reads/writes within a single call stack.

### Solana-specific

- **Instruction array ordering** — inner instructions execute sequentially in the order the transaction author specified.
- **Compute budget priority** — attacker can set higher compute price to land earlier in the block.
- **Versioned transaction with Address Lookup Tables (ALT)** — attacker controls which accounts are addressed.
- **Jito bundle** — attacker pays leader for atomic bundle inclusion.
- **Slot-boundary ordering** — two txs in different slots execute in strict slot order.

### XRPL-specific (validated)

- **CanonicalTXSet** — within a ledger: `AccountID XOR parentHash(prev)` primary, `seqProxy` secondary, `txId` tertiary. Cross-account: consensus-random. Same-account: deterministic.
- **Batch inner-tx array** — attacker orders via `sfRawTransactions`.
- **`Batch::disabledTxTypes`** — some tx types (e.g. `ttVAULT_CLAWBACK`) banned from Batch; creates asymmetric defense.

### Move / Sui / Aptos-specific

- **Programmable Transaction Block (Sui)** — atomic bundle of commands; attacker-chosen order.
- **Module entry ordering** — if protocol design requires specific ordering, violations detected at tx commit.
- **Clock / TimestampUs** — typically read-only within tx; boundary comparisons similar to EVM.

### Cosmos-specific

- **BeginBlocker / EndBlocker ordering** — module-level hooks fire at block boundaries; attacker cannot interleave against them but can SET UP state in the same block.
- **IBC packet ordering** — cross-chain ordered; relayer-dependent for race resolution.

---

## Reward-pool framing (DO NOT skip)

Every race hypothesis MUST be connected to a concrete user loss before submission. Contest judges and protocol teams reject "could create ambiguity" or "makes ordering unfair" without a dollar-impact target.

Valid loss targets:
- **Direct fund loss** — attacker extracts user's balance / collateral / shares.
- **Locked-state loss** — user's funds become permanently inaccessible (expired escrow with no recovery path).
- **Bricked capability** — a designed-to-work operation now permanently fails (destroy, clawback, redemption).
- **Fee griefing** — victim pays fees for ops that cannot succeed (quantified: $X per attack round).
- **Reserve / rent siphon** — attacker forces victim to pay reserves they cannot recover.

Invalid "losses" (will be rejected):
- "Ordering is non-deterministic" (without concrete consequence).
- "Theoretical attacker could front-run" (without showing the profit path).
- "Code looks confusing" (documentation nit).
- "Race exists but both outcomes are within design" (e.g. symmetric 50/50 with zero asymmetry).

---

## Cross-language examples (applied)

### Example 1 — XRPL MPT escrow × Clawback (validated in Domain 19)

- **SLE**: `ltESCROW` with `sfCancelAfter`.
- **Interacting op**: `Clawback(alice, MPT)` submitted by issuer at expiry ledger.
- **Race**: At ledger M with `parentCloseTime(M) > sfCancelAfter`, the escrow becomes cancellable (by anyone) and Alice's transparent balance is 0 (F-13 blind spot). If `EscrowCancel` runs first: Alice's balance restored → Clawback succeeds. If Clawback runs first: fails with `tecINSUFFICIENT_FUNDS`.
- **Q1 (who wins at boundary)**: At `now == sfCancelAfter`, `after(>)` strict → Cancel blocked, Finish allowed. Race starts at the NEXT ledger.
- **Q2 (observable)**: Yes via public mempool / canonical ordering.
- **Q3 (triggerable)**: Issuer can bundle `Batch[EscrowCancel, Clawback]` atomically via attacker-controlled `sfRawTransactions` order. Deterministic ISSUER WIN.
- **Q4 (profitable asymmetry)**: Only if issuer FAILS to batch. Careless-issuer scenario — T-03/T-10 trust model excludes. BOUNDED.
- **Verdict**: CONFIRMED race, REFUTED as new-submission exploit (dupe of ESC-1 + careless-issuer-bounded).

### Example 2 — Generic EVM escrow + clawback

- **SLE**: ERC-3475 / custom escrow contract with `mapping(bytes32 => Escrow)` + `expiry` timestamp.
- **Interacting op**: Admin-initiated `clawback(user, token, amount)` + user-initiated `cancelEscrow()` at expiry.
- **Race**: Within one block:
  - Order [cancel, clawback]: cancel refunds user's balance; clawback then seizes it. Admin wins.
  - Order [clawback, cancel]: clawback fails (user balance = 0 while locked); cancel then refunds. User keeps.
- **Q1**: Typically `block.timestamp >= expiry` INCLUSIVE in Solidity (`require(block.timestamp >= expiry)`). At exact boundary, expired.
- **Q2**: Mempool-observable; attacker can use MEV-boost to bundle.
- **Q3**: Admin can use `multicall` (OpenZeppelin pattern) to atomically `[cancelEscrow, clawback]`. User can defend via `multicall[cancelEscrow, deposit]` to re-escrow. If admin fails to multicall AND user monitors: 50/50 race via gas-priority.
- **Q4**: Admin's win = full clawback amount; admin's cost = 2 tx gas + MEV-tip. Admin's best strategy = always use multicall. User's best strategy if admin is sloppy = Flashbots private bundle. **Race is symmetric for profit — not a bug per se; design flaw if multicall path is undocumented.**
- **Audit focus**: Is multicall EXPECTED by admin SOP? Is there a design doc saying "always use multicall for clawback flows"? If not → documentation finding. If clawback is NOT enabled via `clawback` role → this becomes a real bug (admin cannot recover).

### Example 3 — Solana vault close-at-deadline

- **State**: PDA-backed vault account with `close_at: i64` slot timestamp.
- **Interacting ops**: `close_vault()` (permissionless post-close_at), `withdraw()` (user), `slash()` (governance).
- **Race**: At slot S with `Clock::get().slot >= close_at`:
  - `close_vault` drains funds back to creator.
  - `withdraw` returns user's deposit.
  - `slash` confiscates staked amount.
- **Q1**: Solana uses `Clock::slot >= close_at` INCLUSIVE typically. At exact boundary, closeable.
- **Q2**: Mempool semi-observable (Solana mempool is stateless / forwarded to leader); attacker with RPC access can observe.
- **Q3**: **Instruction array attack**: attacker builds `[close_vault, withdraw]` as a single transaction — instruction array is attacker-ordered. Or Jito bundle for same-slot atomic sequencing.
- **Q4**: If `close_vault` runs first in same tx → vault state is "closed"; `withdraw` hits the `require(!closed)` check → fails. User loses withdrawal. **Profitable asymmetry**: attacker extracts vault funds AND blocks user withdrawal in one atomic tx.
- **Audit focus**: Does `close_vault` require `slot > close_at + grace_period`? Does `withdraw` have priority execution that predates close? Is there an anti-composability guard (e.g. `require(!instruction_introspection::is_last_instruction())`)? If none → this is a Medium+ finding.

---

## Cell status codes

When populating the matrix, mark each cell with one of:

- **CONFIRMED** — race exists AND exploit is profitable for attacker. Submittable if NEW or elevated impact.
- **PARTIAL** — race exists but only exploitable in bounded scenarios (careless-victim, out-of-scope actor). Document for defensive pattern catalog; may not be submittable.
- **REFUTED** — race exists but has no profitable asymmetry. Document why (symmetric outcome, dead-zone by-design, 3rd-party cleanup is unprofitable).
- **VERIFIED safe** — no race (ordering is deterministic, boundary is exclusive, one-side-only).
- **OOS** — race exists in unchanged legacy code; excluded per contest scope rule.
- **UNEXPLORED** — cell identified but not probed during the audit.

---

## Checklist before closing the matrix

- [ ] Every SLE type with an expiry field is represented as a row.
- [ ] Every tx type that reads or mutates the SLE is represented as a column (not just the obvious cancel/finish).
- [ ] Cross-feature cells are probed (e.g. expiry × freeze, expiry × clawback, expiry × flag mutation).
- [ ] Batch / bundle compositions are enumerated for both attacker and defender.
- [ ] Boundary semantics (strict `>` vs inclusive `>=`) are tabulated across all helpers and SLE types.
- [ ] At least one cell per (SLE, op) pair is classified with a status code.
- [ ] Every CONFIRMED cell has a concrete user-loss target in USD or asset units.
- [ ] Every REFUTED cell has a one-line reason.
- [ ] UNEXPLORED cells are flagged for depth-loop probing.

---

## Manifest-entry template (when Methodology finds something)

If the matrix surfaces a new framework fact, refuted class, or defensive pattern, propose a manifest entry in this format:

```
- **F-NN (proposed)**: [one-line fact about platform expiry semantics]
  **File:Line**: [citations]
  **Impact**: [which hypotheses are refuted or enabled]
  **Verified**: [domain/date/agent]
```

And for the high-value "negative result" case (no submittable finding but structural refutation is valuable):

```
- **R-NN (proposed)**: "[hypothesis class]" → refuted by [F-NN reference]. Generalizes to [list of adjacent classes].
  **Source**: [domain]
```

---

## References

- XRPL April 2026 audit, Domain 19: `scratchpad/dewaxguard-domain-19/domain_19_fullrun_merged.md` (46-cell matrix populated, 0 Medium+ race findings; 1 adjacent Low MP-1 sponsor-reserve bug from the same sweep).
- Pattern origin: extended from M-08 (Holder-plants-trap / Issuer-action-bricks-state) to time-gated variant.
- Related: M-09 (Aggregate-vs-per-entity SYNC_GAP), M-12 (Granular permission sandbox ↔ semantic override).
