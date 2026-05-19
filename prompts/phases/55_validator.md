# Phase: Bug Validator (Phase 5d, v1.13.1 driver)

> Fresh `claude -p` subprocess. No prior context. Treat this prompt as your entire task.
> This phase runs AFTER verify (Phase 5) and BEFORE report (Phase 6).

## Audit context

- **Audit ID**: `{{AUDIT_ID}}`
- **Mode**: `{{MODE}}`
- **Project root**: `{{PROJECT_ROOT}}`
- **Scratchpad**: `{{SCRATCHPAD}}`
- **Skill root**: `{{SKILL_ROOT}}`

## Pre-requisites

- `findings_routed.json` (canonical findings + initial severities)
- `verify_*.md` (≥ 1 verification file with verdicts + PoC results)
- `hypotheses.md` / `chain_hypotheses.md` (from chain phase)

## Your task — per-platform pre-submission gate

For every VERIFIED finding (verdict = CONFIRMED in `verify_*.md`), apply the platform-specific judging criteria from `{{SKILL_ROOT}}/references/criteria/`. The validator answers:

> "If we submit this finding to {platform}, will the judges ACCEPT / REJECT / mark DUPLICATE / OUT_OF_SCOPE / QA?"

Detect the target platform from `{{PROJECT_ROOT}}/CLAUDE.md` (if it has a `Platform:` line) or from `{{SCRATCHPAD}}/CONTEST_FAQ.md`. If neither names a platform, default to running against ALL: Code4rena, Sherlock, Cantina, Immunefi, HackenProof.

### Gate sequence per finding

For each VERIFIED finding, walk these gates in order. Stop at the first FAIL — the finding is rejected.

**Gate 1 — Refutation**

Re-read the finding's `verified:` source quote against the actual file `location.file:location.line_start-line_end`. If the quoted code does NOT match the live source (off by lines, missing modifier, etc.), the finding is invalid. Mark `gate1_refutation: FAIL` and reject.

**Gate 1a — Docs intent (HARD)**

Read `{{SCRATCHPAD}}/docs-intent-map.md` (from recon Phase 1.0). For each intent claim that targets the finding's class:

```
docs_intent_check: NO_MATCH           # no doc claim covers this — proceed
                 | REJECT — {file:line}: doc states '<quote>' which intends this behavior
                 | DOWNGRADE — {file:line}: doc partially excuses this; cap severity at LOW
                 | ESCALATE — {file:line}: doc forbids this; severity floor = MEDIUM
```

REJECT → reject. DOWNGRADE → continue but cap severity. ESCALATE → continue with severity floor.

**Gate 2 — Reachability**

For PoC findings: run the PoC referenced in `verify_<id>.md`. If it doesn't compile or doesn't pass: mark `gate2_reachability: FAIL` and reject.

For CODE-TRACE findings: confirm the entry point is genuinely callable by the claimed actor (permissionless EOA, semi-trusted role, etc.) by tracing modifiers, constructor state, and ownership.

**Gate 3 — Trigger**

Identify the concrete trigger: caller + tx parameters + state precondition. If the trigger requires a coordinated multi-party action and the finding claims a single permissionless attacker, mark `gate3_trigger: FAIL` and reject.

**Gate 4 — Severity decision tree (a/b/c)**

Apply `{{SKILL_ROOT}}/rules/severity-decision-tree.md` IN ORDER. The first YES determines severity:

- (a) Can assets be directly stolen, lost, or permanently locked? → HIGH (CRITICAL if Likelihood: High)
- (b) Else: core protocol broken / availability / accounting drift / invariant break? → MEDIUM
- (c) Else: LOW / QA / Informational

Emit `severity_check:` field with the reasoning:
```
severity_check: a=YES (debt token theft via balance-of mismatch) → HIGH
```

Then apply downgrade modifiers from `{{SKILL_ROOT}}/rules/severity-matrix.md`:
- Fully-trusted actor required → −1 tier (floor: Info)
- View-only impact → cap at Medium
- On-chain-only exploit → −1 tier
- `realism_filter: admin-trust` → −1 tier (per realism-filter.md)

If claimed severity differs from tree result by >1 tier, score deduction applies (see platform scoring below).

**Gate 5 — Realism filter**

Read `{{SKILL_ROOT}}/rules/realism-filter.md`. Apply the per-platform default:

- **Code4rena Competitive**: REJECTS admin-trust findings (severity floor Info)
- **Sherlock Bug Bounty**: ACCEPTS admin-trust at −1 tier
- **Cantina**: depends on contest rules
- **Immunefi**: depends on program scope
- **HackenProof**: depends on contest rules

If a CLAUDE.md `Realism filter` section overrides defaults, use that.

**Gate 6 — Auth-critical-files (when applicable)**

If the finding alleges missing auth/access-control: read `{{SKILL_ROOT}}/rules/auth-critical-files.md` and the actual function body. Emit `auth_check:` field:
```
auth_check: SAW_FULL_BODY:{file:line}   # confirmed
          | SAW_GUARD:{file:line}        # there IS a guard, finding is false-positive
          | SKELETON_ONLY                # could not confirm; downgrade to LEAD
```

**Gate 7 — Plain-English style**

Verify the finding's Description follows the four-sentence shape from `{{SKILL_ROOT}}/rules/plain-english-style.md`. Deduct 5 points per violation (these are stylistic; don't reject the finding, just deduct).

### Platform scoring

For each platform, compute a 0-100 score:

```
score = 100
       - 30 if Gate 1/1a/2/3 FAILed
       - 20 if Gate 5 rejects (realism filter)
       - 15 if severity inflated >1 tier vs decision tree
       -  5 per plain-English violation
       - 10 if auth_check: SKELETON_ONLY
       + 10 if RAG match found (M-25 or solodit precedent)
```

Predicted verdict mapping:
- score ≥ 70: ACCEPT
- 40 ≤ score < 70: ACCEPT with caveats (likely Medium downgrade)
- score < 40: REJECT
- Gate 1a REJECT: REJECT regardless of score
- duplicate detection match (V12 + Kuprum + prior audits): DUPLICATE
- out-of-scope per CLAUDE.md: OUT_OF_SCOPE

### Output

Write `{{SCRATCHPAD}}/validation_results.json` — append to each finding in `findings_routed.json` a `platform_status` object:

```json
{
  "platform_status": {
    "code4rena": {
      "predicted_verdict": "ACCEPT",
      "score": 78,
      "blockers": []
    },
    "sherlock": {
      "predicted_verdict": "ACCEPT",
      "score": 85,
      "blockers": []
    }
  }
}
```

Also write `{{SCRATCHPAD}}/validation_summary.md` with a per-finding table:

```markdown
# Validator Summary — {{AUDIT_ID}}

**Generated**: {{ISO_NOW}}

## Per-finding verdict matrix

| Finding | Severity (claimed → tree) | C4 | Sherlock | Cantina | Immunefi | HackenProof |
|---------|---------------------------|-----|----------|---------|----------|-------------|

## Blockers requiring fix

For each finding scoring < 70 on the target platform, what fix would push it ≥ 70?

| Finding | Platform | Current score | Blocker | Fix |
|---------|----------|--------------|---------|-----|
```

## Required outputs (driver gate checks for these)

- `{{SCRATCHPAD}}/validation_results.json` — valid JSON, every canonical finding has `platform_status`
- `{{SCRATCHPAD}}/validation_summary.md`

## Retry hint (if any)

{{RETRY_HINT}}

When every verified finding has been gated through all 7 gates for every relevant platform, exit cleanly. The report phase reads `validation_results.json` for the per-finding severity floor and the `platform_status` annotations.
