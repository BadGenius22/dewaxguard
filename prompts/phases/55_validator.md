# Phase: Bug Validator (Phase 5d, v1.13.1 driver)

> Fresh `claude -p` subprocess. No prior context. Treat this prompt as your entire task.
> This phase runs AFTER verify (Phase 5) and BEFORE report (Phase 6).
>
> **Model tier: commander / decision gate.** Per `rules/model-tiering.md`, this phase runs at the commander tier (`--commander-model`, default `opus`; `fable` applies the ClaudeDevs "premium advisor at decision points" pattern). Platform accept/reject scoring is low-token, high-judgment — exactly the kind of bounded, verifiable decision where the strongest model earns its cost. Do all scoring in this subprocess; do not spawn sub-agents.

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

**Gate 1b — Upstream patch status (bounty engagements only)**

> **Applies ONLY when the engagement is judged against LIVE / current code** — Immunefi, HackenProof, Cantina bounty, or any "is this exploitable today?" program. **SKIP for contests judged on a pinned commit** (Code4rena competitive, Sherlock competitive): there, an upstream fix landing after the audit snapshot does NOT invalidate a finding on the audited commit, and rejecting on that basis would discard valid submissions.

Cheap (one git fetch) and placed before the PoC gate so an already-fixed bug never burns a verification slot.

```bash
python3 {{SKILL_ROOT}}/scripts/patch_status.py \
    --repo {{PROJECT_ROOT}} \
    --path <finding location.file> \
    --commit <audited commit, or HEAD> \
    --pickaxe '<the vulnerable expression, pasted literally from the finding>'
```

Read the `status` field:

| status | Meaning | Action |
|---|---|---|
| `available` + a diff/commit touching the finding's code | Upstream moved past the audited commit AND changed this code | Read the diff. If it removes the vulnerability → `gate1b_patch_status: FAIL — fixed upstream in <sha>` and **reject**, naming the exact fixing commit. |
| `available`, empty diff, no pickaxe hit | Upstream moved but never touched this code | Not patched — proceed. |
| `current_default` | The audited commit IS the current upstream HEAD | Nothing has moved — proceed. |
| `unavailable` | No comparison was possible (no network, fork, rewritten history, local-mirror origin) | **No conclusion exists.** Proceed to the next gate and record `patch_status: NEEDS_MANUAL_REVIEW` with the tool's `reason`. |

`unavailable` means *unknown* — never read it as "not patched", and never as "patched". Do not claim to have run any git command whose output is not in this script's JSON.

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

**Gate 4a — Grief economics (HARD; availability/griefing findings only)**

If the finding's impact is **availability** (DoS, queue/batch blocking, liveness, bricking) rather than theft, fund loss, or accounting drift, a `b=YES` answer is **provisional**. Run all three gates from `{{SKILL_ROOT}}/rules/severity-matrix.md` → *Grief economics*. Any FAIL caps the finding at **Low** and routes it to the QA/Low bundle (do NOT reject — the defect is usually real):

```
G1 economic rationality: is the attacker's UNRECOVERABLE cost < the quantified victim harm?
G2 operator recovery:    can a routine privileged action (treasury fill, admin skip, re-queue)
                         restore service with no funds lost?              → YES = FAIL
G3 quantification:       are BOTH `attacker_cost:` and `victim_harm:` declared with figures?
```

**Self-admission scan (mechanical, do this literally).** Grep the finding's own Description / Impact / Recommendation prose for a conceded recovery path:

```
TREASURY can | admin can | owner can | operator can | governance can
can still recover | can still operate | manual fill | manually filling | work around | fill around
```

A hit means the writeup has already conceded **G2**. Treat it as `operator_recoverable: true` and cap at Low unless the finding explicitly carries `operator_recoverable: false` with a justification. A writeup that argues *High → Medium* on the strength of a recovery path has conceded the same fact that argues *Medium → Low*.

Emit the verdict in `severity_check:`:
```
severity_check: a=NO, b=YES (liveness) → MEDIUM;
                G2 FAIL — impact text concedes "the TREASURY can still recover funds"
                → cap LOW
```

> **Origin (DRE, Sherlock 2026-07)**: a real wrong-list DoS defect shipped as Medium with a passing end-to-end fork PoC and was rejected — *"attacker will lose way more than the party being affected."* The writeup itself contained the disqualifier and used it only to argue down from High. **A passing PoC does not clear these gates**: an executable oracle proves the mechanism, never the economics.

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
