---
name: dewaxguard:batch-import
description: "Bulk-process public audit reports from Code4rena, Sherlock, Cantina. Run /dewaxguard improve against multiple contests in one session for rapid methodology improvement."
user-invocable: false
---

# DewaxGuard Batch Import

> **Invoked by**: `/dewaxguard batch-import`
> **Purpose**: Process multiple public audit reports in one session to rapidly identify methodology gaps.
> **Speed**: 10+ audits per hour vs 1 per month with manual improve cycles.

---

## How It Works

Instead of auditing a codebase and waiting for results, you feed DewaxGuard published contest results and let it analyze what it WOULD have missed.

```
Input:  Public audit report (Code4rena, Sherlock, Cantina results)
        + The audited codebase (cloned from the contest repo)

Process: For each validated finding in the report:
         1. Read the finding description + affected code
         2. Check: does DewaxGuard's methodology cover this class?
         3. If NO → classify root cause → propose fix

Output: Aggregated methodology gaps across all imported audits
```

---

## Phase 1: Source Collection

Ask the user for sources. Supported formats:

### Option A: Contest URL
```
Platform: c4 / sherlock / cantina
Contest URL or repo: https://github.com/code-423n4/2024-XX-projectname-findings
```

The agent clones the findings repo + the contest repo.

### Option B: Local Files
```
Findings report: ./path/to/report.md
Codebase: ./path/to/contest-repo/
```

### Option C: Batch List
```
Provide a list of contests to process:
1. c4: https://github.com/code-423n4/2024-XX-findings
2. sherlock: https://github.com/sherlock-audit/2024-YY-judging
3. ...
```

### Option D: Reproduced-exploit corpus (DeFiHackLabs / crypto.training)

A library of real on-chain hacks with root-cause + standalone Foundry PoC (e.g.
[crypto.training/hacks](https://crypto.training/hacks/), adapted from
SunWeb3Sec's DeFiHackLabs). Hundreds of entries, categorized by class/chain/year.
This is a **learning input**, not a pattern store — the same Anti-Anchoring Rules
below apply: the specific exploits never persist; only class-level methodology and
(optionally) blind benchmarks do.

Because this source is uniform (each entry = class + root-cause + PoC), it has a
deterministic backbone script — you do NOT hand-run the coverage check per entry:

```bash
# 1. Normalize the corpus to JSON (one object per exploit; see the schema at the
#    top of scripts/import_exploits.py). Example shape: scripts/fixtures/exploit-corpus.sample.json
# 2. Class-level coverage + failure-mode candidates (the mechanical Phase 3+4):
python3 scripts/import_exploits.py --corpus corpus.json
# 3. Also scaffold blind benchmarks for entries carrying a `benchmark` block:
python3 scripts/import_exploits.py --corpus corpus.json --scaffold-benchmarks benchmarks/
```

The script does the keyword co-occurrence coverage check (COVERED / PARTIAL /
NOT_COVERED per class), aggregates by `(class, language)`, applies the same
`>= min-occurrences` recurrence filter, and emits paste-ready `failure-modes/INDEX.md`
rows (merged against existing FM rows) plus benchmark scaffolds. Its persisted
output carries **only** generic class + language + root cause — never a protocol
name, loss, or date (it strips those by construction). The LLM's job is then to
review its candidates (Phase 3 refinement below), write the minimal fork-free
benchmark contracts, and turn NOT_COVERED recurring classes into M-template
proposals (Phase 5).

---

## Phase 2: Finding Extraction (per contest)

For each contest, extract validated findings:

### Code4rena Format
- Read the findings repo's `report.md` or individual issue files
- Filter: only `high` and `medium` labeled issues (skip QA/gas)
- Extract: title, severity, affected file:line, root cause description

### Sherlock Format
- Read `{issue-number}.md` files in the judging repo
- Filter: issues labeled `valid` with severity `high` or `medium`
- Extract: title, severity, affected code, root cause

### Cantina Format
- Read the published report PDF/MD
- Extract: title, severity, affected code, root cause

### Normalized Finding Format (per finding):
```markdown
## GT-{N}: {title}
- Severity: {High/Medium}
- Language: {evm/solana/aptos/sui}
- Location: {file:line}
- Class: {vulnerability class — e.g., "reentrancy", "oracle manipulation", "access control"}
- Root Cause: {1-2 sentence description}
- Code: {relevant snippet if available}
```

---

## Phase 3: Methodology Coverage Check (per finding)

For each extracted finding, run a LIGHTWEIGHT version of the RC-AGENT Exclusion Test:

### Step 1: Keyword Search
Grep `~/.agents/skills/dewaxguard/{agents,rules,prompts,references}` for keywords from the finding's vulnerability class.

Result:
- **COVERED**: Existing methodology addresses this class → skip (equivalent to RC-AGENT)
- **PARTIAL**: Related methodology exists but doesn't cover this specific variant → flag
- **NOT COVERED**: Zero relevant methodology → flag as gap

### Step 2: Classify Gaps (only for PARTIAL and NOT COVERED)
Apply same root cause codes:
- RC-METHOD: No rule/skill covers this class
- RC-DEPTH: Coverage exists but too shallow for this variant
- RC-SCOPE: The affected area wouldn't be analyzed (recon gap)

### Step 3: Generalizability Test
For each gap: "Would this same class of bug appear in OTHER protocols?"
- YES → worth fixing
- NO (protocol-specific edge case) → skip

---

## Phase 4: Aggregation Across Contests

After processing all contests, aggregate:

```markdown
# Batch Import Summary

## Contests Processed: {N}
## Total Validated Findings Analyzed: {N}

## Coverage Results
| Status | Count | % |
|--------|-------|---|
| COVERED (methodology exists) | XX | XX% |
| PARTIAL (shallow coverage) | XX | XX% |
| NOT COVERED (gap) | XX | XX% |
| Protocol-specific (skip) | XX | XX% |

## Top Methodology Gaps (by frequency)
| Gap | Occurrences | Contests | Severity | RC Code |
|-----|------------|----------|----------|---------|
| {class description} | 5 | A, B, C, D, E | High | RC-METHOD |
| {class description} | 3 | A, C, F | Medium | RC-DEPTH |
| ... | ... | ... | ... | ... |

## Proposed Fixes (sorted by frequency × severity)
1. {fix proposal — covers 5 occurrences across 5 contests}
2. {fix proposal — covers 3 occurrences across 3 contests}
```

### Priority Rule
Only propose fixes for gaps that appear in **2+ contests**. Single-occurrence gaps are likely protocol-specific noise.

---

## Phase 5: Apply (with user approval)

Same as `/dewaxguard improve` Phase E:
1. Present proposals to user
2. Apply approved changes
3. Version bump + CHANGELOG + MEMORY entry
4. Git push

### MEMORY.md entry format for batch imports:
```
| {version} | {date} | batch({N}) | {language} | - | - | {RC counts} | - | batch |
```

The `batch({N})` in Project Type column and `-` in Recall/Precision columns distinguish batch entries from single-audit entries (we can't compute recall without running the pipeline).

---

## Suggested Starting Contests

For bootstrapping, process these high-quality public audits:

### EVM
- Code4rena: recent vault/lending/DEX contests (rich in accounting bugs)
- Sherlock: recent contests with >10 valid findings (dense finding sets)

### Solana
- Code4rena/Sherlock Solana contests (fewer but growing)
- Neodyme blog posts (detailed Solana vulnerability analyses)

### Move
- MoveBit audit reports (Aptos/Sui specific)
- OtterSec Sui/Aptos reports

---

## Anti-Anchoring Rules

1. **NEVER** store specific finding descriptions in any persistent file
2. **NEVER** add specific bug instances to attack-vectors.md — only generic class descriptions
3. Extracted findings exist ONLY in conversation context
4. What persists: methodology changes (HOW to look) + MEMORY.md metrics entry
5. The skill must approach the NEXT audit with zero knowledge of these specific findings
