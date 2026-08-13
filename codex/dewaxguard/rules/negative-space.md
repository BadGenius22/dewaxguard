# Negative Space — What This Run Did Not Illuminate

> **Purpose**: The pipeline is good at producing findings and bad at knowing what it missed. Every
> stage after breadth is conditioned on the breadth finding list, so a region no breadth agent
> entered is invisible to inventory, depth, chain, and verification alike. This rule builds the
> complement: an explicit map of the unexamined, the unstable, and the unmodelled.
> **Binds**: global rule A-1 (`~/.agents/skills/dewaxguard/references/audit-method.md`) — a quiet pass is not coverage.
> **Phases**: 1.2 (test-gap map) → 2.5 (blind model) → 3.5 (blind re-run) → 4b (budget weighting)
> → 6 (mandatory report section).
> **Artifact**: `{SCRATCHPAD}/negative-space.md`, assembled incrementally by the three sources below.

---

## Why three sources

Each source finds a different kind of blind region, and none of them substitutes for the others:

| Source | Blind region it finds | Fails to find |
|--------|----------------------|---------------|
| Test-gap map (1.2) | Where the **team** did not look | Areas they tested badly |
| Blind model diff (2.5) | Invariants and outflow sites **no finding touches** | Bugs inside modelled areas |
| Blind re-run variance (3.5) | Where **this run** is unstable | Areas stably missed by every run |

The third is the honest one about the tool's own limits, and it is the reason the other two exist:
run-to-run variance means a single pass samples the space, it does not sweep it.

---

## Phase 1.2 — Test-Gap Map (recon, deterministic-first)

> Rationale: the gaps in a test suite are usually the gaps in the team's thinking. A function the
> team never wrote an adversarial test for is a function they believe is obviously correct.

**Build**, writing `{SCRATCHPAD}/test-gap-map.md`:

1. Enumerate the repo's test files (`test/`, `tests/`, `*_test.*`, `*.t.sol`, `#[test]`, `#[cfg(test)]`).
2. For each in-scope entry point (from `auth-critical-files.txt` + the Phase 1.1 attack-surface map),
   grep the test corpus for calls to it. Record the call count.
3. Classify each entry point:

| Class | Definition | Depth priority |
|-------|-----------|---------------|
| `UNTESTED` | Zero test calls | **Highest** |
| `HAPPY-ONLY` | Called only in tests with no `expectRevert` / `should_panic` / `#[should_panic]` / negative assertion anywhere in the test body | **High** |
| `ADVERSARIAL` | At least one test asserts a failure or an attack is blocked | Normal |
| `FUZZED` | Appears in a fuzz/invariant/proptest target | Lowest |

4. Do the same for every **protocol-declared invariant** found by `invariant-extract.md`: is there a
   test that would fail if the invariant broke? An invariant with no such test is `UNTESTED`.

**Consumption (HARD)**: Phase 4b depth agents receive the `UNTESTED` + `HAPPY-ONLY` sets as a
priority list. When depth budget is contested, an `UNTESTED` entry point outranks a
finding-derived depth target of equal severity. Record the weighting decision in the depth log.

**Do not** treat `FUZZED` as safe. A fuzz target proves the invariant it asserts, and nothing about
the invariants it does not assert. Note which invariants the fuzz harness actually checks.

---

## Phase 2.5 — Findings-Blind Protocol Model

> Rationale: build the model of what the protocol is *trying* to be, so that a divergence between
> intent and code is detectable. This is the half that has not commoditized, and it is the half the
> pipeline currently never does independently, because every agent after recon reads code with a
> finding list already in context.

**Spawn ONE agent (finding in core/thorough, worker in light) with a hard input restriction:**

```
ALLOWED INPUT:  source files in scope, protocol docs, docs-intent-map.md, invariant-extract.md
FORBIDDEN INPUT: any findings file, analysis_*.md, findings_*.json, hypotheses, leads,
                 prior-audit reports, known-issue indices, refuted/INDEX.md, patterns/
```

The forbidden list is the point. The agent must not be able to pattern-match against a finding
shape, because its job is to describe the intended system, not to hunt in it.

**It produces `{SCRATCHPAD}/protocol-model.md`:**

1. **Intent** — one paragraph: what is this protocol trying to be, in the words its own docs use.
2. **Invariant ledger** — every statement that must always be true, each with either the `file:line`
   that enforces it, or the marker `NOT ENFORCED IN CODE` (which is a claim requiring a citation of
   where it *should* have been enforced).
3. **Value-outflow map** — every site where value leaves the system, and for each, the actor gate
   that reaches it. Organise by protocol mechanic, never by vulnerability class. (This is the
   differentiated-work question from `~/.agents/skills/dewaxguard/references/bounty-calibration.md` rule 4: enumerate the
   outflow sites and who can reach each one, rather than sweeping bug taxonomies.)
4. **Model-vs-code divergences** — places where the code stops agreeing with the intent in (1).
   These enter the finding stream as normal LEADs.

**Diff at Phase 4c (orchestrator, mechanical)**: for every invariant in the ledger and every row in
the outflow map, check whether any finding references it. The unreferenced set is the **unmodelled
region** and appends to `negative-space.md`. Any unreferenced row that is both `NOT ENFORCED IN CODE`
and permissionlessly reachable is promoted to a depth target regardless of remaining budget.

---

## Phase 3.5 — Blind Re-Run Variance

> Rationale: these agents are not deterministic. Running the same lens twice over the same code
> yields two different sets. Measuring that spread converts "the run was quiet here" from an implied
> coverage claim into a number.

**Re-run exactly these three lenses** on the identical scope, after the Phase 3 breadth roster
returns:

| Lens | Why this one |
|------|-------------|
| `invariant-agent` | Novel business logic — the non-commoditized half |
| `economic-security-agent` | Cross-contract economic reasoning — the other non-commoditized half |
| `first-principles-agent` | Lowest prior-shape dependence, so highest expected spread |

`vector-scan-agent` is deliberately **excluded**: known attack patterns are the commoditizing half
and are the most stable across runs, so re-running it buys the least information per token.

**Hard conditions on the re-run:**
- No exclusion list. No pass-1 finding list. No `analysis_*.md` in context. This is a *blind* re-run,
  not the exclusion-list rescan pattern (which measures novelty, not stability, and cannot detect
  variance by construction).
- Same source, same scope, same agent file, same model tier as pass 1.

**Measure**, appending to `negative-space.md`:

```bash
# Cluster both passes together, then compare group_key sets per lens.
python3 scripts/parse_findings.py $SCRATCHPAD/analysis_{lens}.md      --phase breadth  -o $SCRATCHPAD/var_{lens}_p1.json
python3 scripts/parse_findings.py $SCRATCHPAD/rerun_{lens}.md         --phase rerun    -o $SCRATCHPAD/var_{lens}_p2.json
python3 scripts/dedup.py $SCRATCHPAD/var_{lens}_p1.json $SCRATCHPAD/var_{lens}_p2.json -o $SCRATCHPAD/var_{lens}_merged.json
```

`stability = |P1 ∩ P2| / |P1 ∪ P2|` on group_keys, per lens.

| Stability | Reading | Action |
|-----------|---------|--------|
| ≥ 0.7 | Lens is reproducible on this codebase | Quiet regions are weak evidence of absence |
| 0.3–0.7 | Lens is sampling | State this in the report; quiet regions carry no evidence |
| < 0.3 | Lens is effectively random here | A third run is worth more than any depth agent; escalate |

**Findings unique to pass 2 are real findings** and enter the inventory normally. They are also the
direct measurement of what a single pass would have missed, so record that count explicitly.

---

## Phase 6 — Mandatory report section

Every report carries a `## What this audit did not cover` section, sourced from
`negative-space.md`. It states, in plain English per `rules/plain-english-style.md`:

1. Entry points and invariants with no team test, and whether depth reached them.
2. Invariants and value-outflow sites from the protocol model that no finding touched.
3. Per-lens stability numbers, and the count of findings that only one of the two passes found.
4. Anything examined but left unresolved either way, with the reason (no build, no fork RPC, no
   documented intent, budget exhausted).

**Prohibited in every report** (per global rule A-1): "full coverage", "all paths analyzed", "the
contract is clean", "no issues found in X", and any use of the word *coverage* for a throughput
count. The correct phrasing for a quiet area is: "this run surfaced nothing in X; at lens stability
S that is weak/no evidence of absence."
