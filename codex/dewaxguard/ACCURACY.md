# Accuracy — what this skill can and cannot promise

> Read this before trusting (or promising) any accuracy number for dewaxguard.

## The honest headline

**No LLM-based security auditor is 100% accurate, and dewaxguard does not claim to be.** Smart-contract bug-finding is not a decidable problem with a checkable oracle — it is open-ended reasoning over adversarial code. Two hard limits apply:

1. **Recall (catching every bug) cannot be guaranteed.** There is no enumerable list of "all bugs" to check against. A novel business-logic flaw with no prior art (the RC-NOVEL / RC-METHOD classes in the post-audit protocol) can always exist below the methodology's current coverage. The Sherlock 1260 post-mortem is the standing proof: dewaxguard shipped 5 valid findings but **0 of the contest's 9 High/Critical families** — a 0% recall event on the hardest tier, on a real audit.
2. **Precision (zero false positives) cannot be guaranteed either.** LLM reasoning produces plausible-but-wrong findings. The skill's entire Phase 5 (PoC) + Phase 5d (bug validator) + realism-filter machinery exists *because* raw findings are not trustworthy without mechanical proof.

So "make this skill 100% accurate" is not an achievable target. What **is** achievable, and what this skill is built around, is: **maximize accuracy with layered defenses, and measure the residual error honestly instead of asserting perfection.**

## What "maximize accuracy" concretely means here

### Recall maximizers (find more real bugs)
- **8 core + 5 attacker-framing breadth agents** with different lenses — diversity beats a single pass.
- **6 depth agents + Nemesis cross-feed** (thorough) — re-interrogate breadth output, hunt cross-lens seams.
- **25 cross-audit methodology templates (M-03…M-30)**, now **auto-selected by trigger frontmatter** (`scripts/match_methodologies.sh`) so the relevant lens fires from code evidence, not memory.
- **Post-audit Phase A retrospective gate** — every audit closes only after a recall/precision comparison vs ground truth, so misses become methodology fixes (the loop that turns a 0%-recall event into M-30 + three template extensions).

### Precision maximizers (drop false positives)
- **Mainnet-fork PoC** (`[FORK-PASS]`) — mechanical proof on real deployed contracts; the only evidence tier that supports a confident CONFIRMED.
- **`rules/realism-filter.md`** — rejects out-of-scope classes at discovery (e.g. compromised-key preconditions) before a verification pass is spent.
- **`rules/severity-decision-tree.md`** — hard a/b/c severity ceiling; over-claimed severity is deducted by the bug validator.
- **`platform-quirks/*.md` + `refuted/INDEX.md`** — pre-refute known false-positive classes per platform (Soroban archive-restore, Sui shared-object serialization, …) so they are never re-investigated.
- **`references/criteria/*.md`** — score each finding against the actual platform's judging rules before submission.

### Consistency guarantees (the part that CAN be ~100%)
The *internal consistency* of the skill is mechanically checkable and held at 100% by `scripts/selfcheck.sh`:
- every methodology file registered in INDEX.md, every link resolves
- version synced across VERSION / SKILL.md / CHANGELOG
- every trigger-grep compiles; no brace-globs; no double-backslash corruption
- every file SKILL.md references actually exists
- benchmarks parse and their blind-stripper removes all answer leaks

This is the one place "100%" is the right word — and it is enforced by a script, not a promise.

## How accuracy is measured (not asserted)

`benchmarks/` holds known-bug contracts with `ground-truth.json` oracles. The protocol:

```bash
scripts/blind_benchmark.sh --out /tmp/blind        # strip answer comments, omit ground truth
#   -> run the breadth/depth agents on the BLIND copy
scripts/score_benchmark.py <agent_output> benchmarks/<id>/ground-truth.json
```

`score_benchmark.py` reports **recall** (must_detect findings hit), **trap precision** (false-positive traps left clean), and **severity delta** (calibration). `scripts/run_benchmarks.sh` wraps blind-prep + scoring + aggregation into one CI-gateable runner (`--prep` / `--score DIR` / `--check`). Latest baseline: `benchmarks/results/v1.21.0_2026-06-12.md` — 6/6 recall, 5/6 trap precision, a consistent +1 severity over-escalation at the breadth layer, and one corrected benchmark oracle.

As of v1.22.0 the corpus is **8 benchmarks across 5 of 6 language trees** (3 EVM, 2 Solana, 1 Sui, 1 Aptos, 1 Stellar; C/C++ remains the only unmeasured tree). The +1 breadth over-escalation flagged by the v1.21.0 run is now addressed at its source by the "Severity self-calibration" rule in `shared-rules.md` (derive impact×likelihood, no pre-applied modifiers, sandbag on ties) — the next full benchmark run will measure whether the bias closed.

### Three rules that keep the measurement honest
1. **Never audit a leaked benchmark.** Sources carry `// VULNERABLE:` comments; always run through `blind_benchmark.sh` first. `selfcheck.sh` regression-guards the stripper.
2. **Never edit a ground truth to match agent output.** Oracles are corrected only when the code is independently re-read and the oracle is *wrong* (the v1.21.0 Sui fix: the claimed race is impossible on Sui; the real fund-lock bug was added). Every correction carries an `_oracle_review` note. Coaching the metric is a banned anti-pattern.
3. **Report the caveats with the number.** Toy contracts, single breadth pass; as of v1.22.0 only the C/C++ tree is unmeasured (Aptos + Stellar benchmarks added). A recall number is meaningless without its corpus.

## If you want higher real-world accuracy on a given audit
- Run `thorough` mode (adds the 5 attacker-framing agents + Nemesis + full verification).
- Provide docs (`docs:{url}`) so the docs-intent map can both raise recall and kill "intended-behavior" false positives.
- Provide a fork RPC (`network:{name}`) so Medium+ findings get `[FORK-PASS]` proof instead of `[CODE-TRACE]`.
- Run `proven-only:true` when you want every unproven finding capped at Low — trades recall for precision.

## Bottom line
The reachable target is **"highest achievable recall, mechanically-proven precision, fully measured residual error, and 100% internal consistency"** — not omniscience. This file, `selfcheck.sh`, the blind benchmark harness, and the Phase A retrospective gate are the machinery that keeps that target honest audit over audit.
