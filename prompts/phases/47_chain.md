# Phase: Chain Analysis (v1.13.1 driver)

> Fresh `claude -p` subprocess. No prior context. Treat this prompt as your entire task.
> This phase runs AFTER depth (Phase 4b) and BEFORE verification (Phase 5).

## Audit context

- **Audit ID**: `{{AUDIT_ID}}`
- **Mode**: `{{MODE}}`
- **Scratchpad**: `{{SCRATCHPAD}}`
- **Skill root**: `{{SKILL_ROOT}}`

## Pre-requisites

`{{SCRATCHPAD}}` must contain:
- `findings_routed.json` (from inventory)
- `depth_*_findings.md` (≥ 1 file from depth phase)

Confirm with `ls {{SCRATCHPAD}}/depth_*_findings.md`. If absent, write `{{SCRATCHPAD}}/chain_failed.md` with the diagnostic and exit.

## Your task — two-agent sequential pipeline

Follow `{{SKILL_ROOT}}/rules/chain-analysis-prompt.md` (and the more detailed `~/.plamen/rules/phase4c-chain-prompt.md` if available). The split-agent architecture prevents context overflow on large inputs.

### Pre-step — Compact chain summaries (orchestrator-inline)

Each depth agent emits a Chain Summary table at the end of its output (per `45_depth.md`). Extract these tables into a single compact file:

```bash
# Build a chain summaries digest (~200-400 lines instead of 5000+)
for f in {{SCRATCHPAD}}/depth_*_findings.md; do
    echo "## from $(basename $f)"
    sed -n '/## Chain Summary/,$p' "$f"
    echo ""
done > {{SCRATCHPAD}}/chain_summaries_compact.md
```

Also extract from `findings_routed.json` a variable→finding cross-reference for state-precondition matching:

```bash
python3 -c "
import json
data = json.load(open('{{SCRATCHPAD}}/findings_routed.json'))
m = {}
for f in data['findings']:
    if f.get('canonical_id'):
        continue
    # extract state variable names from postconditions and write list
    for p in (f.get('postconditions') or []):
        for v in (p.get('description', '') + ' ' + (p.get('beneficiary') or '')).split():
            v = v.strip('.,;()')
            if v.isidentifier() and len(v) > 3:
                m.setdefault(v, []).append(f['id'])
print('# Variable → Finding Cross-Reference')
for v, ids in sorted(m.items()):
    if len(ids) > 1:
        print(f'- **{v}**: {\", \".join(ids)}')
" > {{SCRATCHPAD}}/variable_finding_map.md
```

### Agent 1 — Enabler Enumeration + Grouping

Spawn via the Task tool (`general-purpose`, model=opus for core/thorough, sonnet for light):

```
You are Chain Agent 1: Enabler Enumeration + Grouping.

## Inputs
- {{SCRATCHPAD}}/findings_routed.json (canonical findings + severities)
- {{SCRATCHPAD}}/chain_summaries_compact.md (compact digest from depth)
- {{SCRATCHPAD}}/variable_finding_map.md (state variable index)
- {{SCRATCHPAD}}/attack_surface.md (entry points + privileged roles)

## Phase 0 — Enabler enumeration (Rule R12)

For each CONFIRMED or PARTIAL finding's dangerous precondition state S, enumerate the 5-actor table:

| # | Actor Category | Path to S? | Reachable? | Existing Finding? | New finding needed? |
|---|----------------|-----------|------------|------------------|--------------------|
| 1 | External attacker (permissionless) | ... | YES/NO | ... | [EN-N] or N/A |
| 2 | Semi-trusted role (within permissions) | ... | YES/NO | ... | ... |
| 3 | Natural protocol operation | ... | YES/NO | ... | ... |
| 4 | External event (governance/pause/slash) | ... | YES/NO | ... | ... |
| 5 | User action sequence | ... | YES/NO | ... | ... |

'No path' requires a one-sentence reason. Reachable-but-no-existing-finding → create [EN-N] inheriting the IMPACT of the original.

## Phase 1 — Grouping & dedup

1. Merge depth findings + enabler findings + breadth findings (route via canonical_id)
2. Group by root cause into hypotheses
3. Max 5 findings per hypothesis. No catch-all. Same fix required → same hypothesis. Different fixes → separate.
4. Severity inheritance: hypothesis inherits HIGHEST severity from its constituents.
5. Anti-absorption test: write a 1-line fix for each. Different functions → separate hypotheses.

## Outputs
- {{SCRATCHPAD}}/hypotheses.md (hypothesis table)
- {{SCRATCHPAD}}/finding_mapping.md (finding → hypothesis mapping)
- {{SCRATCHPAD}}/enabler_results.md (enabler enumeration + 5-actor tables)

Return: 'DONE: N hypotheses, E enabler paths enumerated'.
SCOPE: write only to these files; do not run Agent 2 or verification.
```

Wait for Agent 1 to complete before spawning Agent 2.

### Agent 2 — Chain Matching + Composition Coverage

Spawn via Task tool:

```
You are Chain Agent 2: Chain Matching + Composition Coverage.

## Inputs
- {{SCRATCHPAD}}/hypotheses.md (from Agent 1)
- {{SCRATCHPAD}}/finding_mapping.md (from Agent 1)
- {{SCRATCHPAD}}/enabler_results.md (from Agent 1)
- {{SCRATCHPAD}}/variable_finding_map.md (variable cross-reference)
- {{SCRATCHPAD}}/findings_routed.json (full finding bodies)

## Phase 2 — Chain matching

For each PARTIAL or REFUTED finding A:
1. Extract A's missing precondition + type (STATE / ACCESS / TIMING / EXTERNAL / BALANCE)
2. For STATE-type: variable_finding_map.md → find ALL findings writing to the same variable
3. Search CONFIRMED + PARTIAL findings for postconditions matching A's missing precondition
4. If found: create CHAIN HYPOTHESIS CH-N with combined attack sequence

### Chain Hypothesis Format

## Chain Hypothesis CH-{N}
### Blocked Finding (A)
- ID, Title, Original Verdict, Missing Precondition, Type
### Enabler Finding (B)
- ID, Title, Original Verdict, Postcondition Created, Type
### Chain Match
- Match Strength: STRONG / MODERATE / WEAK
- Match Reasoning: B creates exact precondition A needs
### Combined Attack Sequence
1. Execute B's enabler action
2. Execute A's previously-blocked attack
3. Impact
### Severity Reassessment
Chain severity ≥ max(A.severity, B.severity).
Upgrade if combined impact > $100k & profitability > 2x → CRITICAL.
Upgrade if combined impact > $10k & profitability > 2x → minimum HIGH.

## Composition Coverage Map

After chain matching, emit a coverage table:

| Finding A | Finding B | Explored? | Result | Notes |
|-----------|-----------|-----------|--------|-------|

Cross-class pairs (state+token, access+external) are HIGH PRIORITY.

## Phase 3 — RAG validation for chains (when available)

For each chain hypothesis: call `mcp__unified-vuln-db__validate_hypothesis` if available; otherwise WebSearch `solodit.xyz {chain pattern}`. Upgrade chain severity if historical precedent confirms.

## Outputs
- Append chain hypotheses to {{SCRATCHPAD}}/hypotheses.md
- {{SCRATCHPAD}}/chain_hypotheses.md (chain summary table + detailed CH-N entries)
- {{SCRATCHPAD}}/composition_coverage.md (coverage map)
- {{SCRATCHPAD}}/synthesis_full.md (combined enabler+grouping+chain analysis)

Return: 'DONE: M chains identified, K severity upgrades, U unexplored pairs remaining'.
SCOPE: write only to these files; do not run verification or report.
```

### Iterative composition (orchestrator inline)

After Agent 2 completes, read `{{SCRATCHPAD}}/composition_coverage.md`. Count unexplored cross-class Medium+ pairs.

- If 0 unexplored pairs OR Agent 2 reported 0 new chains AND 0 unexplored Medium+ pairs → DONE
- Otherwise (max 1 iteration in v1.13.1, hard cap 2): spawn one more Task agent targeting just the unexplored pairs, append results to `chain_hypotheses.md`

## Required outputs (driver gate checks for these)

- `{{SCRATCHPAD}}/hypotheses.md`
- `{{SCRATCHPAD}}/chain_hypotheses.md`

Both must be non-empty.

## Retry hint (if any)

{{RETRY_HINT}}

When Agent 1 + Agent 2 + iterative composition all complete with non-empty outputs, exit cleanly.
