# Phase: Report Assembly (v1.13 driver)

> Fresh `claude -p` subprocess. No prior context. Treat this prompt as your entire task.

## Audit context

- **Audit ID**: `{{AUDIT_ID}}`
- **Mode**: `{{MODE}}`
- **Project root**: `{{PROJECT_ROOT}}`
- **Scratchpad**: `{{SCRATCHPAD}}`
- **Skill root**: `{{SKILL_ROOT}}`

## Pre-requisites

`{{SCRATCHPAD}}/findings_routed.json` and at least one `verify_*.md` must exist.

## Your task

Assemble the final audit report at **`{{PROJECT_ROOT}}/AUDIT_REPORT.md`** following the template in `{{SKILL_ROOT}}/rules/report-template.md`. The report assembly pipeline is described in `{{SKILL_ROOT}}/rules/phase6-report-prompts.md` (3 parallel tier writers + 1 assembler). For the v1.13 driver MVP, you may either:

**Option A (preferred for thorough mode)**: spawn the 4 sub-agents (Index → 3 tier writers → Assembler) per `phase6-report-prompts.md`.

**Option B (for light/core mode)**: produce the full report in a single pass. Read:

- `{{SCRATCHPAD}}/findings_routed.json` for canonical findings + severities
- `{{SCRATCHPAD}}/verify_*.md` for verification verdicts and PoC results
- `{{SCRATCHPAD}}/dedup_clusters.json` for the consolidation map
- `{{SKILL_ROOT}}/rules/report-template.md` for the exact structure
- `{{SKILL_ROOT}}/rules/plain-english-style.md` for the style rules
- `{{SKILL_ROOT}}/references/report-formatting.md` for per-finding formatting

The report MUST:

- Use clean sequential severity-prefixed report IDs (`C-01`, `H-01`, `M-01`, `L-01`, `I-01`) — NO internal pipeline IDs in the body
- Have every finding in its own `### [X-NN] Title [VERIFIED|UNVERIFIED|CONTESTED]` section — no catch-all tables
- Follow the plain-English style (four-sentence Description, dollar/percent Impact, fix-sentence + diff + result-sentence Recommendation)
- Include Executive Summary (2-3 paragraphs for non-technical readers), Summary counts table, Components Audited table, Priority Remediation Order

The Quality Gates from `phase6-report-prompts.md` apply. After writing the report, run the self-checks at the end of `report-template.md`.

## Required outputs (driver gate checks for these)

- `{{PROJECT_ROOT}}/AUDIT_REPORT.md`

The content gate verifies the report contains the expected sections (Executive Summary, severity buckets, Priority Remediation Order).

## Retry hint (if any)

{{RETRY_HINT}}

When `AUDIT_REPORT.md` is written and passes the self-check, exit cleanly.
