# Phase: Report Assembly (v1.13.2 driver)

> Fresh `codex exec --json` subprocess. No prior context. Treat this prompt as your entire task.
> This is the user-facing artifact. Plain-English style is HARD; banned-jargon survival is a deduction.

## Audit context

- **Audit ID**: `{{AUDIT_ID}}`
- **Mode**: `{{MODE}}`
- **Project root**: `{{PROJECT_ROOT}}`
- **Scratchpad**: `{{SCRATCHPAD}}`
- **Skill root**: `{{SKILL_ROOT}}`
- **Phase budget**: `{{TIMEOUT_SECONDS}}` seconds

## Pre-requisites

- `{{SCRATCHPAD}}/findings_routed.json` — canonical findings + verdicts + severities
- `{{SCRATCHPAD}}/verify_*.md` — per-finding verification verdicts + PoC results (skipped in `light`)
- `{{SCRATCHPAD}}/dedup_clusters.json` — consolidation map
- `{{SCRATCHPAD}}/chain_hypotheses.md` — chain hypotheses for cross-references
- `{{SCRATCHPAD}}/validation_results.json` — per-platform scores (skipped in `light`)
- `{{SCRATCHPAD}}/design_context.md` — for Executive Summary
- `{{SCRATCHPAD}}/contract_inventory.md` — for Components Audited table

If `findings_routed.json` is missing, write `{{SCRATCHPAD}}/report_failed.md` and exit.

---

## STEP 1 — Choose assembly strategy

| Mode | Strategy |
|------|----------|
| `light` | Single-pass — produce the full report directly without spawning sub-agents |
| `core` | Single-pass for ≤ 25 findings; 4-agent assembly pipeline for > 25 |
| `thorough` | 4-agent assembly pipeline (Index → 3 tier writers → Assembler) — ALWAYS, regardless of finding count |

Count canonical findings in `findings_routed.json` to decide.

---

## STEP 2 (Strategy A) — Single-pass

When chosen, produce the report directly. Read all required inputs, then write `{{PROJECT_ROOT}}/AUDIT_REPORT.md` following the structure in STEP 3 below.

---

## STEP 2 (Strategy B) — 4-agent assembly pipeline

Per `rules/phase6-report-prompts.md`, the 4-agent pipeline produces higher-quality output for large finding counts. The pipeline runs SEQUENTIALLY (Index first, then 3 tier writers in parallel, then Assembler).

### Agent 1 — Index (mechanical)

```
spawn_agent(
  task_name="{TASK_NAME}",
  fork_turns="none",
  reasoning_effort="low",
  message="
You are the Report Index agent.

## Inputs
- {{SCRATCHPAD}}/findings_routed.json (canonical findings + severity + verdicts)
- {{SCRATCHPAD}}/chain_hypotheses.md (chains)
- {{SCRATCHPAD}}/dedup_clusters.json (consolidation map)
- {{SCRATCHPAD}}/validation_results.json (per-platform scores; may be absent in light mode)

## Method
1. Final severities: for each finding, use verifier severity if present, else inventory severity. Apply trust-assumption downgrades from realism_filter where applicable.
2. Root-cause consolidation (mandatory): merge hypotheses sharing the same root cause IF same fix pattern + same severity tier + same vulnerability class. List all affected locations in a single finding.
3. Assign report IDs: sort by severity tier (Critical → High → Medium → Low → Informational), within tier by verification status (VERIFIED first), then by impact. Assign clean sequential IDs: C-01, C-02, ..., H-01, H-02, ..., M-01, ..., L-01, ..., I-01, ...
4. Tier assignments:
   - Critical+High tier (for finding writer)
   - Medium tier (for worker writer)
   - Low+Info tier (for worker writer)
5. Cross-references: for chain findings referencing component findings, note the cross-reference using REPORT IDs only (e.g., 'C-01 references H-03').
6. Excluded findings list: any internal hypothesis that did NOT get a report ID. Each must have a valid exclusion reason (FALSE_POSITIVE from verifier OR DUPLICATE OF X-NN).

## Output
Write to {{SCRATCHPAD}}/report_index.md:

# Report Index

## Report Header Info
- Project Name: <from design_context.md>
- Date: <today>
- Contracts: <from contract_inventory.md>
- Build Status: <from build_status.md>
- Platform: <from applicable AGENTS.md, legacy CLAUDE.md, or contest scope; default = unspecified>

## Summary Counts
| Severity | Count |
|----------|-------|

## Master Finding Index
| Report ID | Title | Severity | Location | Verification | Trust Adj. | Internal Hyp. | Agent Sources |

## Tier Assignments
### Critical+High Tier (for finding writer)
### Medium Tier (for worker writer)
### Low+Info Tier (for worker writer)

## Consolidation Map
| Report ID | Consolidated From | Reason |

## Cross-Reference Map
| Report ID | References | Context |

## Excluded Findings (for Appendix A)
| Internal ID | Severity | Title | Exclusion Reason |

SCOPE: write only to {{SCRATCHPAD}}/report_index.md. Return 'DONE: N findings indexed' and stop.
"
)
```

After Agent 1 completes, run the completeness assertion inline:

```
hypothesis_count = count of canonical findings in findings_routed.json
report_ids = count of rows in Master Finding Index
excluded_count = count of rows in Excluded Findings
consolidated_absorbed = count from Consolidation Map (multiple-hypothesis-per-row)
ASSERT: hypothesis_count == report_ids + excluded_count + consolidated_absorbed
```

If MISMATCH, re-spawn Agent 1 with a retry hint naming the missing hypotheses.

### Agent 2 — Critical+High tier writer (finding)

```
spawn_agent(
  task_name="{TASK_NAME}",
  fork_turns="none",
  reasoning_effort="high",
  message="
You are the Critical+High Findings Writer.

## Mandatory reading
- {{SKILL_ROOT}}/rules/report-template.md (format)
- {{SKILL_ROOT}}/rules/plain-english-style.md (style, HARD)
- {{SKILL_ROOT}}/references/report-formatting.md (per-finding formatting)
- {{SCRATCHPAD}}/report_index.md (your tier assignments under 'Critical+High Tier')

## Inputs per finding
- {{SCRATCHPAD}}/findings_routed.json (full body)
- {{SCRATCHPAD}}/verify_<id>.md (verification verdict + PoC)
- {{SCRATCHPAD}}/chain_hypotheses.md (if this finding is part of a chain)
- Source files referenced in the finding's location

## Method
For EACH finding in your tier:
1. Write the full section using the format in report-template.md
2. Use the report ID (C-01, H-01) — NEVER internal pipeline IDs
3. Include code snippets from actual source
4. For chain findings: describe the COMPLETE attack sequence in the Description
5. For verified findings: include PoC results from verify_*.md
6. Cross-reference other findings using ONLY report IDs

## HARD rules
- No internal IDs anywhere (no [CS-N], [AC-N], [DST-N], [DEPTH-N], [SLITHER-N], [CH-N], or bracketed [H-N] inside body)
- Every finding gets its own ### section — no tables, no groups, no summaries
- Four-sentence Description shape (per plain-english-style.md)
- Recommendation = fix sentence + diff + result sentence

## Output
Write to {{SCRATCHPAD}}/report_critical_high.md:

## Critical Findings
### [C-01] Title [VERIFIED|UNVERIFIED|CONTESTED]
...

## High Findings
### [H-01] Title [VERIFIED|UNVERIFIED|CONTESTED]
...

SCOPE: write only to that file. Return 'DONE: C Critical + H High findings written' and stop.
"
)
```

### Agent 3 — Medium tier writer (worker)

```
spawn_agent(
  task_name="{TASK_NAME}",
  fork_turns="none",
  reasoning_effort="medium",
  message="
You are the Medium Findings Writer.
(Same structure as Agent 2 but for Medium tier; output {{SCRATCHPAD}}/report_medium.md)
"
)
```

### Agent 4 — Low+Info tier writer (worker)

```
spawn_agent(
  task_name="{TASK_NAME}",
  fork_turns="none",
  reasoning_effort="medium",
  message="
You are the Low+Informational Findings Writer.
(Same structure but Recommendation is optional for Low, PoC Result optional for Informational; output {{SCRATCHPAD}}/report_low_info.md)
"
)
```

Spawn agents 2, 3, 4 in parallel with three Codex delegation calls.

### Agent 5 — Assembler (mechanical for ≤ 25 findings, worker for > 25)

```
spawn_agent(
  task_name="{TASK_NAME}",
  fork_turns="none",
  reasoning_effort="low" if FINDING_COUNT <= 25 else "medium",
  message="
You are the Report Assembler. Merge the tier sections into the final report.

## Inputs
- {{SCRATCHPAD}}/report_index.md (header info, summary counts, cross-references)
- {{SCRATCHPAD}}/report_critical_high.md
- {{SCRATCHPAD}}/report_medium.md
- {{SCRATCHPAD}}/report_low_info.md
- {{SCRATCHPAD}}/design_context.md (for Executive Summary; or write your own from findings)
- {{SKILL_ROOT}}/rules/report-template.md (canonical structure)

## Method
1. Assemble sections in order:
   - Report header (project name, date, scope, build status, platform)
   - Executive Summary (3 paragraphs, plain English, 1: what the protocol does, 2: how many issues + worst one in user terms, 3: top 3 recommendations as bullets)
   - Summary table (severity counts)
   - Components Audited table (from contract_inventory)
   - Critical Findings (paste from report_critical_high.md)
   - High Findings (paste from report_critical_high.md)
   - Medium Findings (paste from report_medium.md)
   - Low Findings (paste from report_low_info.md)
   - Informational Findings (paste from report_low_info.md)
   - Priority Remediation Order (numbered list, Critical → High → Medium)
   - Appendix A: Internal Audit Traceability (paste Master Finding Index + Excluded Findings from report_index.md)

2. Quality gates before writing the file:
   a. Finding count matches Summary table per tier (count ### sections)
   b. NO internal IDs in body — grep for [CS-, [AC-, [TF-, [BLIND-, [EN-, [SE-, [VS-, [DEPTH-, [SLITHER-, CH-, and bracketed H-N. None outside Appendix A.
   c. Cross-references valid — every 'see X-NN' points to an existing finding
   d. No duplicate findings — no two sections describe the same bug
   e. Plain-English self-check passes (4-sentence shape, Impact has $/%, Recommendation has fix sentence + diff + result sentence)

3. Write to {{PROJECT_ROOT}}/AUDIT_REPORT.md

4. Write quality check log to {{SCRATCHPAD}}/report_quality.md:
   # Report Quality Check
   - Finding count: PASS/MISMATCH
   - Internal ID leak: CLEAN/FOUND <list>
   - Cross-references: VALID/BROKEN <list>
   - Duplicates: NONE/FOUND
   - Plain-English style: PASS/<N violations>
   - Fixes applied: <list>

SCOPE: write to {{PROJECT_ROOT}}/AUDIT_REPORT.md and {{SCRATCHPAD}}/report_quality.md only. Return 'DONE: report assembled, N findings, quality=PASS|ISSUES' and stop.
"
)
```

---

## STEP 3 — Report structure (canonical)

The final `AUDIT_REPORT.md` MUST follow this structure. Tier writers and the Assembler use this as the source of truth.

```markdown
# Security Audit Report — <Project>

**Date**: YYYY-MM-DD
**Auditor**: DewaxGuard <VERSION>
**Scope**: <description from design_context.md>
**Platform**: <C4|Sherlock|Cantina|Immunefi|HackenProof|unspecified>
**Build Status**: <Compiled successfully | Failed - reason>
**Language/Version**: <from build_status.md>

---

## Executive Summary

(3 paragraphs, plain English, for a non-technical project lead:
 1. What the protocol does (1-2 sentences)
 2. How many issues found + how bad the worst one is in user terms
 3. Top 3 recommendations as a bulleted list)

## Summary

| Severity | Count |
|----------|-------|
| Critical | <N> |
| High | <N> |
| Medium | <N> |
| Low | <N> |
| Informational | <N> |

### Components Audited

| Component | Path | Lines | Description |
|-----------|------|-------|-------------|

---

## Critical Findings

### [C-01] <Title> [VERIFIED]
(full section per finding-output-format.md)

---

## High Findings

### [H-01] <Title> [VERIFIED|UNVERIFIED|CONTESTED]

---

## Medium Findings

### [M-01] <Title> [VERIFIED|UNVERIFIED|CONTESTED]

---

## Low Findings

### [L-01] <Title>

---

## Informational Findings

### [I-01] <Title>

---

## Priority Remediation Order

1. **C-01**: <one-line reason> — Immediate
2. **H-01**: <one-line reason> — Before launch
...

---

## Appendix A: Internal Audit Traceability (optional, audit-team-only)

| Report ID | Internal Hypothesis | Chain | Verification | Agent Sources |
|-----------|---------------------|-------|--------------|---------------|

### Excluded Findings

| Internal ID | Severity | Title | Exclusion Reason |
```

---

## STEP 4 — Per-finding format

Use the worked H-01 example from `{{SKILL_ROOT}}/rules/report-template.md` as the canonical style reference. Every finding section follows:

```markdown
### [X-NN] <Title> [VERIFIED|UNVERIFIED|CONTESTED]

**Severity**: Critical/High/Medium/Low/Informational
**Location**: `File:L<n>-L<m>`
**Evidence**: [FORK-PASS] / [POC-PASS] / [CODE-TRACE]
**Confidence**: HIGH/MEDIUM/LOW (<reason — N agents confirmed, validator score>)
**Validation Score**: XX/100 (platform: <C4/Sherlock/...>)

**Description**:
(Four sentences per plain-english-style.md:
 1. What is wrong (function name + missing check)
 2. Why that matters (what the check would have prevented)
 3. Who can trigger it (actor in plain words)
 4. What the user sees (money loss, locked funds, blocked action))

Include the smallest code snippet that proves point 1.

**Impact**:
Concrete user-level harm with $ or %. Examples:
- "User loses 100% of their deposit (e.g. $10k from a 10k USDC deposit)."
- "Pool stops accepting withdrawals for everyone until admin pauses and migrates."

**PoC Result**: <test command + key assertion line + plain-English attack story>

**Recommendation**:
1. <One sentence fix>
2. <Code diff>
3. <One sentence on what the fix prevents>
```

---

## STEP 5 — Platform impact quantification (Medium+ findings)

For every Medium-or-higher finding, the Impact field MUST include platform-specific numbers per `rules/report-template.md`:

### Sherlock
- Concrete dollar amount of loss
- Percentage of principal / yield / fees
- State the threshold: "above Sherlock's Medium bar of > 0.01% of TVL AND > $10"
- For DoS: permanent vs temporary + what users can no longer do

### Code4rena
- High: explain direct loss with a realistic scenario in one sentence
- Medium: list conditions required + likelihood in plain language

### Cantina
- Impact axis (High/Medium/Low) + user harm
- Likelihood axis (High/Medium/Low) + triggering action
- Matrix cell

### Immunefi
- Map to impact category from their severity table — name the category
- State attack cost (gas, capital, time) and value extracted in dollars

---

## STEP 6 — Quality gates (mandatory before writing AUDIT_REPORT.md)

Before saving the report, verify:

1. **Finding count consistency**: `count(### sections per tier) == Summary table count per tier`
2. **No internal IDs in body**: grep the assembled text for `[CS-`, `[AC-`, `[TF-`, `[BLIND-`, `[EN-`, `[SE-`, `[VS-`, `[DEPTH-`, `[SLITHER-`, `[DTF-`, `[DST-`, `[DEC-`, `[DEX-`, `[DLL-`, `[DRT-`, `CH-`, and bracketed `H-` followed by a number in the body. NONE outside Appendix A.
3. **Cross-references valid**: every `see X-NN` reference points to a finding that exists
4. **No duplicate findings**: no two `###` sections describe the same bug at the same location
5. **Plain-English style** (5-point self-check per report-template.md):
   - Every finding has the 4-sentence Description shape
   - Every Impact uses $ / % / clear user-action verb
   - Every Recommendation has fix-sentence + diff + result-sentence
   - Zero banned-jargon words from plain-english-style.md survive without a one-sentence definition
   - No sentence > 25 words

If any check fails, fix the issue in the assembled output BEFORE writing AUDIT_REPORT.md. Document fixes in `{{SCRATCHPAD}}/report_quality.md`.

---

## Required outputs (driver gate checks for these)

- `{{PROJECT_ROOT}}/AUDIT_REPORT.md` — must contain Executive Summary + ≥ 3 of the severity-bucket sections (Critical/High/Medium/Low/Informational)

## Retry hint (if any)

{{RETRY_HINT}}

When `AUDIT_REPORT.md` is written, passes the 6 quality gates, and `report_quality.md` records the result, exit cleanly. This is the last phase — no further work.
