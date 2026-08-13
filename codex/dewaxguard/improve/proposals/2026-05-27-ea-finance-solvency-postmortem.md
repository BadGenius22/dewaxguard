# Post-Audit Improvement Proposals — EA Finance Staking (2026-05-27)

> DewaxGuard v1.10+, EVM/Solidity, MasterChef-style single-asset staking on BSC.
> Findings: 1 High (H-01 claimRewards solvency, [POC-PASS] on live fork) + 1 Low + 10 Info.
> Key lesson: The pipeline correctly identified and verified a solvency-design failure, but
> the **severity framework has a hole** for bugs that fire under normal operation without an
> attacker. The user's pushback ("High requires instant drain + minimal capital") exposed the
> ambiguity. M-27 covers theft-attackers; this audit demonstrates a sibling class.

---

## Audit Summary (in-conversation, not persisted to MEMORY)

- 8 breadth agents, 3 converged on H-01 (economic, invariant, first-principles)
- Live BSC fork PoC: 4 tests, test_03 + test_04 mechanically violated K-INV2 (`balance ≥ totalStaked + totalFees`)
- Live state at audit: 8,803 wCC reward buffer / 198 wCC/day emission = **44-day runway**, then principal drains
- No attacker action required — bug self-triggers by elapsed time alone
- Severity calibration: H-01 graded High; defensible Medium under explicit documented admin-trust assumption

---

## Proposal 1: M-28 Solvency-Failure Severity Framework (NEW methodology)

**Root cause classification**: RC-METHOD — no existing methodology covers the severity decision for bugs that fire under normal operation due to a missing solvency / accounting invariant, where the harm is to OTHER USERS, not the actor calling the function.

**Gap**: M-27 (Realistic-Attacker Severity) explicitly excludes this class:
> "Skip M-27 IF: finding requires no attacker capital (e.g., reentrancy from anywhere) OR finding is flash-loanable OR finding is in a category where severity is fixed by mechanism alone."

The EA Finance H-01 satisfies NONE of M-27's apply conditions:
- Attacker capital is required to be a victim, not to attack
- Per-unit profit is computable but goes to *honest* claimers, not an attacker
- Mechanism alone doesn't fix severity — likelihood depends on admin top-up cadence

The severity-decision-tree question (a) — *"Can assets be DIRECTLY stolen, lost, or permanently locked by an attacker?"* — is ambiguous when the "attacker" is just normal protocol users acting normally and the harm lands on other users via shared-pot accounting.

**Proposed change** (write a new methodology file):

```
~/.agents/skills/dewaxguard/methodology/M28-solvency-failure-severity.md
```

**Skeleton** (~150 lines, under 300-line cap):

```markdown
# M-28: Solvency-Failure Severity Framework

> **Origin**: EA Finance audit (2026-05-27). H-01 (claimRewards has no solvency check)
> was a real bug that fires by time alone. Severity calibration was contested because
> the standard "attacker-driven" framing doesn't apply. M-27 explicitly excludes this
> class. This framework fills the gap.
>
> **Trigger**: Any finding where the harm fires under normal protocol operation given
> sufficient time, no attacker action required. Mechanically: if a PoC can be written
> that uses `skip(N days)` plus only normal user calls (no malicious sequencing, no
> reentrancy, no specific actor) and produces user fund loss, run M-28.
>
> **Yield**: Resolves the ambiguity in severity-decision-tree question (a) for the
> "no attacker, normal operation" class. Forces an explicit on-chain enforceability
> check before applying any admin-trust downgrade.

## When to apply

Apply M-28 IF (all true):
  finding.trigger == "elapsed time + normal user actions" (no attacker required)
  finding.harm.victim != finding.trigger.actor (harm lands on other users)
  finding.invariant == "shared-pot solvency" OR "share-pot deflation" OR
                       "accumulator-vs-balance drift"

Skip M-28 IF:
  An attacker can amplify or accelerate the failure beyond natural rate
  (then use M-27 instead, possibly chained with M-28 for baseline severity)

## STEP 0 — Verify "normal operation" trigger

The PoC must demonstrate harm using ONLY:
  - skip(T) for time advance
  - Normal user calls (deposit / withdraw / claim) with no specific ordering
  - No flash loans, no specific actor coordination, no MEV
  - No admin actions (no setters, no pauses)

If harm requires any of the above → not in scope, fall back to M-27 or standard matrix.

## STEP 1 — Compute time-to-failure (TTF)

TTF = time from current on-chain state until the invariant is mechanically violated
      under unchanged admin behavior.

Examples:
  - Reward pool: TTF = buffer_size / emission_rate
  - Oracle staleness: TTF = max_staleness_threshold − current_staleness
  - Paymaster: TTF = paymaster_balance / expected_gas_subsidy_rate

For EA Finance: TTF = 8,803 wCC / 198 wCC/day = **44 days**.

## STEP 2 — Classify TTF tier

| TTF | Tier | Default Likelihood |
|-----|------|-------------------|
| < 1 day | Imminent | **High** |
| 1-30 days | Near-term | **High** |
| 30-180 days | Medium-term | **Medium** |
| 180 days - 2 years | Long-term | **Medium** |
| > 2 years | Distant | **Low** |
| Unbounded (no natural failure mode) | n/a | M-28 doesn't apply |

EA Finance: 44 days → near-term → Likelihood: High under STEP 2.

## STEP 3 — Check on-chain enforcement of mitigation

Is there an on-chain mechanism that prevents the failure?

  (a) Solvency guard in the failing function (claim, withdraw, etc.) → applies even
      if admin abandons
  (b) Automatic emission halt when buffer < threshold → enforced
  (c) Permissionless top-up function (`fundRewardPool` anyone-callable) → enforced
  (d) Time-locked admin obligation (admin must top up by T or pool halts) → partial
  (e) NONE of the above; rely entirely on admin off-chain operational commitment

EA Finance: NONE. The contract has `withdrawRemainingRewards` (admin sweep) but no
solvency guard, no auto-halt, no permissionless top-up. → STEP 3 = (e).

## STEP 4 — Apply enforcement modifier

| STEP 3 result | Likelihood adjustment |
|---|---|
| (a) On-chain solvency guard | −2 tiers (likely refutes finding entirely) |
| (b) Auto-halt | −2 tiers |
| (c) Permissionless top-up | −1 tier (still fails if no one funds, but enabled) |
| (d) Time-locked obligation | −1 tier |
| (e) None | **no adjustment** (admin operational risk remains) |

EA Finance: (e) → Likelihood stays at High.

## STEP 5 — Apply admin-trust-assumption modifier

| Documented commitment | Modifier |
|---|---|
| Protocol docs explicitly state admin commits to ongoing top-ups at rate ≥ emission, AND defines remediation if they stop | −1 tier |
| Docs implicitly assume admin will top up (no explicit commitment) | no adjustment |
| Docs silent or admin is a single EOA | no adjustment (default operational risk) |

EA Finance: single EOA owner, no documented commitment → no adjustment.

## STEP 6 — Output severity

Combine Impact (from standard matrix) with Likelihood from STEP 2 + STEP 4 + STEP 5:

EA Finance H-01:
  Impact: High (principal lock confirmed mechanically)
  Likelihood (STEP 2): High (44-day TTF)
  Likelihood (STEP 4): no adjustment (no on-chain enforcement)
  Likelihood (STEP 5): no adjustment (no documented commitment)
  → Likelihood: High
  → Severity: **Critical** under standard matrix (Impact:High × Likelihood:High)

Compare to the audit's final High grade: M-28 would have produced Critical, not High.
The audit grade was tempered by the small absolute TVL ($408K) and the bug's slow rate.
This is a calibration question for the framework: should "small protocol TVL" be an
additional modifier? Open question, track for next M-28 instance.

## Tag in finding output

Every finding evaluated under M-28 emits:

```
**M-28 (Solvency-Failure Severity)**:
  TTF: 44 days (buffer 8,803 wCC / emission 198 wCC/day)
  Trigger: elapsed time + normal claim() calls (no attacker)
  On-chain enforcement: NONE (rely on EOA owner)
  Documented commitment: NONE (single EOA, no docs)
  Likelihood: High → Severity: Critical
```

## Cross-language applicability

| Language | Example bug class M-28 applies to |
|---|---|
| EVM | Reward pool insolvency, oracle staleness without halt, paymaster underfunding |
| Solana | Subsidy pool depletion, accumulator drift unchecked at claim |
| Aptos/Sui | Shared object solvency without balance check, FA accumulator drift |
| Stellar/Soroban | Vault rate accumulation without balance backing |

## Validation gate

Provisional until validated against 5 past findings of this class. Track in
`benchmarks/severity_regression.md`. Promote to MANDATORY at 5 audits, ≥80% agreement.
```

**Anti-bloat check**:
- Methodology over patterns: YES (encodes process, not specific bugs)
- Line budget: ~150 lines, under 300 cap
- Duplication: NO overlap with M-27 (mutually exclusive — M-27 attacker-driven, M-28 normal-operation)
- Marginal value: HIGH (closes systematic gap for solvency-design bugs)
- Overlap check: grep "solvency", "time-to-failure", "ongoing admin" in existing rules → no hits

---

## Proposal 2: Realism-filter tag extension — `ongoing-admin-obligation`

**Root cause classification**: RC-METHOD — the realism-filter taxonomy distinguishes `admin-trust` (admin acts maliciously) but has no tag for "admin must perform recurring operational task indefinitely."

**Gap**: A bug that depends on `admin keeps topping up forever` is NOT the same as `admin acts maliciously`. The former is operational risk; the latter is centralization risk. Currently both route to ADDITIONAL_LEADS (parked) under Code4rena/Sherlock platform defaults, which under-grades operational-dependency bugs.

**Proposed change** (extend `rules/realism-filter.md`):

Add to the filter values table:

```markdown
| `ongoing-admin-obligation` | Trigger fires under normal operation IF admin
  fails to perform a recurring task X (top-up, oracle update, parameter
  refresh) within window T | **Keep in main report at base severity**; do
  NOT apply the admin-trust −1 modifier. Reasoning: failing to act ≠ acting
  maliciously. Apply M-28 to derive likelihood. |
```

Add to the decision tree (between current steps 3 and 4):

```markdown
3.5. Does the trigger require admin to PERFORM a recurring operational task
     (not act maliciously, but reliably maintain a parameter or balance)?
     YES → tag = ongoing-admin-obligation → apply M-28 framework → keep at
           base severity. The downgrade-for-trusted-actor rule does NOT
           apply because the bug fires when admin FAILS to act, not when
           admin acts maliciously.
     NO  → continue to step 4 (semi-trusted-role)
```

**Anti-bloat check**:
- Extension (not new rule): ~10 lines added to existing file (under cap)
- Methodology: encodes a *class* of finding, not specific bugs
- Marginal value: prevents under-grading of solvency / staleness / paymaster classes
- Overlap: distinguishes from `admin-trust` cleanly (orthogonal direction of admin failure)

---

## Proposal 3: PoC scale-sweep requirement

**Root cause classification**: RC-DEPTH — `phase5-poc-execution.md` requires harm assertion and one fuzz variant, but does not require **parameter-scale sweep** when the finding's profit/harm function is bounded by a continuous parameter.

**Gap**: EA Finance test_02 (100k stake, 365d skip) returned inconclusive because pending reward (2,692) was less than buffer (8,803). The test_02 PoC was written, executed, and honestly gated — but a less-diligent author would have logged `[POC-FAIL]` and demoted the finding to CONTESTED.

The bug IS real. The PoC author correctly added test_03 (1M stake) and test_04 (3×1.5M, 730d) which both confirmed K-INV2 violation. The methodology should mandate this scaling.

**Proposed change** (extend `rules/fork-poc-execution.md`):

Add a new section after "Impact Premise Verification":

```markdown
## Parameter Scale Sweep (MANDATORY for bounded-extraction bugs)

If the finding's harm function is bounded by a continuous parameter (stake size,
time elapsed, share fraction, debt amount, price drift, etc.), the PoC MUST
include AT LEAST 2 parameter scales:

1. **Smallest realistic scale**: parameter values typical for a retail user at
   the protocol's expected TVL band (from design_context.md `expected_TVL_band`)
2. **Largest realistic scale**: parameter values that demonstrate the harm
   crossing the meaningful-loss threshold (per M-27 STEP 2)

If the smallest-scale PoC is inconclusive (`pending < threshold`, `drift < epsilon`,
etc.), the test MUST gate honestly (return early with explanation) AND a
larger-scale companion test MUST be added. Inconclusive-at-small-scale is NOT
a `[POC-FAIL]` verdict — it is `[POC-PASS at large scale, scale-dependent at
small scale]`.

Example tag in verify_*.md:

  ### Execution Result
  - Smallest scale (100k, 365d): pending=2,692 < buffer=8,803 → inconclusive (test returned early)
  - Largest scale (1M, 365d): pending=20,136 > buffer=8,803 → K-INV2 violated, deficit 11,332 wCC
  - Verdict: [POC-PASS] at realistic-whale scale; [INCONCLUSIVE] at retail scale
  - Likelihood interpretation: scale-dependent — see M-28 STEP 2 for TTF analysis
```

**Anti-bloat check**:
- ~15 lines added to existing file (under cap)
- Encodes a process (parameter sweep), not specific bug shapes
- Marginal value: prevents false `[POC-FAIL]` on scale-dependent bugs
- Overlap: none — current rules require fuzz variant but fuzz uses `bound()` ranges, not deliberate small/large pair

---

## Anti-Pattern: User Heuristic Documentation

**Optional addition** — a paragraph in `rules/severity-decision-tree.md` documenting a
common auditor mental model that produces wrong answers:

```markdown
## Common Misconceptions

### "High severity requires instant drain with minimal capital"

This heuristic is a useful first filter for THEFT-class bugs but FAILS for:
- Solvency-design failures (no attacker; bug fires by time)
- Dilution attacks (slow extraction via pro-rata share)
- Accumulator drift (compounding harm with no triggering attacker)
- Liveness failures (no theft, but core function locks)

When evaluating a finding, ask the matrix questions DIRECTLY rather than checking
against the "instant drain" heuristic:
  1. Can the bug cause direct fund loss or permanent lock? (Impact)
  2. Under what realistic conditions does it fire? (Likelihood)

If the answer to (1) is YES and the answer to (2) is "any 44-day gap in admin
top-ups," the bug is High under the matrix regardless of whether it matches the
"instant drain" mental model.
```

**Anti-bloat check**:
- ~15 lines added to existing file
- Documents an anti-pattern (common wrong reasoning), not a methodology
- Marginal value: helps human reviewers and the bug-validator agent resist common-but-incorrect intuitions

---

## Implementation Order (if approved)

1. **First**: Proposal 1 (M-28). It's the load-bearing change. The other two depend on it.
2. **Second**: Proposal 2 (realism-filter extension). Small surgical change, low risk.
3. **Third**: Proposal 3 (PoC scale sweep). Process change to verification protocol.
4. **Optional**: Anti-pattern doc paragraph.

## Validation Plan

- Re-run severity calibration on Ledgity Yield H-01 (the M-27 origin case) under M-28:
  expected outcome — M-28 does not apply (Ledgity is capital-amplifiable, M-27 territory)
- Re-run severity calibration on EA Finance H-01 under M-28: expected outcome — Critical (per STEP 6)
- Apply M-28 to next 3 audits with solvency / staleness / paymaster components; record agreement vs. shipped grades
- Promote M-28 to MANDATORY after 5 audits with ≥80% agreement

## DECISION CHECKLIST (for user review)

- [ ] Approve Proposal 1 (M-28)
- [ ] Approve Proposal 2 (realism-filter ongoing-admin-obligation tag)
- [ ] Approve Proposal 3 (PoC scale-sweep requirement)
- [ ] Approve optional anti-pattern paragraph
- [ ] Defer (collect strikes 2 and 3 before any change)
- [ ] Reject (rationale: __________________)

Per 3-strike rule, the conservative default is **DEFER** until 2 more audits surface
the same gaps. Approve early only if the user's domain knowledge confirms these gaps
are recurring across past audits not yet captured in MEMORY.md.
