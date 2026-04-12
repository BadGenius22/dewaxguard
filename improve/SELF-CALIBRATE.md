---
name: dewaxguard:self-calibrate
description: "Auto-runs after every audit. Analyzes internal disagreements, PoC failures, and confidence patterns to reduce false positives and tune agent behavior. No ground truth needed."
user-invocable: false
---

# DewaxGuard Self-Calibration

> **Trigger**: Automatically after Phase 5 verification completes, before Phase 6 report.
> **No ground truth needed** -- uses signals the pipeline already generates.
> **Improves**: Precision (fewer false positives). Does NOT improve recall.

---

## Phase 1: Signal Collection

Read these scratchpad artifacts from the current audit:

| Signal Source | File | What It Tells Us |
|---|---|---|
| Agent disagreements | `findings_inventory.md` | Findings where agents contradicted each other |
| PoC failures | `verify_batch*.md` | Findings where PoC was written but FAILED |
| Low confidence | `confidence_scores.md` | Findings that stayed < 0.4 after all iterations |
| Severity downgrades | `hypotheses.md` vs `report_index.md` | Findings that started HIGH but ended LOW/INFO |
| FALSE_POSITIVE verdicts | `verify_batch*.md` | Findings explicitly rejected by verifiers |

### Extract per-agent stats:

For each of the 8 breadth agents + 6 depth agents, compute:

```
Agent: {agent_name}
  Total findings produced: {N}
  Confirmed by verifier: {N} ({%})
  FALSE_POSITIVE by verifier: {N} ({%})
  PoC FAILED: {N} ({%})
  Confidence < 0.4: {N} ({%})
  FP Rate = (FALSE_POSITIVE + POC_FAILED) / Total
```

---

## Phase 2: Pattern Detection

### 2a: Agent-Level FP Patterns

Flag agents with FP rate > 50%:

```
ALERT: {agent_name} produced {N} findings, {M} were false positives ({X}%)
  FP findings: {list with 1-line descriptions}
  Common pattern: {what these FPs have in common}
```

### 2b: Vulnerability Class FP Patterns

Group all FALSE_POSITIVE and POC_FAILED findings by vulnerability class:

```
Vulnerability Class FP Rates:
  Reentrancy:        1/3  (33%) -- acceptable
  Rounding errors:   4/5  (80%) -- FLAGGED
  Access control:    0/4  (0%)  -- clean
  Oracle staleness:  3/4  (75%) -- FLAGGED
```

Flag classes with FP rate > 60%.

### 2c: Language-Specific Patterns

If the audit language is known, check:
- Did language-specific depth agents (lowlevel, runtime) produce useful findings?
- Did any language-specific template produce only FPs?

### 2d: Confidence Score Calibration

Check if confidence scores predicted verification outcomes:
```
Confidence >= 0.7 AND verified CONFIRMED: {N} (should be high)
Confidence >= 0.7 AND verified FALSE_POSITIVE: {N} (should be ~0)
Confidence < 0.4 AND verified CONFIRMED: {N} (under-confident)
Confidence < 0.4 AND verified FALSE_POSITIVE: {N} (correctly flagged)
```

If high-confidence findings are frequently FALSE_POSITIVE → confidence formula may need recalibration.

---

## Phase 3: Calibration Report

Write to `{SCRATCHPAD}/self_calibration.md`:

```markdown
# Self-Calibration Report — {project_name}

## Agent Performance
| Agent | Findings | Confirmed | FP | FP Rate | Status |
|-------|----------|-----------|-----|---------|--------|
| vector-scan | 5 | 3 | 2 | 40% | OK |
| math-precision | 6 | 1 | 5 | 83% | FLAGGED |
| ... | ... | ... | ... | ... | ... |

## Vulnerability Class FP Rates
| Class | Total | FP | Rate | Status |
|-------|-------|-----|------|--------|
| Rounding | 5 | 4 | 80% | FLAGGED |
| ... | ... | ... | ... | ... |

## Confidence Calibration
| Bucket | Confirmed | FP | Calibration |
|--------|-----------|-----|-------------|
| >= 0.7 | 12 | 1 | GOOD (92% accuracy) |
| 0.4-0.7 | 5 | 3 | WEAK (62% accuracy) |
| < 0.4 | 1 | 4 | GOOD (80% correctly flagged) |

## Tuning Proposals
1. {proposal — e.g., "math-precision agent: add guard against flagging intentional truncation patterns"}
2. {proposal}
```

---

## Phase 4: Accumulation (append to MEMORY.md)

After writing calibration report, append a calibration entry to MEMORY.md:

```
| {version} | {date} | {project_type} | {language} | cal | - | FP:{agents flagged} | CLASS:{classes flagged} | CONF:{calibration status} |
```

The `cal` marker in Recall% column distinguishes calibration entries from improve entries.

---

## Phase 5: Auto-Propose (requires user approval)

If the same agent or vulnerability class is FLAGGED across 3+ consecutive calibration entries in MEMORY.md:

1. Read the agent's instruction file
2. Identify the methodology step that produces the false positives
3. Propose a TARGETED tightening:
   - Add a guard condition ("only flag if X AND Y, not X alone")
   - Add a counter-check ("before reporting, verify that Z is not present")
   - Narrow the scope ("apply only to protocols with feature F")
4. Present to user for approval

**NEVER auto-apply.** Always present and wait.

**3-strike rule**: A pattern must appear in 3+ audits before proposing a change. A single bad audit is noise, not signal.

---

## Integration Point

The orchestrator adds this phase to the pipeline between Phase 5 (verification) and Phase 6 (report):

```
Phase 5:    Verification (PoC execution)
Phase 5e:   Self-Calibration (NEW — automatic, no extra cost)
Phase 6:    Report generation
```

Self-calibration reads existing scratchpad artifacts. It does NOT spawn new analysis agents or run new tests. Cost: 1 haiku agent reading files and computing stats.
