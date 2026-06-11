---
id: M-22
name: hypothesis-pre-declaration
trigger_type: process
trigger_event: "audit planning with >=3 domains or >=1500 nSLoC scope (pre-declare falsifiable hypotheses before breadth)"
trigger_languages: [all]
applies_to_protocol_types: [any]
---

# M-22 — Hypothesis Pre-Declaration with Falsifiable Verdict Tracking

**Origin**: Monetrix audit (April 2026), Code4rena. Domains 11/12/13/14 ran with pre-declared falsifiable hypotheses → all converged in 1-2 breadth agents instead of 8, with mechanical verdicts (CONFIRMED / REFUTED / PARTIAL). Without pre-declaration, agents do open-ended discovery and produce verbose-but-shallow output.

**Highest-leverage benefit**: each domain enters Phase 3 (breadth) with a *closed* set of falsifiable claims. Agents verdict against the claims instead of "looking for bugs". This produces sharper REFUTED entries (which become R-N manifest deltas) and prevents wasted depth on already-refuted angles.

---

## When to apply

| Audit shape | Apply M-22? |
|-------------|-------------|
| ≥3 domains | YES — pre-declare per-domain hypotheses |
| ≥1500 nSLoC scope | YES |
| Single-contract, <500 nSLoC | NO — open-ended discovery is fine; pre-declaration overhead exceeds yield |
| Cross-domain synthesis pass (e.g. chain composition) | YES — pre-declare specific candidate compositions, not just "look for chains" |
| Iteration on prior audit | YES — pre-declared hypotheses anchor against prior R-N refutations |

---

## Process

### Step 1: Per-domain hypothesis pre-declaration

For each domain in `DEEP_DIVE_PLAN.md`, declare 3-7 hypotheses BEFORE spawning breadth agents. Each entry:

| Field | Description |
|-------|-------------|
| **ID** | `H{domain}.{n}` (e.g. H6.1, H12.4) |
| **Statement** | A FALSIFIABLE claim — "[function X] in [state Y] produces [outcome Z] when [actor A] does [action B]" |
| **Predicted ceiling severity** | Critical / High / Medium / Low — based on impact × likelihood, before verdict |
| **Why pre-declared** | What signal (code pattern, manifest cross-feed, prior-audit precedent) raised this hypothesis |
| **Verdict template** | CONFIRMED / PARTIAL / REFUTED — agent fills this at breadth completion |

### Step 2: Falsifiability check

Before locking the plan, verify each hypothesis:

- ✓ **Falsifiable**: a concrete code trace can prove it FALSE (not "audit X for safety")
- ✓ **Specific**: names the function, state condition, actor, and outcome
- ✓ **Bounded**: predicts a severity ceiling (so judges can validate calibration)
- ✗ Reject: "Investigate the foo system" (too open-ended)
- ✗ Reject: "Function X has a bug" (no specific failure mode named)

### Step 3: Agent prompt enrichment

In Phase 3 (breadth) and Phase 4b (depth), agents receive the pre-declared hypotheses for their assigned scope. Agent prompt template:

```
HYPOTHESES YOU OWN: {list of H{domain}.{n} entries}

For EACH hypothesis, produce:
- Verdict: CONFIRMED / PARTIAL / REFUTED
- Mechanical evidence: code trace, function-by-function table, or counterexample
- If CONFIRMED: severity vs predicted ceiling
- If REFUTED: the specific defense mechanism (file:line) that defeats the hypothesis

DO NOT do open-ended discovery. Verdict the hypotheses first. Open-ended findings are FALLBACK only after all hypotheses are verdicted.
```

### Step 4: Verdict consolidation

After breadth completes, consolidate into per-domain REPORT.md:

```
## Hypothesis verdict table

| ID | Title | Verdict | Severity (vs predicted) | Submittable? |
|----|-------|---------|------------------------|--------------|
| H{n}.1 | ... | REFUTED | n/a | No (R-N to manifest) |
| H{n}.2 | ... | CONFIRMED | Medium (matched ceiling) | Yes (M-N) |
| H{n}.3 | ... | PARTIAL | Low (downgraded from Medium) | Maybe (QA candidate) |
```

Refutations become `R-N` manifest entries; confirmed findings advance to Phase 5.

---

## Why this works (the underlying mechanic)

**Open-ended discovery** asks agents "what's wrong here?" — agents respond with a wide, shallow output. Recall is reasonable but precision suffers and the agent's attention diffuses.

**Hypothesis pre-declaration** asks agents "is this specific claim true or false?" — agents respond with mechanical proof or counterexample. Both directions yield useful artifacts:
- TRUE → submittable finding (with provenance back to the hypothesis source)
- FALSE → refutation entry that prevents future agents from re-investigating the same dead end

This is the same epistemic shift that takes science from "natural philosophy" (open observation) to "Popper's falsification" (testable predictions). Audits benefit identically.

---

## Cross-language applicability

| Language | Pre-declaration considerations |
|----------|------------------------------|
| EVM/Solidity | Standard — name function + state + actor + outcome. Works directly. |
| Solana/Rust | Account-validation hypotheses ("PDA seeds for X don't validate Y") map cleanly. CPI hypotheses pre-declare target program + invariant. |
| Move (Aptos/Sui) | Resource-lifecycle hypotheses ("resource of type T can be moved out of context Y"). Object-capability hypotheses for Sui. |
| C/C++ (XRPL, Bitcoin) | Memory-safety hypotheses pre-declare buffer/lifetime/UB classes. Wire-format hypotheses pre-declare codec invariant. |

---

## Anti-patterns (when NOT to apply)

1. **Single-contract, <500 nSLoC scope** — pre-declaration overhead (~30 min) exceeds yield. Open-ended discovery on small surface is faster.
2. **Hypothesis-of-the-week syndrome** — pre-declaring 50+ hypotheses across all domains floods agent context. Cap at ~7 per domain; promote stretch hypotheses to L-N (open leads) for later iteration.
3. **Pattern matching from prior audits** — pre-declaring "Audit X had a registry-desync; check if this audit has one too" anchors on specific patterns. Pre-declare CLASSES of hypotheses, not specific bug shapes from prior audits.
4. **Too-general hypotheses** — "The protocol has a reentrancy" is not falsifiable until you name the function. Reject these at the falsifiability check.

---

## Cost analysis

| Phase | Time delta vs open-ended |
|-------|------------------------|
| Phase 0 (planning) | +30-60 min for hypothesis pre-declaration |
| Phase 3 (breadth) | -50% to -70% (focused agents converge faster) |
| Phase 4b (depth) | -30% (fewer dead-end angles) |
| Net | ~30-40% faster overall + sharper REFUTED entries |

Pre-declaration is a **front-loaded investment** that pays back across the audit. The 30-60 min upfront overhead saves several agent-hours downstream.

---

## Validation: Monetrix April 2026 audit

| Domain | Open-ended ran first? | Pre-declared hypothesis approach | Outcome |
|--------|----------------------|---------------------------------|---------|
| 1-8 | Yes (open-ended discovery) | NO | 3 Mediums + 23 QAs across ~8 domains, 8-agent breadth |
| 11 | n/a (synthesis pass) | YES — 6 pre-declared chain candidates CH-A..CH-F | 0 NEW, all chains verdicted in 1 agent |
| 12-14 | n/a | YES — H12.1-H12.9, H13.1-H13.7, H14.1-H14.7 | 0 NEW HM in each, all hypotheses verdicted in 2 breadth agents |

Effort comparison: Domains 1-8 used 8 breadth agents per domain; Domains 12-14 used 2 breadth agents per domain. Same surface coverage. **~75% breadth budget reduction** with no recall loss (both yielded 0 new HM in those late domains).

The pre-declared approach also produced systematic R-N refutations (R-21 through R-39) that flowed into the cross-language manifest, vs. the open-ended approach which produced verbose REPORT.md prose without easy-to-extract refutation entries.