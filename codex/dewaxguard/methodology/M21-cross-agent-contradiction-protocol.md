---
id: M-21
name: cross-agent-contradiction-protocol
trigger_type: process
trigger_event: "merge step of a multi-reviewer pipeline yields contradictory verdicts or a lone-flagger on the same code surface"
trigger_languages: [all]
applies_to_protocol_types: [any]
---

# M-21: Cross-Agent Contradiction Protocol with Mandatory Source-Code Arbitration

**Origin**: XRPL Sherlock April 2026, Domain 17 / Domain 18 — surfaced when two breadth agents disagreed on the same code surface (one REFUTED based on a partial code read; another CONFIRMED based on a fuller code read). The merge orchestrator's instinct was to defer to majority vote, which would have produced a wrong refutation. Source-code direct arbitration overrode the agent verdicts and produced **L-35 — a Low submittable finding that all 7 other breadth agents missed**. Without this protocol, L-35 would have been silently dropped at the merge step.

**Relationship to M-18**: M-18 (Account-Lifecycle Cleanup-Switch Completeness Matrix) introduced cross-agent contradiction handling as a Phase-3 sub-rule for one specific matrix domain. M-21 generalizes that sub-rule into a stand-alone, always-on merge-step protocol that applies to every multi-reviewer pipeline regardless of audit domain.

**One-line**: When two reviewers (LLM agents, human peers, formal verifier vs dynamic analyzer) reach contradictory verdicts on the same code surface, the merge step MUST arbitrate by reading the source code directly with both reviewers' citations side-by-side — never by majority vote, never by trusting either citation alone, never by deferring to the higher-confidence agent.

## Trigger

Apply whenever a multi-reviewer pipeline produces contradictory verdicts on the same artifact, including:

- Multiple LLM breadth agents in an audit pipeline (8-agent breadth, peer review, /dewaxguard thorough).
- Human peer reviewers disagreeing on a single PR / finding's validity.
- Static analyzer (Slither, Semgrep) flagging vs dynamic analyzer (Foundry fuzz, Echidna) refuting.
- Formal verifier (Certora, Move Prover) certifying vs LLM agent flagging.
- Symbolic executor (Mythril, KLEE) reachability vs concrete-trace-only refutation.

The trigger condition: **at least one reviewer says BUG and at least one reviewer says NO BUG**, and both cite the SAME code location or the SAME root-cause class.

**Lone-flagger extension**: also trigger when 1 reviewer flags and the other N-1 reviewers are silent on the cell (no explicit refutation but no confirmation either). Treat as implicit-disagreement; majority-of-silence is the most common failure mode.

## The four-step protocol

### Step 1 — Catalog the disagreement structurally

For every cross-reviewer disagreement, record in a structured table:

| Field | Reviewer A (BUG) | Reviewer B (NO BUG) |
|---|---|---|
| Verdict | CONFIRMED / FOUND | REFUTED / NO_FINDING |
| Cited location | file:line range | file:line range |
| Cited code excerpt | (verbatim) | (verbatim) |
| Severity (if any) | High / Medium / Low | N/A |
| Reasoning chain | (1-3 sentences) | (1-3 sentences) |
| Confidence (self-reported) | 0.0–1.0 | 0.0–1.0 |

If the cited line ranges DIFFER → first arbitration check: *did one reviewer read more of the code than the other?*

### Step 2 — Open the source code directly; never trust either citation alone

The orchestrator (or human merge reviewer) MUST open the source file at the maximum union of both line ranges (Reviewer A's range ∪ Reviewer B's range, plus ±20 lines for context). Read the actual current code — not Reviewer A's excerpt, not Reviewer B's excerpt.

This step exists because agent excerpts can be:
- **Truncated** — agent only quoted the lines that supported its verdict.
- **Stale** — agent quoted from a cached or older version of the file.
- **Reformatted** — agent paraphrased rather than copying verbatim.
- **Hallucinated** — agent quoted lines that don't exist as written.

Any of these failure modes invalidates the agent's reasoning chain regardless of self-reported confidence.

### Step 3 — Apply the three arbitration verdicts

After direct source read, classify the disagreement as one of:

- **A-CORRECT, B-WRONG-SCOPE**: Reviewer B inspected too narrow a range and missed the buggy lines that Reviewer A flagged. Verdict: CONFIRMED. Record the scope-coverage gap as a meta-finding (improves future-audit reviewer prompting).
- **B-CORRECT, A-FALSE-POSITIVE**: Reviewer A's bug claim is invalidated by code that Reviewer A did not include in its excerpt (defensive layer, preflight check, downstream validation). Verdict: REFUTED. Record A's reasoning failure as a meta-finding.
- **NEITHER-CORRECT (both wrong)**: Source-code arbitration reveals a third interpretation neither reviewer reached. Verdict: NEW (different root cause). Record as a fresh finding under the orchestrator's name; both reviewers were partial.

### Step 4 — Write the arbitration record back to the audit trail

For every arbitration:
- Document the disagreement (Step 1 table).
- Document the source-read (Step 2).
- Document the verdict (Step 3) with explicit override of any majority vote.
- For OVERTURN cases (A-CORRECT or NEITHER-CORRECT against majority), explicitly flag the lone-flagger / minority-vote outcome — these are the highest-value findings in the entire pipeline because they survive against attention saturation.

## Cross-domain mapping

This protocol generalizes to any multi-reviewer code-review pipeline:

### LLM multi-agent audit pipelines (validated origin)

- **Pattern**: 8 parallel breadth agents, each surfacing candidate findings; merge orchestrator deduplicates.
- **Failure mode without M-21**: lone-flagger findings get dropped because "7 agents disagreed". Majority vote silently kills the unique perspective.
- **M-21 fix**: every lone-flagger triggers source-code arbitration before refutation.

### Peer code review (human)

- **Pattern**: PR with 2 reviewers; one says LGTM, other says CHANGES REQUESTED.
- **Failure mode without M-21**: PR author argues with the dissenting reviewer; team votes. The dissenting reviewer's source citation may be the only correct read.
- **M-21 fix**: a third reviewer opens the file at the disputed range and reads independently. No vote.

### Formal verification + dynamic analysis

- **Pattern**: Certora certifies a Solidity contract; Foundry fuzz finds a counterexample.
- **Failure mode without M-21**: defer to formal verifier ("it's mathematically proven correct"). But the spec may be wrong, or the fuzz harness exposed a behavior not covered by the spec.
- **M-21 fix**: read the source + spec + counterexample together. Arbitrate at source. Spec bugs are common.

### Symbolic execution + concrete trace

- **Pattern**: Mythril reports reachability of a vulnerable path; manual concrete-trace says path is unreachable due to inline-assembly check Mythril didn't model.
- **Failure mode without M-21**: trust whichever tool you used most recently.
- **M-21 fix**: open the assembly block. Determine empirically whether the check covers the reachability claim.

### Static analyzer + LLM analyzer

- **Pattern**: Slither flags an integer-overflow; LLM agent says "the variable is bounded by an upstream require".
- **Failure mode without M-21**: trust the LLM (it has more context). But the LLM may have hallucinated the require.
- **M-21 fix**: grep for the require. If absent, Slither was right.

## The cross-agent contradiction failure modes

When the protocol is NOT applied, the following failure modes recur:

1. **Lone-flagger silently dropped** — the unique-perspective agent's finding is killed by majority vote without source check. Highest-value findings die here.
2. **Majority converges on a wrong refutation** — multiple agents copy each other's misreading; the lone correct reviewer is dismissed.
3. **Higher-confidence-wins bias** — the merger trusts the agent with higher self-reported confidence; but confidence calibration varies wildly between agents.
4. **Citation-truncation pollution** — both agents quote different excerpts of the same function; the merger compares excerpts (not source) and reaches a wrong synthesis.
5. **Stale-cache divergence** — one agent read the post-fix code, another read the pre-fix code; the merger doesn't notice because both cite the same file path.

The protocol blocks all 5 by mandating direct source-read at the merge step.

## Validated finding

**XRPL April 2026, Domain 17 (XLS-0075 Permission Delegation × cross-feature compositions)** — 8 agents ran breadth on the new granular-permission system. One agent (Vector Scan) flagged a specific cross-feature delegation grief vector. **The other 7 agents did not reach the cell to refute or confirm**. The merge orchestrator's instinct: drop the lone-flagger as 1-of-8 noise.

Application of M-21 produced:

- **Step 1**: catalog showed only one agent surfaced; technically not a "contradiction" but a "lone-flag" — same protocol applies (verify against source rather than majority-vote).
- **Step 2**: source-code arbitration — orchestrator read the relevant transactor (whole file, ~100 LoC), the relevant tx-type schema (5 sibling tx-types side-by-side), and the prior-finding catalog (#6890 + 5 other related issues).
- **Step 3**: A-CORRECT verdict — the lone agent's claim was technically accurate; the other 7 agents had not reached the cell.
- **Step 4**: explicit OVERTURN of the implicit majority (silent non-coverage = implicit refutation in 8-agent voting). Recorded as a Submittable Low (L-35) because:
  - All technical claims confirmed at source.
  - No other agent surfaced contradictory evidence.
  - Prior-finding catalog dedup (M-10) cleared it as not-known-issue.
  - Connected to a previously-uncovered reward-pool feature (M-04 framing).

**L-35 was the third reward-pool hit (3 of 5 pools)** — without M-21, the audit would have stopped at 2 of 5 pools.

**XRPL April 2026, Domain 18** — independently validated again. Two agents disagreed on whether a new code block in an authorize transactor blocked holder cleanup when residue exists. One agent (Vector Scan) inspected only the entry-point lines and REFUTED; another agent (Economic Security) inspected the full new block and CONFIRMED. Source-code arbitration sided with the CONFIRMING agent; the REFUTING agent's narrow scope was the failure mode. Verdict: PARTIAL CONFIRMED Low (HOLD per trust-model gating).

## Checklist

When merging multi-reviewer audit outputs:

```
[ ] List every cross-reviewer disagreement (BUG vs NO BUG on same surface)
[ ] List every lone-flagger (1 reviewer flags, others silent — treat as implicit-disagreement)
[ ] For each: build the Step 1 table (verdicts, cited ranges, excerpts, reasoning, confidence)
[ ] For each: open source file at union of ranges + ±20 lines for context
[ ] Read source independently — DO NOT compare reviewer excerpts against each other
[ ] Classify as A-CORRECT / B-CORRECT / NEITHER-CORRECT
[ ] Write arbitration record to audit trail (override majority/confidence explicitly when applicable)
[ ] For OVERTURN cases: record as meta-finding (improves future reviewer prompting)
[ ] For lone-flagger CONFIRMED outcomes: explicitly note "would have been silently dropped without M-21"
```

## Anti-patterns

- **Don't trust self-reported confidence**. Reviewer confidence calibration varies; high-confidence reviewers can be wrong, low-confidence reviewers can be right. Source-code arbitration is platform-neutral.
- **Don't compare reviewer excerpts against each other** as a substitute for source-read. Both excerpts may be partial; the synthesis is still wrong.
- **Don't apply majority vote**. 7-of-8 against 1 is a strong signal in many domains; in code review it can be precisely WRONG when the lone reviewer reads more of the file. Validated against L-35: 1-of-8 lone-flag became a Submittable.
- **Don't skip lone-flag arbitration to save time**. The marginal cost of source-read is ~5 minutes per disagreement; the marginal value is preserving high-uniqueness findings that majority vote silently kills. Time-savings here destroys yield.
- **Don't escalate disputes to the higher-context reviewer without source-read**. Even the highest-context reviewer can hallucinate or miss lines; the source is the only ground truth.

## Related methodology

- **M-07** (post-finding sweep) — when arbitration produces a CONFIRMED, sweep all callers / sibling transactors for the same pattern.
- **M-10** (prior-audit dedup) — every CONFIRMED arbitration outcome must pass the dedup filter before submission (especially important for lone-flag findings that nobody else surfaced — verify they're not in the known-issue catalog).
- **M-18** (account-lifecycle cleanup-switch matrix) — first introduced cross-agent contradiction handling as a Phase-3 sub-rule for one matrix domain. M-21 generalizes it into an always-on merge-step protocol independent of any matrix.
- **M-20 Step 3** (multi-agent convergence on Informational properties) — the inverse case: when MULTIPLE agents converge on the same Informational property, treat the convergence itself as evidence of the property's reality.

## ROI

**THE highest-leverage methodology in the v1.5.0 release.** XRPL April 2026: this protocol alone produced L-35, the **3rd reward-pool hit** that all 7 other breadth agents missed. Without it, the audit would have shipped 2 of 5 pools. Cost: ~5 minutes per arbitration; yield: one Submittable Low and one PARTIAL Low across two domains. Highest yield in pipelines with ≥3 parallel reviewers; near-zero cost in single-reviewer pipelines (no arbitration to perform). Always-applicable when running multi-reviewer audits.
