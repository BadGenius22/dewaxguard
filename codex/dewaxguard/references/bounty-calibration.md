# Bug Bounty / Contest Calibration (applies to ALL audit + bounty work, every project)

## The filter — apply this first, to every candidate finding

**A bounty-worthy bug must be one of: (a) exploitable, (b) profitable for the attacker, or (c) causing
serious damage to the protocol. Those are the bugs worth chasing. Focus on them.**

Everything below is calibration for findings that already pass this filter. If a candidate passes none of
the three, it is at most an Informational note — do not spend a verification pass, a PoC, or an escalation
argument on it, and do not pad a report with it. Say what it is, in one line, and move on.

Corollaries that follow directly:
- "Real defect" ≠ "bounty-worthy". A genuine code flaw with no exploit path, no attacker profit, and no
  protocol damage is a code-quality note, not a submission.
- Test (b) with a **measured number** from a zero-capital start, not an assertion.
- Test (c) against the protocol's own solvency/liveness invariants, not against intuition — and if the
  damage chain does not reproduce mechanically, drop the claim rather than argue it.

Base rates from the Sherlock Bountiability Benchmark (TestMachine.ai, published 2026; dataset =
13,251 submissions across 24 Sherlock contests). Use these as priors **before** assigning severity or
deciding to submit. The source article was user-supplied; no stable public URL was captured, so
revalidate these figures before using them as current external evidence.

## The base rates

| Fact | Number |
|---|---|
| Labeled submissions that are **invalid / info / low** | **79%** |
| Paid submissions that are **duplicates** of another paid report | **88%** (2,510 paid → 303 unique bugs) |
| Typical monthly bountiable share | **17–29%** (one outlier contest hit 42%) |
| Bugs found by exactly one auditor ("singletons") | 84 of 303 |
| Language mix of validated bugs | 259 Solidity / 41 Go / 3 Rust |

## The rules these imply

1. **"Is it a real defect?" is the wrong bar. "Does it map to a payable impact row?" is the bar.**
   Check the target program's *actual* severity table before assigning severity — never a remembered or
   assumed one, and never invent a plausible-sounding row (e.g. "theft of protocol treasury") that the
   program does not list. If a finding maps to no row, say so plainly; a real bug that fits no row is
   unpayable, and that is a legitimate outcome to report.

2. **A unique finding skews LOWER, not higher.** Singletons are 71% medium / 29% high, versus 60/40 for
   crowd-found bugs. The instinct "nobody else found this, so it must be big" is backwards and must be
   actively resisted. Being the only finder is evidence of subtlety, not of severity.

3. **Unique findings get contested ~1.6× more** (45% escalation-contested vs 28%). So a singleton needs a
   *stronger* mechanical proof than an obvious bug — executed PoC, measured numbers, stated bounds.
   Novelty raises the evidence bar; it does not substitute for evidence.

4. **Assume duplication by default.** 88% of paid reports duplicate another. Undirected "find all bugs"
   sweeps converge on the same recognizable patterns. Differentiated work comes from asking a question the
   crowd is not asking — e.g. enumerate the **value-outflow sites and who can reach each one**, rather than
   sweeping vulnerability classes. Organise by *protocol mechanic*, not by *bug taxonomy*.

5. **Find, Validate, and Confirm/Refute are three different skills — score them separately.**
   - *Find*: surface the issue from the code alone.
   - *Validate*: trace the claim through code and reproduce the judge's reasoning.
   - *Confirm/Refute*: reach the correct disposition on valid AND invalid claims.
   Strength in one does not imply strength in another. **A finding already in your report can still be
   wrong about its own reachability, trigger, or actor** — that is a validation failure, not a find
   failure, and it is the most common self-inflicted error. Re-validate the *precondition and the payout
   leg separately*: a chain whose entry path is privileged may still have an unprivileged payout.

6. **Measure attacker profit; never assert it.** Report profit as a measured delta from a zero-capital
   start, with the bound stated (per-account? per-block? global?). "Attacker profits" without a number is
   the signature of an unbountiable report.

7. **Report the refutations too.** Recording what was tested and disproven — with the evidence — is what
   separates a validation pass from a plausible narrative, and it prevents re-deriving dead ends later.

## Interaction with the auto-invalidator rule

These calibration priors apply *after* the known auto-invalidators (see the compromised-private-key rule in
applicable `AGENTS.md` or target rules). Order of operations: **auto-invalidate → map to the program's real impact table → apply
singleton/duplication priors → assign severity → demand proof proportional to novelty.**
