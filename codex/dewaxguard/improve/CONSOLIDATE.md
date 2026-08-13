---
name: dewaxguard:consolidate
description: "Review skill files for bloat, redundancy, and overlap. Propose merges, removals, and compressions. Enforce file size caps."
user-invocable: false
---

# DewaxGuard Consolidation Sweep

> **Invoked by**: `/dewaxguard consolidate`
> **Also triggered**: When `improve` detects any file above 80% of its cap.

---

## Step 1: Census

Run line counts on every file in `~/.agents/skills/dewaxguard/`. Present as table:

```
File                                          Lines   Cap    Usage%
SKILL.md                                        XXX   350      XX%
agents/hacking-agents/vector-scan-agent.md       XX    80      XX%
...
references/attack-vectors/attack-vectors.md    XXXX  1500      XX%
```

Flag files above 80% cap usage with `<<<`.

### File Size Caps

| Category | Cap | Rationale |
|----------|-----|-----------|
| SKILL.md | 350 | Core prompt, loaded every audit |
| Hacking agents (each) | 80 | Loaded into agent context with source |
| Depth agents (each) | 100 | Same |
| Nemesis agents (each) | 80 | Same |
| Per-language templates (each) | 150 | Loaded alongside depth agents |
| attack-vectors.md | 1500 | Reference doc, selectively loaded |
| Rules (each) | 200 | Reference for specific phases |
| Criteria (each) | 200 | Reference for validator |
| MEMORY.md | 80 | Metrics only |
| CHANGELOG.md | 150 | Rolling window |

---

## Step 2: Redundancy Scan

For file groups that share a logical domain:
- All 4 language-specific lowlevel templates
- All 4 language-specific runtime templates
- All 8 hacking agent files

1. Extract methodology verbs and their objects
2. Identify instructions appearing in 3+ files with >60% textual similarity
3. Propose extraction to shared location (e.g., `rules/shared-checks.md`)

---

## Step 3: Overlap Detection in attack-vectors.md

1. For each entry, extract core vulnerability class
2. Find entries where descriptions overlap >60% in concept
3. Propose merging overlapping entries (keep the more comprehensive one)

---

## Step 4: Stale Content Detection

1. Read MEMORY.md for root cause distributions across recent audits
2. If a methodology change from a past version correlates with RC-AGENT dominance in subsequent audits → flag for review (the change may not be helping)
3. If an attack vector entry has never matched a finding across 5+ audits → flag as potentially stale

---

## Step 5: Proposals

Present all actions as a numbered list:

| Action | Description | Lines Saved |
|--------|-------------|-------------|
| MERGE | Combine entries X and Y in attack-vectors.md | -N |
| EXTRACT | Move shared content to shared location | -N |
| REMOVE | Delete stale/unused content | -N |
| COMPRESS | Rewrite verbose section more concisely | -N |
| ARCHIVE | Move old CHANGELOG/MEMORY entries to summary | -N |

User approves each individually. Then apply:
1. Make approved changes
2. Version bump (MAJOR if structural, PATCH otherwise)
3. Update CHANGELOG.md
4. Git commit and push

---

## MEMORY.md Archival (automatic when >50 rows)

When MEMORY.md exceeds 50 data rows:
1. Take the oldest 25 rows
2. Compute averages: recall%, precision%, dominant RC code
3. Replace with single summary line:
   ```
   | v1.0-v1.12 | archived | avg | mixed | 68% | 82% | 2 | 3 | 4 | 1 | 43 | 0 | 5 |
   ```
4. Keep the 25 most recent rows as-is

---

## CHANGELOG.md Archival (automatic when >20 versions)

When CHANGELOG.md exceeds 20 version entries:
1. Collapse oldest entries into:
   ```
   ## [1.0.0 - 1.5.0] - Archived
   See git history for details.
   ```
2. Keep last 15 versions with full details
