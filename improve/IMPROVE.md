---
name: dewaxguard:improve
description: "Post-audit self-improvement. Compares pipeline output vs ground truth, classifies misses, proposes minimal methodology fixes. Requires ground truth report."
user-invocable: false
---

# DewaxGuard Self-Improvement Protocol

> **Invoked by**: `/dewaxguard improve`
> **Principle**: Improve HOW agents analyze, never WHAT specific bugs to find.
> **Anti-anchoring**: NOTHING from the comparison persists except approved methodology changes and one-line metrics.

---

## Phase A: Input Collection

1. Ask the user for:
   - Path to the pipeline's `AUDIT_REPORT.md`
   - Ground truth source: contest results URL, pasted report, or file path
   - Language (`evm`/`solana`/`aptos`/`sui`) and project type (vault, DEX, lending, etc.)
2. Read both reports into conversation context

---

## Phase B: Structured Comparison (IN-SESSION ONLY — never write to disk)

1. Extract all findings from both reports (ID, severity, title, location, root cause)
2. Build **Finding Alignment Matrix** (conversation context only):

```
| GT ID | GT Sev | GT Title | Match? | Pipeline ID | Pipeline Sev | Delta |
|-------|--------|----------|--------|-------------|-------------|-------|
```

Match by: location overlap > title similarity > vulnerability class

3. Classify each:
   - GT finding with pipeline match → **MATCHED**
   - GT finding with partial match (wrong severity/incomplete) → **PARTIAL**
   - GT finding with no match → **MISSED** (false negative)
   - Pipeline finding with no GT match → **EXTRA** (false positive)

4. Compute metrics:
   - **Recall** = (MATCHED + PARTIAL) / total_GT
   - **Precision** = (MATCHED + PARTIAL) / total_pipeline
   - **Severity accuracy** = exact_sev_match / MATCHED

5. Present metrics to user before proceeding

---

## Phase C: Root Cause Classification (per MISSED finding)

### MANDATORY FIRST: RC-AGENT Exclusion Test

For EVERY missed finding, run this test BEFORE any other classification:

```
RC-AGENT EXCLUSION TEST (all 3 must be YES to proceed past RC-AGENT):

1. METHODOLOGY SEARCH: Grep ~/.claude/skills/dewaxguard/{agents,rules,prompts,references}
   for keywords related to this vulnerability class.
   → Did the search find ZERO relevant coverage? [YES/NO]
   → If NO (coverage exists): DEFAULT TO RC-AGENT. Stop.

2. REASONING TRACE: If scratchpad/intermediate output is available, check whether
   any agent analyzed the relevant function/area.
   → Did the agent SKIP the area entirely (no mention)? [YES/NO]
   → If NO (agent analyzed it but reached wrong conclusion): DEFAULT TO RC-AGENT. Stop.

3. METHODOLOGY GAP PROOF: State in ONE sentence what specific methodology instruction
   is missing — not "the agent should have checked X" (that's a pattern) but
   "no existing rule tells the agent HOW to systematically discover this class of bug."
   → Can you state this without referencing the specific missed finding? [YES/NO]
   → If NO: DEFAULT TO RC-AGENT. Stop.
```

**If any answer is NO → classify as RC-AGENT. No pipeline change.**

### Root Cause Codes (only if exclusion test passes all 3)

| Code | What Failed | Fix Strategy |
|------|-------------|-------------|
| **RC-SCOPE** | File/function not analyzed by any agent | Recon improvements |
| **RC-METHOD** | No rule/skill/check covers this class | New skill or scanner check |
| **RC-DEPTH** | Correct area but too shallow | Adjust depth directive |
| **RC-CONTEXT** | Lacked domain knowledge | Recon doc ingestion |
| **RC-NOVEL** | Unprecedented class, no prior art | RAG entry only |
| **RC-AGENT** | Agent had methodology but made reasoning error | **NO PIPELINE CHANGE** |

**When in doubt between RC-AGENT and any fix-eligible code, default to RC-AGENT.**

Present classification table with evidence chains to user.

---

## Phase D: Fix Proposals (per fix-eligible miss)

For each non-RC-AGENT/RC-NOVEL miss, walk the decision tree:

```
Is the gap covered by an EXISTING rule/skill/check?
├── YES → Re-run RC-AGENT Exclusion Test question 1
│   ├── Coverage exists but fails to trigger → trigger-fix (~2 lines)
│   └── Coverage exists and triggered → RC-AGENT, no fix
└── NO → Is the vulnerability class generalizable (2+ protocol types)?
    ├── YES → Extends existing component? → extend (~5-10 lines)
    │         No natural home? → new-injectable (~50-100 lines)
    └── NO → RAG entry only (0 pipeline lines)
```

### Anti-Bloat Gates (MANDATORY before any extend or higher)

| Gate | Check |
|------|-------|
| **Line budget** | Target file stays under cap? (agents: 80, templates: 150, attack-vectors: 1500, SKILL.md: 350) |
| **Duplication** | Change touches 4+ files with identical text? → shared location instead |
| **Methodology test** | Teaches HOW to look (proceed) vs WHAT to find (reject → RAG only) |
| **Overlap** | >60% keyword overlap with existing check? → merge, don't create new |

### Generate Improvement Proposal per fix:

```markdown
# Proposal: {title}
- **Root cause**: {RC-code}
- **Change type**: {trigger-fix / extend / new-injectable / rag-entry}
- **Files modified**: {list with line deltas}
- **Anti-bloat gates**: all passed / {which failed}
- **Methodology test**: HOW (proceed) / WHAT (reject)
- **Could produce false positives?**: {assessment}
```

Present all proposals as a numbered list. Wait for user approval.

---

## Phase E: Implementation (approved changes only)

1. Apply each approved change using Edit/Write tools
2. **Attack vector auto-update** (if user confirms):
   - For CONFIRMED findings not matching existing `attack-vectors.md` patterns
   - Add as generic class description in existing D:/FP: format
   - Never add specific bug instances
   - Check 1500-line cap first; if near cap, propose consolidation
3. **Version bump** in `VERSION`:
   - PATCH: trigger-fix, rag-entry, attack-vector additions
   - MINOR: extend, new-injectable
   - MAJOR: structural changes
4. Update `CHANGELOG.md` with changes applied
5. Update `MEMORY.md` with one-line metrics entry:
   ```
   | {version} | {date} | {project_type} | {language} | {recall} | {precision} | {RC counts...} | {reclassified} |
   ```
6. Git sync:
   ```bash
   cd ~/.claude/skills/dewaxguard
   git add -A
   git commit -m "v{VERSION}: {1-sentence summary}"
   git push origin main
   ```

---

## HARD RULES

1. **NEVER** write the Finding Alignment Matrix to any file
2. **NEVER** store specific finding titles, descriptions, or locations persistently
3. **NEVER** modify pipeline files without user approval
4. **ALWAYS** run RC-AGENT Exclusion Test before classifying any miss
5. **ALWAYS** check anti-bloat gates before any extend or higher change
6. MEMORY.md records ONLY: version, date, type, language, recall%, precision%, RC distribution counts
7. If user challenges a non-RC-AGENT classification, re-run the exclusion test
