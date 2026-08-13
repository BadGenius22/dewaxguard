# Agent Failure Recovery Protocol

> **Origin**: K2 audit Pass 7 (2026-05-05). 4 parallel verifier agents hit a usage-credit cap mid-run and returned `You're out of extra usage` with zero output. The orchestrator fell back to direct verification, which produced 3 false negatives that the agent retry later corrected.
>
> **Status**: MANDATORY for all multi-agent passes.

---

## Why Manual Fallback Is Forbidden

When agents fail mid-pass, the orchestrator's instinct is to fall back to direct Read/Grep verification. The K2 audit demonstrates this introduces false negatives:

| Hypothesis | Manual orchestrator verdict | Agent retry verdict | Delta |
|------------|----------------------------|---------------------|-------|
| HF50 (oracle self-consistency) | REFUTED | **REFINED → Informational** (intra-tx baseline mutability) | Manual missed nuance |
| HF51 (try_invoke_contract sweep) | "PARTIAL — already filed" | **PARTIAL → 3 new Info observations** including QA-05 | Manual missed novel finding |
| HF44 → HF60 reclassification | Parked in ADDITIONAL_LEADS as unsafe | **SAFE — uses `invoke_contract` (panics on error), not `try_`** | Manual incorrectly flagged |

The orchestrator's direct verification produces lower-resolution analysis than dedicated agents because:
1. The orchestrator's context is shared with prior reasoning — anchoring bias toward "already concluded"
2. The orchestrator doesn't have the depth-* agent's specialized methodology prompt
3. Manual time pressure encourages "good enough" verdicts vs exhaustive sweeps

---

## The Protocol

### When an agent returns failure

Failure modes that trigger this protocol:
- `You're out of extra usage` (rate-limit cap)
- `Error: ...` from the agent runtime
- Agent returns 0 lines or ≤50 tokens of actual output
- Agent timeout after the configured budget

### Step 1 — Detect

The orchestrator MUST check each agent's return for:
- Non-zero output length (≥500 tokens)
- Presence of a `DONE:` line at the end
- A verdict string for each requested hypothesis

If any check fails → agent failed → enter recovery.

### Step 2 — Wait for cap reset (if rate-limited)

If the failure mode is `You're out of extra usage`:
1. Surface this to the user IMMEDIATELY — do not proceed
2. Note the reset time from the error (e.g., "resets 3pm Asia/Jakarta")
3. Set a wakeup or wait for user re-invocation
4. Do NOT fall back to direct verification

### Step 3 — Retry agents (after cap reset)

Re-spawn the failed agents with:
- Same prompt (no changes — the original was correctly scoped)
- Same model
- Same tool budget

If the retry succeeds, proceed normally.

### Step 4 — Document the gap

If retry also fails (true agent infrastructure failure, not rate limit):
1. Write `{SCRATCHPAD}/agent-failure-{date}.md` documenting which hypotheses were left unverified
2. The orchestrator's report MUST explicitly mark these hypotheses as `UNVERIFIED — agent failure`
3. The bug validator (Phase 5d) MUST cap unverified findings at Low severity
4. The orchestrator MAY do direct verification as a LAST RESORT, but EVERY direct-verification verdict MUST be tagged `[ORCHESTRATOR-DIRECT]` so the post-audit retro can flag the false-negative risk

---

## Forbidden Patterns

❌ **"For time efficiency, I'll do this myself"** — the K2 audit shows this introduces false negatives. The cost of waiting for cap reset is far less than the cost of shipping wrong verdicts.

❌ **"The agent's prompt was too complex; let me simplify and retry"** — original prompt was scoped correctly. Simplification introduces another variable. Retry the same prompt.

❌ **"I'll do a quick grep to confirm"** — quick greps confirm anchoring bias. The agent's full sweep is necessary.

❌ **"This is too late in the audit; let me ship without verification"** — unverified findings ARE worse than no findings. They invite contested submissions and waste reviewer time.

---

## Allowed Patterns

✅ **Wait for cap reset** — even if it means deferring the audit by hours

✅ **Re-spawn the agent with identical prompt** — exactly once per failure

✅ **Document unverified hypotheses with severity cap** — explicit limitation is better than implicit gap

✅ **Surface the failure to the user** — they may have additional credit pools or alternate solutions

---

## Validated Recovery

K2 Pass 7+8 retry: After agents hit usage cap on first attempt, the orchestrator (incorrectly) did direct verification. After user explicitly requested retry via `$dewaxguard core`, all 7 agents successfully completed and:
- Confirmed 14 of 17 hypotheses (matching manual verdicts)
- **Corrected 3 manual verdicts** (HF50 → Informational, HF51 → 3 new observations, HF44 reclassified SAFE)
- Surfaced 1 new QA-Info entry (QA-05) that manual missed entirely

The retry took ~30 minutes vs ~2 hours of manual orchestrator work. Better quality at lower cost.

---

## Integration Points

- **Phase 3-5 (any agent-spawn point)**: Apply this protocol on every agent return
- **Orchestrator self-check**: After spawning N agents, count successful returns. If <N, enter recovery before proceeding to next phase.
- **Report writers (Phase 6)**: Reject any finding tagged `[ORCHESTRATOR-DIRECT]` from main report unless the underlying methodology has independent reliability evidence

---

## Why This Is Hard for Orchestrators

The orchestrator is naturally biased toward "completing the audit." Agent failures feel like an obstacle to route around. But the audit's value is in **verified findings**, not completion. An incomplete audit with retried agents > a complete audit with manual fallbacks.

This protocol exists because the orchestrator's instinct will fight it. Mandatory means mandatory.
