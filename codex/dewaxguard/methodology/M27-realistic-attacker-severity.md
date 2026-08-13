---
id: M-27
name: realistic-attacker-severity
trigger_type: process
trigger_event: "severity assessment of any finding claiming direct fund loss that requires attacker capital and is not flash-loanable"
trigger_languages: [all]
applies_to_protocol_types: [any]
---

# M-27: Realistic-Attacker Severity Framework

> **Origin**: Ledgity Yield audit (2026-05-26). H-01 (WrappedLToken APR-race) was graded High based on a stacked worst-case scenario ($100M TVL × 90d gap × 100% attacker share → $1.24M extraction). Mainnet-fork PoC verified the mechanism but the realistic-attacker EV at production parameters caps in the Medium tier ($30k–$400k range, requires $1M+ pre-positioned capital). The audit had no framework forcing the auditor to compute *who can actually pull this off and what does it cost them*.
>
> **Trigger**: Any finding whose Impact is "direct fund loss" AND whose attack mechanism requires the attacker to provide capital (not flash-loanable). Mechanically: if a finding lists a dollar magnitude in its Impact section, run this framework before fixing severity.
>
> **Yield**: prevents severity inflation when an attack mechanism is real but only profitable to attackers who control capital that doesn't exist at the protocol's expected scale. Forces the severity grade to reflect the marginal-attacker class, not the maximum-attacker class.

---

## The decision problem

The standard severity matrix (Impact × Likelihood) is a 2D grid with English glosses. "Likelihood: Medium = specific conditions" is ambiguous for capital-dependent attacks. Two auditors looking at the same finding can rationally pick different Likelihood tiers depending on whether they think of "specific conditions" as the *event* (an APR cut, a liquidation, a governance vote) or the *attacker state* (holding $X capital pre-positioned).

This methodology resolves the ambiguity by adding a **per-finding realistic-attacker EV calculation**. The result feeds into the existing Likelihood column.

---

## When to apply

```
Apply M-27 IF:
  finding.impact.dollar_magnitude_claimed != None
  AND finding.attack.requires_attacker_capital == YES
  AND finding.attack.flash_loanable == NO   (verified via M-27 Step 0)

Skip M-27 IF:
  finding requires no attacker capital (e.g., reentrancy from anywhere)
  OR finding is flash-loanable (use R15 / FLASH_LOAN_INTERACTION instead)
  OR finding is in a category where severity is fixed by mechanism alone
     (e.g., "any user can permanently brick the contract" → severity from
      mechanism, capital-realism doesn't apply because trigger is permissionless
      and the *bricking* doesn't pay anyone)
```

---

## STEP 0 — Verify the attack is not flash-loanable

Before running the framework, prove the attacker cannot bootstrap their position with a flash loan. The wrap-and-unwrap-in-same-tx test is the canonical check for vault-shaped bugs:

```
HYPOTHETICAL FLASH LOAN PATH:
  1. flash_loan_amount = X tokens
  2. wrap(X) → receive Y shares
  3. unwrap(Y) → receive Z tokens
  4. repay flash loan (X tokens)
  5. attacker profit = Z − X − loan_fee

Verify with code-trace OR PoC that Z ≤ X (attack is neutralized for fresh wraps).
```

For non-vault shapes, identify the equivalent same-block bootstrap. If ANY same-block bootstrap is profitable, this is a flash-loan attack — use R15, not M-27.

If verified non-flash-loanable, proceed to Step 1.

---

## STEP 1 — Compute per-share excess

For attacks where the bug pays out at an inflated rate proportional to held shares, compute the **per-share excess** the attacker extracts beyond fair value:

```
per_share_excess = (wrapper_quoted_rate − fair_rate) where
  fair_rate = reserves_pre_attack / total_supply_pre_attack
  wrapper_quoted_rate = the rate the buggy code uses to pay the attacker
```

This is unitless (decimal) and scales linearly with all of:
- attacker_position_size (their shares × fair_value)
- time_elapsed_since_trigger (longer stale window = bigger drift)
- parameter_delta (larger APR cut, larger oracle move, etc.)

For attacks that don't fit the per-share model, generalize: `attacker_profit = f(attacker_capital, time, delta)` and continue.

---

## STEP 2 — Define the meaningful-loss threshold

The meaningful-loss threshold is the smallest dollar amount that justifies a given severity tier at this protocol's scale:

```
meaningful_loss = min(0.5% of expected_TVL_band, $100k)
```

Where `expected_TVL_band` comes from:
- The protocol's stated TVL targets (from docs / pitch deck)
- The expected_TVL_band field in design_context.md (filled by Recon Agent 1B)
- If neither is available, use $10M as the small-protocol default

`meaningful_loss` is the dollar amount where reasonable readers would agree "this is a problem worth a CVE." Below this, the bug exists but is dust.

---

## STEP 3 — Compute attacker capital required

Invert the profit function to solve for capital required to extract `meaningful_loss`:

```
attacker_capital_required = meaningful_loss / per_share_excess
                          (under realistic time and delta assumptions —
                           NOT the maximum stacked scenario)
```

For "realistic time" and "realistic delta": use the **median** observed in similar protocols, not the maximum:
- Time-since-trigger: how long does it typically take for a normal user to react? For passive yield wrappers, days. For active DEXes, minutes. For governance, hours.
- Parameter delta: what's the largest single-event change the protocol's history shows? APR cuts of >5pp are uncommon; oracle moves of >10% are uncommon; etc.

If the protocol has no history, use:
- `time = 7 days` (one weekly cycle — long enough for the bug to be visible, short enough to be a realistic mempool-watcher reaction)
- `delta = the median parameter change in similar protocols`

---

## STEP 4 — Classify the realistic attacker

Map `attacker_capital_required` to a realistic attacker class:

| Capital required | Realistic attacker class | Likelihood tier |
|---|---|---|
| < $1k | Anyone with a wallet | **High** |
| $1k – $100k | Retail user / small-fund | **High** |
| $100k – $1M | Sophisticated retail / MEV bot operator | **Medium** |
| $1M – $10M | Whale / professional trading firm | **Low** |
| $10M – $100M | Institutional / large fund | **Low** (very narrow class) |
| > $100M | Whale-only at protocol-TVL scale | **Low** (effectively rules out unless protocol is large) |

Two additional considerations that can shift the tier:

**Capital lock duration**: how long must the attacker hold the position before the trigger? If they must commit capital from `pre_trigger_time` to `unwrap_time`, the opportunity cost is:
```
opportunity_cost = attacker_capital × (best_alternative_yield − this_protocol_yield) × lock_duration / 365
```
If `opportunity_cost > meaningful_loss / 4`, the attack is net-negative for any realistic actor — drop one tier in Likelihood.

**Trigger frequency**: how often does the triggering event (APR change, governance vote, oracle update) occur? If yearly, attackers must commit capital all year for one event — drop one tier. If daily/weekly, no adjustment.

---

## STEP 5 — Output severity

Combine Impact (from the standard matrix in `rules/severity-matrix.md`) with Likelihood from Step 4:

| Impact | Realistic-Attacker Likelihood (from M-27) | Severity |
|---|---|---|
| High | High | Critical |
| High | Medium | High |
| **High** | **Low** | **Medium** |
| Medium | High | High |
| Medium | Medium | Medium |
| Medium | Low | Medium |

The auditor MUST record the M-27 computation in the finding's body:

```markdown
**M-27 (Realistic-Attacker Severity)**:
  Per-share excess: 37 bps at 30-day gap, 9% → 4.5% APR cut
  Meaningful loss threshold: min(0.5% × $10M TVL, $100k) = $50k
  Capital required for meaningful loss: $50k / 0.0037 = $13.5M pre-positioned
  Realistic attacker class: Whale / professional firm (capital >$1M)
  Likelihood: Low
  Impact: High → Severity: Medium
```

This record is **mandatory**. Findings claiming a dollar magnitude without an M-27 record are rejected by the Phase 5d validator.

---

## Worked example — H-01 Ledgity WrappedLToken APR-race

**Mechanism**: `updateRateCheckpoint` guard at `WrappedLToken.sol:L190` compares values in incompatible units (raw UD7x3 vs RAY/base-100). The refresh fires every call and compounds the OLD APR over the elapsed window before storing the NEW APR.

**Step 0 — flash-loanable?**
Mainnet-fork PoC (`poc_h01/test/H01_AprRace_SonicFork.t.sol`) confirms `_wrap` and `_unwrap` share the same `updateRateCheckpoint` path. A same-tx wrap refreshes the cache, so any same-tx unwrap pays at the freshly-set (correct) rate. Flash-loan profit = 0. → **Non-flash-loanable, proceed.**

**Step 1 — per-share excess**:
- At 30-day gap, 9% → 4.5% APR cut: drift = ~37 bps per share
- At 7-day gap: ~9 bps per share
- At 1-day gap: ~1 bps per share

**Step 2 — meaningful loss threshold**:
- Expected TVL band: $10M (small-protocol default; wLUSDC has no real history yet)
- Threshold = min(0.5% × $10M, $100k) = **$50k**

**Step 3 — attacker capital required**:
- At realistic 7-day gap: capital = $50k / 0.0009 = **$55M**
- At median 30-day gap (if no other holders react sooner): capital = $50k / 0.0037 = **$13.5M**

**Step 4 — realistic attacker class**:
- $13.5M pre-positioned, locked from before the APR cut until unwrap = whale class
- Capital lock duration: months (must hold before AND after the APR cut event)
- Trigger frequency: APR cuts happen quarterly-ish in similar protocols → drop one tier
- Combined: **Low** likelihood

**Step 5 — severity**:
- Impact: High (direct fund loss to other holders)
- Likelihood: Low (per M-27)
- → **Medium**

Compare to the audit report which graded H-01 as **High** by stacking $100M TVL + 5pp delta + 90d gap + 100% attacker share. Each parameter was independently realistic; their conjunction was not. M-27 forces the median scenario instead.

---

## Worked example — drainable reentrancy (control case)

**Mechanism**: `withdraw()` has reentrancy; any caller can drain the entire pool.

**Step 0 — flash-loanable?**
The attack requires no capital from the attacker (the drain pulls from the pool's reserves, not the attacker's balance). Per-attacker-share excess is undefined; profit = entire pool.

**Decision**: M-27 does not apply. Skip the framework. Use standard severity matrix.

**Severity**: High Impact × High Likelihood = **Critical**

This is the canonical "drainable reentrancy" case. M-27 correctly defers to the standard matrix here because no capital constraint exists.

---

## Worked example — oracle-staleness liquidation manipulation

**Mechanism**: A stale oracle price lets an attacker liquidate borrowers at a stale-good price. Attacker profit = liquidation bonus × position size.

**Step 0 — flash-loanable?**
- The attacker uses flash-loaned capital to repay the borrower's debt and seize collateral.
- → Flash-loanable. Skip M-27. Use R15 / FLASH_LOAN_INTERACTION.

**This case demonstrates the M-27 exclusion**: capital-dependent attacks are M-27. Capital-amplifiable attacks are R15. The two are mutually exclusive.

---

## Why this is robust across protocols

M-27 does NOT hardcode dollar thresholds or specific bug shapes. It defines a **process**:
1. Compute the per-unit-capital extraction rate from the bug
2. Multiply by realistic event parameters (median, not max)
3. Invert for capital required to extract a meaningful loss
4. Map capital to a realistic attacker class
5. Use that class's likelihood in the standard matrix

The output naturally scales:
- Larger protocol → larger meaningful_loss threshold → larger capital required for "Medium" → fewer attackers, but those who exist extract more
- Smaller protocol → smaller threshold → smaller capital → broader attacker class, smaller absolute losses

For a $1B-TVL protocol with the same bug, M-27 gives:
- meaningful_loss = $100k (capped, not 0.5%)
- capital required at 30-day gap: $27M
- still whale-class, still Low likelihood
- but the protocol's larger TVL also means $100k is more like "actually meaningful" relative to user expectation → severity still Medium

For a $100M-TVL protocol with a bigger APR delta (10pp), the same framework gives:
- per_share_excess: 80 bps at 30-day gap
- capital required: $50k / 0.008 = $6.25M
- whale class but smaller capital → Low → still Medium (Impact High × Low = Medium)

For a $50M-TVL protocol with a 5pp delta over 60d:
- per_share_excess: ~80 bps at 60-day gap
- meaningful_loss = $250k (capped at 0.5% × $50M)
- capital required = $250k / 0.008 = $31M
- Still whale-tier → Low → Medium

The framework consistently produces Medium for this bug class across protocol scales, because the bug's *per-unit extraction rate* is fundamentally moderate. Only when the bug has a much higher per-unit rate (e.g., a 5% per share over-extraction) does it cross into High territory.

---

## Integration points

- **Phase 1 (recon)**: Recon Agent 1B writes `## Economic context` to `design_context.md`:
    - `expected_TVL_band` (small <$10M, mid $10–100M, large >$100M)
    - `actor_profile` (retail-heavy, whale-heavy, institutional)
    - `trigger_frequency` for any state-changing admin operations referenced by findings
- **Phase 4b (depth)**: depth agents that produce a dollar magnitude must populate the M-27 inputs into their finding output:
    - `per_share_excess` or equivalent extraction rate
    - whether the attack is flash-loanable (Step 0)
- **Phase 5d (bug validator)**: applies M-27 mechanically. Findings claiming a dollar magnitude without an M-27 record are rejected for re-grading.
- **Phase 6 (report)**: the M-27 record is included in the finding body as a `**M-27 (Realistic-Attacker Severity)**:` block.

---

## Anti-bloat sanity check

| Gate | Status |
|---|---|
| Methodology over patterns | YES — encodes HOW to compute realistic-attacker EV, never WHICH bugs to find |
| Line budget | 280 lines, under the 300-line skill cap |
| Duplication check | No overlap with R15 (flash-loan amplification, opposite direction), no overlap with realism-filter (trigger-actor classification, not capital), no overlap with severity-matrix (extends the Likelihood column rather than replacing it) |
| Marginal value | High — closes a systematic over-grading gap that exists in EVERY capital-dependent direct-fund-loss finding |
| Overlap check | grep `realistic.*attacker`, `capital.*required`, `meaningful.*loss` in existing rules → no hits |

---

## Validation gate

This methodology is provisional until it has been validated against at least 5 past findings from independent audits and produces severities consistent with the audits' final shipped grades (or improves them with a defensible reasoning trace). Track validation in:

```
~/.agents/skills/dewaxguard/benchmarks/severity_regression.md
```

Add a row for every audit where M-27 was applied and record:
- Audit ID, finding ID, audit-graded severity, M-27-graded severity, agreement (Y/N), rationale-if-N

Promote to mandatory after 5 audits with ≥80% agreement. Until then, M-27 is OPTIONAL but recommended; findings without M-27 records may still ship under the standard matrix.

---

## Cross-language applicability

| Language | Example bug class M-27 applies to |
|---|---|
| EVM | Vault inflation attacks, oracle-stale-rate exploits where attacker must hold position, reward-rate cache staleness (this audit) |
| Solana | LP-token redemption rate staleness, share-price drift in lending markets |
| Aptos / Sui | FA-share redemption rate manipulation, vault accounting drift exploited by pre-positioned holders |
| C++ (rippled) | N/A typically — protocol-level rather than user-fund-extraction patterns |
| Stellar / Soroban | Soroban vault share-rate manipulation, archive-restore race conditions where attacker must own the resurrected entry |

The framework is language-agnostic because the inputs (per-unit extraction, time, delta, capital) are protocol-economic properties, not language features.
