# Finding Validation

Every finding passes four sequential gates. Fail any gate → **rejected** or **demoted** to lead. Later gates are not evaluated for failed findings.

> This is dewaxguard's end-of-pipeline validator (Phase 5d) — it is the inline equivalent of the standalone bug-validator's Reality Gate, so running the pipeline means you do NOT need the separate skill. A single REJECT/DEMOTE on any gate is final: **legitimacy ≠ submittability** — never re-promote a gated finding because it "feels like a real defect." (Gate calibration: the gates below were hardened from real contest rejections where a polished, technically-true finding was rejected for documented behavior, a fabricated enabler, or harm only to a voluntary participant.)

## Gate 1 — Refutation

Construct the strongest argument that the finding is wrong. Find the guard, check, or constraint that kills the attack — quote the exact line and trace how it blocks the claimed step.

- Concrete refutation (specific guard blocks exact claimed step) → **REJECTED** (or **DEMOTE** if code smell remains)
- **By-design / spec refutation** (grep the contract's OWN source NatSpec + spec/whitepaper, not just `docs-intent-map.md`): if the source documents the exact behavior → **REJECTED**. This includes an explicit `"Reverts if X"` / `"Reverts when Y"` (propagating that revert is *specified*, not a broken guarantee — even when a different nearby doc like "skips a failed take" tempts a "design clearly meant to handle this too" narrative), and a parameter whose harmful effect IS its documented purpose (a kill even at an *extreme* value and even with no bound/warning — "no guardrail/validation/warning on a parameter whose effect is documented" is a documentation suggestion, not a bug).
- Speculative refutation ("probably wouldn't happen") → **clears**, continue

## Gate 2 — Reachability

Prove the vulnerable state exists in a live deployment.

- Structurally impossible (enforced invariant prevents it) → **REJECTED**
- **Enabler verification (anti-fabrication)**: list every precondition the finding leans on (actors, settable params, external state) and verify EACH against the code (cite file:line). A precondition that is actually **caller-supplied** (the "victim" controls it themselves — e.g. a function-argument fee %, a self-chosen amount/budget), or that does not exist as claimed (no such role/param/state), is not an attacker enabler → **REJECTED**. Never credit an enabler ("a fee-setter raises X", "an admin can Y") you have not confirmed in the source.
- Requires privileged actions outside normal operation → **DEMOTE**
- Achievable through normal usage or common token behaviors → **clears**, continue

## Gate 3 — Trigger

Prove an unprivileged actor executes the attack.

- Only trusted roles can trigger → **DEMOTE**
- Costs exceed extraction → **REJECTED**
- Unprivileged actor triggers profitably → **clears**, continue

## Gate 4 — Impact

Prove material harm to an identifiable victim.

- Self-harm only → **REJECTED**
- **Opted-in disclosed risk (no involuntary victim)**: if the harm comes from a parameter/property in the **immutable, on-chain-visible identity** of a permissionlessly-created market/pool/vault that the affected party **voluntarily entered**, there is no involuntary victim — it is accepted, disclosed risk (Morpho-Blue-style isolated-market ruling) → **REJECTED**. A real loss to a voluntary participant in disclosed immutable terms does NOT survive just because the loss is real. *Exception:* the party can be forced/migrated in without consent, the harmful param can change AFTER entry, or third parties who never opted in are hit.
- Dust-level, no compounding → **DEMOTE**
- Material loss to identifiable victim → **CONFIRMED**

## Confidence

Start at **100**, deduct: partial attack path **-20**, bounded non-compounding impact **-15**, requires specific (but achievable) state **-10**. Confidence ≥ 80 gets description + fix. Below 80 gets description only.

## Safe patterns (do not flag)

- `unchecked` in 0.8+ (but verify the reasoning is correct)
- Explicit narrowing casts in 0.8+ (reverts on overflow)
- MINIMUM_LIQUIDITY burn on first deposit
- SafeERC20 (`safeTransfer`/`safeTransferFrom`)
- `nonReentrant` (only flag cross-contract attacks)
- Two-step admin transfer
- Consistent protocol-favoring rounding unless compounding or zero-rounding

## Lead promotion

Before finalizing leads, promote where warranted:

- **Cross-contract echo.** Same root cause confirmed as FINDING in one contract → promote in every contract where the identical pattern appears.
- **Multi-agent convergence.** 2+ agents flagged same area, lead was demoted (not rejected) → promote to FINDING at confidence 75.
- **Partial-path completion.** Only weakness is incomplete trace but path is reachable and unguarded → promote to FINDING at confidence 75, description only.

## Leads

High-signal trails for manual investigation. No confidence score, no fix — title, code smells, and what remains unverified.

## Do Not Report

Linter/compiler issues, gas micro-opts, naming, NatSpec. Admin privileges by design. Missing events. Centralization without exploit path. Implausible preconditions (but fee-on-transfer, rebasing, blacklisting ARE plausible for contracts accepting arbitrary tokens). Behavior the source NatSpec documents as intended (incl. `"Reverts if X"` and a parameter's documented effect). Inconvenience/surprise/asymmetry between intentionally-different siblings (exact-in vs exact-out, atomic vs two-step permit) with no fund loss. Documented-revert DoS with atomic rollback and no loss. Harm only to voluntary participants in an immutable, disclosed, permissionlessly-created market.
