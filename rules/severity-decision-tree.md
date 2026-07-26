# Severity Decision Tree (a / b / c)

> **Phase**: 5d (Bug Validator) — applied to every PASS finding before report routing
> **Purpose**: Replace ad-hoc severity reasoning with a 3-question ordered tree. The FIRST "yes" determines severity. Forces validators to articulate the impact mechanism rather than pattern-match severity.
> **Origin**: Ported from cosminmarian53/skills `soroban-auditor` Verifier prompt.

---

## The Tree

For every finding that survives Gate 1 (Refutation), Gate 2 (Reachability), and Gate 3 (Trigger), the validator MUST answer these questions IN ORDER. The first "yes" determines severity:

```
a. Can assets be DIRECTLY stolen, lost, or permanently locked by an attacker?
   → YES: severity = HIGH (escalate to CRITICAL only if Likelihood: High via severity-matrix.md)
   → NO: continue to b

b. If not (a): Is a CORE PROTOCOL FUNCTION broken,
                is AVAILABILITY/LIVENESS impacted,
                or does INCORRECT ACCOUNTING compound over time to leak material value?
   → YES: severity = MEDIUM
   → NO: continue to c

c. Else: severity = LOW / QA / Informational
```

The validator MUST emit a `severity_check:` field for every finding:

```
severity_check: a=NO, b=YES (liveness — pause cannot be reversed) → MEDIUM
severity_check: a=YES (debt token theft via balance-of mismatch) → HIGH
severity_check: a=NO, b=NO (cosmetic event mismatch) → LOW
```

Findings without `severity_check:` populated are auto-failed by the validator harness.

---

## Interpreting "directly stolen, lost, or permanently locked" (question a)

YES requires ALL of the following:

1. **Identifiable victim**: a user, the protocol treasury, or a specific role's funds are diminished.
2. **Permissionless or commodity precondition**: the attacker either has no special role, OR has a role that is freely obtainable (e.g., any LP, any borrower).
3. **No legitimate compensating action**: the victim has no protocol-supplied remedy that would make them whole within the same transaction or block.

Examples:
- ✅ a=YES: attacker drains a liquidity pool via reentrancy on `withdraw()`.
- ✅ a=YES: rounding bug systematically rounds against users on every `redeem()`, attacker triggers it at scale.
- ❌ a=NO: bug requires the protocol admin to call a malicious function — that's centralization, not direct theft.
- ❌ a=NO: liquidator bonus is 1bp lower than documented — accounting error, not theft (route to b).

---

## Interpreting "core protocol function" (question b)

YES if any of the following hold:

1. **Liveness / availability**: a core entry point can be DoS'd by an attacker, OR a state machine deadlocks (e.g., admin can pause but no path unpauses).
2. **Compounding accounting drift**: an error of any size that accumulates with each call and is not bounded by user action (e.g., interest index drift, share-price drift).
3. **Invariant break**: a protocol-declared invariant (from docs, from `fuzz/invariants.rs`, or from on-chain code comments) can be violated.
4. **Material accounting inconsistency**: a balance / supply / accumulator can drift from its source-of-truth identity, even if no theft is possible right now (the drift is the bug; theft would be a downstream consequence).

### b-qualifier — availability answers require the grief-economics gates (HARD)

A **liveness / availability** answer of b=YES is provisional. Before it stands, the finding MUST clear all three gates in `rules/severity-matrix.md` → *Grief economics*: G1 economic rationality (attacker's unrecoverable cost < quantified victim harm), G2 operator recovery (no routine privileged action restores service), G3 quantification (`attacker_cost:` and `victim_harm:` both declared). Failing any gate caps the finding at **Low**, regardless of how cleanly the DoS reproduces.

This qualifier exists because b=1 ("a core entry point can be DoS'd by an attacker") is trivially satisfiable — nearly every griefing claim reaches it — and on its own it inflated a real DRE defect to Medium that judges scored as no finding at all. Compounding-accounting (b=2), invariant breaks (b=3), and accounting inconsistency (b=4) are **not** subject to the gates; they describe value drift, not availability.

Examples:
- ✅ b=YES: `liquidity_index` updates skip a write path, slowly under-counting accrued interest. *(b=2, not availability — gates do not apply.)*
- ⚠️ b=PROVISIONAL: `liquidationCall()` can be DoS'd by a tiny dust deposit that hits a 200-storage-read limit. *Availability claim — run the gates.* It holds at Medium only if the dust is cheap **and** recoverable by the attacker **and** no admin path clears it **and** the victim harm is quantified (e.g. positions stay underwater and bad debt accrues). If the dust is burned and an operator can clear the queue, this is **Low**.
- ❌ b=NO → Low: a permissionless dust action bricks an automated queue, but the treasury can fill around it and no funds are lost — the attacker pays more than the victims lose. *(DRE 2026-07: submitted Medium with a passing fork PoC, rejected outright.)*
- ❌ b=NO: a view function returns slightly stale data when called between two state mutations within the same block — read-only, no compound impact.

---

## Interpreting "low / QA" (question c)

LOW is the default for findings that survive validation but neither steal funds nor break protocol functions. Typical c-cases:

- Code quality issues (unused vars, dead code, redundant checks).
- Event parameter mismatches that don't affect on-chain state.
- Documentation drift between code and natspec/comments.
- Suboptimal gas patterns.
- Centralization risks where the trusted role has no permissionless path to harm.

c-tier findings route to the platform's QA channel:
- **Code4rena**: consolidated `QA-Bundle.md` (per `references/criteria/c4-competitive.md`).
- **Sherlock**: low-severity issues file.
- **Cantina/Immunefi**: omit unless explicitly requested.

---

## Interaction with severity-matrix.md downgrades

The decision tree determines the **base** severity. After the tree, apply downgrade modifiers from `rules/severity-matrix.md`:

```
After tree:        severity = MEDIUM
Modifier check:    Attack requires FULLY_TRUSTED actor → -1 tier → LOW
Final severity:    LOW
```

Modifiers:
- **Grief economics** — a DoS/griefing finding failing G1 (uneconomic), G2 (operator-recoverable), or G3 (unquantified) → **cap at Low**. See `rules/severity-matrix.md` → Grief economics. Applied mechanically by `scripts/severity_router.py`; runs before the proven-only cap, so a `[FORK-PASS]` cannot rescue it.
- Attack requires FULLY_TRUSTED actor (governance multisig, DAO, timelock) → −1 tier (floor: Info).
- View-function-only impact → cap at Medium.
- On-chain-only exploit (no UI/off-chain path AND impact confined to on-chain state) → −1 tier.
- Attack requires control of block production on an external chain (Bitcoin mining, ETH proposer slot, etc.) → cap at Low (contest) / Medium (bounty). See `rules/severity-matrix.md` for the full rationale. Distinct from M-27 (capital-dependent attacks): the prerequisite here is *capability* (mining pool / validator slot), not *capital*.

The `severity_check:` field MUST record both the pre-modifier and post-modifier severity:

```
severity_check: a=NO, b=YES (liveness) → MEDIUM; modifier: requires pool-admin → LOW (floor)
```

For any **availability / griefing** finding, `severity_check:` must also show the grief-economics gates, and the finding body must carry the three declared fields:

```
severity_check: a=NO, b=YES (liveness) → MEDIUM;
                G1 attacker cost $12 unrecoverable vs victim harm = delay only → FAIL
                → cap LOW
attacker_cost: ~$12 dust + gas, UNRECOVERABLE (NFT parked at a blacklisted address)
victim_harm:   withdrawals delayed until TREASURY manually fills; no funds lost
operator_recoverable: true
```

---

## Interaction with platform bug-validator scoring

The bug validator (Phase 5d) scores findings 0-100 against platform criteria. The severity decision tree feeds the validator's "Claimed vs Predicted Severity" comparison:

- If the finding's claimed severity matches the tree result → no deduction.
- If the finding's claimed severity is HIGHER than the tree result → deduct 10-30 points (severity inflation).
- If the finding's claimed severity is LOWER than the tree result → no deduction (sandbagging is acceptable; judges may upgrade).

This gives the validator a mechanical, defensible reason to downgrade inflated severities before submission.
