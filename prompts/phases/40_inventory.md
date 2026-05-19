# Phase: Inventory + Dedup + Severity Routing (v1.13 driver, v1.12 scripts)

> You are a fresh `claude -p` subprocess invoked by the dewaxguard v1.13 driver.
> You have no prior conversation context. This phase is **mostly mechanical** — you invoke three Python scripts and inspect their output. The only LLM step is an optional tie-break for ambiguous dedup pairs.

## Audit context

- **Audit ID**: `{{AUDIT_ID}}`
- **Scratchpad**: `{{SCRATCHPAD}}`
- **Skill root**: `{{SKILL_ROOT}}`
- **Phase budget**: `{{TIMEOUT_SECONDS}}` seconds

## Pre-requisites (from prior phase)

`{{SCRATCHPAD}}` must contain at least one breadth analysis file (pattern `analysis_*.md`). Confirm with `ls {{SCRATCHPAD}}/analysis_*.md` before proceeding.

## Your task — run the v1.12 mechanical pipeline

Use the Bash tool to invoke these scripts in order. Do NOT re-implement the logic in prose; the scripts are the source of truth.

### Step 1 — Parse breadth output into the v1.0 findings_table schema

```bash
python3 {{SKILL_ROOT}}/scripts/parse_findings.py \
    {{SCRATCHPAD}}/analysis_*.md \
    --audit-id "{{AUDIT_ID}}" \
    --phase breadth \
    -o {{SCRATCHPAD}}/findings_breadth.json
```

Confirm: `findings_breadth.json` exists and has `"findings": [...]` with ≥ 1 entry.

### Step 2 — Mechanical three-stage dedup

```bash
python3 {{SKILL_ROOT}}/scripts/dedup.py \
    {{SCRATCHPAD}}/findings_breadth.json \
    -o {{SCRATCHPAD}}/findings_merged.json \
    --clusters-out {{SCRATCHPAD}}/dedup_clusters.json \
    --ambiguous-out {{SCRATCHPAD}}/dedup_ambiguous.json \
    --report
```

The script will print dedup stats (input → output count, ambiguous pair count).

### Step 3 — Optional LLM tie-break for ambiguous pairs

Read `{{SCRATCHPAD}}/dedup_ambiguous.json`. If the `ambiguous` array is empty, skip to Step 4.

Otherwise, for each ambiguous pair:

1. Read both findings' full body from `{{SCRATCHPAD}}/findings_merged.json` (find them by `id` field).
2. Decide MERGE or SEPARATE based on whether the bugs share root cause + fix.
3. If MERGE: edit `findings_merged.json` to add a `canonical_id` field on one row pointing to the other's `id`. Use the same canonical-picker rule: highest severity → FINDING over LEAD → most evidence tags.
4. If SEPARATE: do nothing (the rows stay separate by default).

Write the tie-break decisions to `{{SCRATCHPAD}}/dedup_tiebreaks.md`:

```markdown
# Tie-break decisions (Phase 4a)

| Pair | Decision | Reasoning |
|------|----------|-----------|
| F-3 ↔ F-7 | MERGE | both describe missing access on liquidate; same fix |
| F-12 ↔ F-15 | SEPARATE | rounding vs reentrancy on same function; different fixes |
```

### Step 4 — Severity routing

```bash
python3 {{SKILL_ROOT}}/scripts/severity_router.py \
    {{SCRATCHPAD}}/findings_merged.json \
    -o {{SCRATCHPAD}}/findings_routed.json \
    --diff-out {{SCRATCHPAD}}/severity_changes.json \
    --report
```

If the audit is in PROVEN_ONLY mode (set in `{{PROJECT_ROOT}}/CLAUDE.md` or `--proven-only` flag), append `--proven-only` to the command.

### Step 5 — Write phase summary

Write `{{SCRATCHPAD}}/inventory_summary.md`:

```markdown
# Inventory Phase Summary — {{AUDIT_ID}}

**Generated**: {{ISO_NOW}}

## Dedup stats

| Metric | Count |
|--------|-------|
| Input findings (breadth) | <N> |
| Output canonicals | <N> |
| Duplicates absorbed | <N> |
| Clusters | <N> |
| Ambiguous pairs | <N> |
| Tie-break decisions | <N merged> / <N separate> |

## Severity distribution

| Severity | Count |
|----------|-------|
| Critical | <N> |
| High | <N> |
| Medium | <N> |
| Low | <N> |
| Informational | <N> |

## Realism downgrades applied

| Finding ID | Original | Final | Reason |
|-----------|----------|-------|--------|

(One row per entry in `severity_changes.json` where `pre_modifier` is not null.)

## Files passed to Phase 4b (depth)

`{{SCRATCHPAD}}/findings_routed.json` — N canonical findings ready for depth analysis.
```

## Required outputs (driver gate checks for these)

- `{{SCRATCHPAD}}/findings_routed.json`
- `{{SCRATCHPAD}}/dedup_clusters.json`

## Retry hint (if any)

{{RETRY_HINT}}

When all 5 steps complete and the required outputs exist, exit cleanly. Do not start Phase 4b depth; the driver invokes that separately.
