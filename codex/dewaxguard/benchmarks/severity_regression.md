# Severity Regression Benchmark

> **Purpose**: Pin specific real findings to a target severity. When methodology changes (especially M-27, the realism filter, the severity matrix, or the inventory-router), re-grade these findings and assert the output matches the pinned severity. A mismatch = regression. The benchmark is **process-anchored**: it tests that the pipeline arrives at the right grade via the right reasoning, not just that it outputs the right letter.
>
> **How this differs from `manifest.json`**: that file pins *whether* a class of bug is detected. This file pins *what severity* dewaxguard assigns to bugs whose detection is already settled — i.e., it guards against severity drift after methodology edits.
>
> **When to run**: after any edit to `methodology/M-27*`, `methodology/M-14*`, `rules/severity-matrix.md`, `rules/realism-filter.md`, `rules/severity-decision-tree.md`, or `scripts/severity_router.py`. Also part of `/dewaxguard benchmark` and `/dewaxguard improve`.
>
> **Pass criterion**: for each pinned finding, the pipeline's final severity must equal `expected_severity`. The pipeline must also produce reasoning that touches each `must_reference_methodology` ID below — otherwise the right answer was reached for the wrong reason and the test is a soft-fail (warn, don't block).

---

## Schema

Each entry uses this structure:

```yaml
- id: <unique slug>
  origin_audit: <audit name + date>
  origin_report_path: <local path or URL to the audit report this finding came from>
  finding_title: <short description>
  short_description: <one-sentence mechanism>
  original_grade: <severity the audit shipped>
  expected_severity: <severity dewaxguard MUST produce>
  must_reference_methodology: [<methodology IDs that the reasoning must cite>]
  inputs:
    flash_loanable: <yes|no>
    capital_required_usd: <integer>
    realistic_profit_usd: <integer>
    realistic_loss_per_victim_usd: <integer>
    actor_profile: <whale|mid-tier|retail|mixed>
    expected_tvl_band: <range string>
    trigger_frequency: <one-line cadence>
  rationale: |
    <2-4 sentence explanation of why this is the correct grade. This is the human-readable
    reasoning the regression check uses to judge whether the pipeline arrived at the right
    severity via the right path.>
  poc_evidence: |
    <one-line summary + path to the executed PoC, if any>
```

---

## Pinned Findings

### LEDGITY-H01 — WrappedLToken cached-APR race

```yaml
- id: LEDGITY-H01
  origin_audit: Ledgity Yield Sonic deployment (2026-05-26)
  origin_report_path: ~/Documents/Work/Audit/tvl-scanner-targets/2026-05-26-ledgity-yield/AUDIT_REPORT.md
  finding_title: WrappedLToken cached-APR refresh compounds old rate after admin APR cut
  short_description: |
    WrappedLToken caches the LToken APR. On every interaction it compares the cache
    against the current LToken APR in incompatible units (raw UD7x3 vs base-100 RAY), so
    the cached-rate guard never trips. After an admin lowers the LToken APR the wrapper
    keeps compounding at the OLD higher APR across the elapsed window until the next
    write touches updateRateCheckpoint. A pre-positioned attacker unwraps first and pays
    out at the inflated exchange rate; remaining wrappers absorb the shortfall.
  original_grade: High
  expected_severity: Medium
  must_reference_methodology: [M-27, severity-matrix, realism-filter]
  inputs:
    flash_loanable: no
    capital_required_usd: 1_000_000
    realistic_profit_usd: 301
    realistic_loss_per_victim_usd: 301
    actor_profile: mid-tier
    expected_tvl_band: "$1M-$10M (early Sonic deployment)"
    trigger_frequency: "APR cut: discretionary admin (Ledgity multisig), not on a fixed schedule"
  rationale: |
    PoC against the live Sonic mainnet fork at $10M TVL with a 9% to 4.5% APR cut and a
    1-day reaction window produced $301 attacker profit and $301 aggregate victim
    shortfall (mass-conserving). The attack is NOT flash-loanable because the wrap path
    refreshes the same cache that unwrap reads, so any same-tx setup neutralizes the
    profit. An attacker therefore needs $1M+ pre-positioned capital plus front-running
    access to the admin's APR-cut tx; M-27 STEP 4 places this in the mid-tier capital
    class on a single-shot opportunity. Impact is Low (sub-meaningful dollar magnitude
    on the protocol's stated actor profile) and Likelihood is Low (whale-only capital
    plus discretionary trigger). Severity matrix: Impact Low × Likelihood Low = Low,
    upgraded to Medium because the loss is to other depositors (cross-user) and not just
    the attacker's own funds. High is wrong because the audit's grade implicitly assumes
    flash-loan-grade likelihood without verifying it.
  poc_evidence: |
    4/4 PASS at ~/Documents/Work/Audit/tvl-scanner-targets/2026-05-26-ledgity-yield/poc_h01/test/H01_AprRace_SonicFork.t.sol
    (Sonic chainId 146, real LUSDC/WLUSDC pool, vm.etch for wrapper proxy, real USDC
    funded personas). test_H01_step4 asserts attacker_profit approxEq victim_shortfall
    within 10 wei tolerance.
```

---

## Adding new pinned findings

When a future audit produces another severity-corrected finding (audit shipped grade X, post-mortem said grade Y), add it here with full schema. The benchmark is meant to grow — each entry encodes a calibration data point that defends against future regressions.

**Inclusion bar**:
- The original audit's grade and the correct grade must differ — otherwise there's nothing to regress against.
- A PoC (or rigorous code-trace if no fork environment available) must back the inputs.
- The `must_reference_methodology` list must include at least one specific methodology ID — entries that just say "common sense" are not useful as regression anchors.

**Anti-pattern**: do NOT pin findings whose severity was correctly assigned by the original audit. Those are detection benchmarks, not severity benchmarks; they belong in `manifest.json`.

---

## Companion: how the regression runner uses this file

A future `/dewaxguard benchmark severity` command (or the `/dewaxguard improve` flow) does the following per entry:

1. Feed `short_description` + `inputs` block to the severity router as if they came from a fresh finding.
2. Read the router's output severity and its reasoning trace.
3. Assert `output_severity == expected_severity` — hard fail on mismatch.
4. Soft-assert that the reasoning trace contains each ID in `must_reference_methodology` — warn if not.
5. Print a compact diff: `LEDGITY-H01 expected=Medium got=High [reasoning: missing M-27]` so methodology drift is identifiable in CI logs.
