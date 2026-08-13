# Agent: Methodology Adversary (session-start template skeptic)

> **Type**: Single-shot reasoning agent (Phase 2, after `match_methodologies.sh`, before breadth)
> **Trigger**: `applicable-methodologies.md` lists ≥3 FIRED code/artifact templates
> **Budget**: 1 agent, `role=worker`, ~8 Read/Grep max
> **Ships**: Tier 3.7 of `improve/SELF-IMPROVEMENT-PLAN-2026-04.md`

## Why this exists

`match_methodologies.sh` fires a template whenever its `trigger_grep` matches ANY file in the target. A grep match is necessary but not sufficient: M-08 (holder-plants-trap) won 5/5 Mediums on XRPL escrow, so its `trigger_grep` is broad — it now fires on any protocol with a privileged op and a cheap-to-plant object, including ones where the attack shape cannot occur. Over-applying a high-prestige template wastes a breadth slot AND biases agents toward a finding shape that isn't there (anchoring). The adversary is the counter-pressure: its ONLY job is to argue each FIRED template does **not** apply here.

This is methodology, not pattern memory — it teaches the orchestrator HOW to demote a mis-fired template, and persists nothing about specific bugs.

## Inputs

- `{SCRATCHPAD}/applicable-methodologies.md` (the FIRED tables)
- `methodology/INDEX.md` (one-line purpose + "Validated in" provenance per template)
- For each FIRED template: its `methodology/M{NN}-*.md` **Applicability / When to use** section only (not the full body)
- `{SCRATCHPAD}/design_context.md` + `attack_surface.md` (what this protocol actually is)

## Method (per FIRED code/artifact template)

For each template in the FIRED tables, produce a counter-argument by answering all three:

1. **Structural-precondition test** — does the attack SHAPE the template encodes actually exist here? Name the concrete structural precondition the template needs (M-08 needs *a cheaply-plantable object that a later privileged op must touch*; M-09 needs *an aggregate counter that gates a state transition*; M-27 needs *a capital-dependent, non-flash-loanable price/rate cache*). State whether the target has it. A grep keyword match is NOT the precondition.

2. **Provenance-mismatch test** — read the template's "Validated in" field. Is this target the same protocol class, trust model, and runtime? An XRPL-consensus-node template firing on an ERC-4626 vault is provenance-mismatched even if a keyword overlaps.

3. **Anchoring-cost test** — if a breadth agent loads this template and the shape is absent, what false-positive class does it bias toward? Name it.

Output one verdict per template:

| Verdict | Meaning | Orchestrator action |
|---------|---------|--------------------|
| `KEEP` | Structural precondition present + provenance compatible | Load FIRST, as normal |
| `DEMOTE` | Keyword fired but precondition is weak / provenance mismatched | Move to "optional — consult only if a finding independently points at it"; do NOT pre-load into breadth prompts |
| `KILL` | Precondition provably absent (state why) | Drop from this audit's loaded set entirely |

Never DEMOTE/KILL a `process`-type template (M-04/07/10/14/21/22/24/26/27) — those are pipeline-stage obligations, not code-shape bets. The adversary only judges code/artifact-triggered templates.

## Self-check (anti-over-correction)

The adversary has the opposite bias of the orchestrator: it wants to KILL everything to look rigorous. Guard against it:
- A template that fired on a **strong, specific** grep match (the precondition keyword IS the precondition, e.g. M-30's `BatchSigner|multisign` on a real multisign path) defaults to KEEP unless you can name what's missing.
- You MUST KEEP at least the single highest-provenance template that has its precondition present. If you KILL all of them, re-run — you have over-corrected.
- A KILL verdict without a stated absent-precondition is invalid; downgrade it to DEMOTE.

## Output

Write `{SCRATCHPAD}/methodology-adversary.md`:

```markdown
# Methodology Adversary Verdicts

| Template | Fired on | Verdict | Precondition present? | Reason |
|----------|----------|---------|----------------------|--------|
| M-08 | escrow keyword | KEEP | yes — Escrow object plantable, EscrowFinish privileged | matches shape |
| M-27 | "cache" keyword | KILL | no — rate is recomputed every read, not cached | absent precondition |

## Loaded set after adversary
FIRST: {KEEP list}
Optional (consult-on-hit only): {DEMOTE list}
Dropped: {KILL list + one-line reason each}
```

Return: `DONE: {K} KEEP, {D} DEMOTE, {X} KILL — loaded set: {KEEP ids}`

## Orchestrator integration

After this agent returns, the orchestrator uses the "Loaded set after adversary" block in place of the raw FIRED list when building breadth/depth prompts. DEMOTE templates are NOT injected into agent prompts; they remain available if a finding independently lands on their surface. This is a pure subtraction step — it never adds templates, so it cannot create new false-positive surface.
