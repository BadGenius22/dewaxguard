# Phase: Depth — 6 Specialized Agents (v1.13.1 driver)

> Fresh `claude -p` subprocess. No prior context. Treat this prompt as your entire task.
> This phase runs AFTER inventory (Phase 4a) and BEFORE chain analysis (Phase 4c).

## Audit context

- **Audit ID**: `{{AUDIT_ID}}`
- **Mode**: `{{MODE}}` (light / core / thorough)
- **Source path**: `{{SRC_PATH}}`
- **Project root**: `{{PROJECT_ROOT}}`
- **Scratchpad**: `{{SCRATCHPAD}}`
- **Skill root**: `{{SKILL_ROOT}}`

## Pre-requisites

`{{SCRATCHPAD}}` must already contain (from prior phases):
- `findings_routed.json` — canonical findings from inventory (v1.12 dedup + severity)
- `attack_surface.md`, `contract_inventory.md`, `state_variables.md` (or whatever recon emitted)
- `static_analysis.md` (or per-language equivalent: `unsafe-map.md`, `guard-map.md`, etc.)
- Language detection result from `preflight.md`

Confirm with `ls {{SCRATCHPAD}}/` before proceeding. If anything is missing, **stop and write the missing-prerequisites diagnostic to `{{SCRATCHPAD}}/depth_failed.md`** rather than continuing.

## Your task

Spawn 6 depth agents in parallel via the Task tool. The standard 4 (Plamen-style) focus on business logic; the 2 NEW agents focus on language and runtime semantics.

### Routing rule

Each canonical finding in `findings_routed.json` is routed to the most relevant depth agent by `bug_class` root token. **Every uncertain canonical finding (composite confidence < 0.7, or severity ≥ Medium) MUST be assigned to at least one depth agent.** Use this routing table (when in doubt, pick the agent on the left):

| bug_class root tokens | Depth agent |
|----------------------|------------|
| token, balance, share, donation, fee, accrual, transfer | depth-token-flow |
| auth, access, role, permission, state-stale, sync-gap, invariant | depth-state-trace |
| precision, rounding, overflow, boundary, zero, first, last, dust | depth-edge-case |
| oracle, external, callback, cpi, periphery, integration | depth-external |
| cast, unsafe, memory, serial, layout, type | depth-lowlevel |
| ordering, compose, resource, account-alias, vm, pda, lifecycle, ttl | depth-runtime |

Findings that match multiple agents are sent to the most-specific one; if truly ambiguous, send to depth-state-trace (it's the generalist).

### Agent prompts

For each agent, use this Task tool invocation template:

```
Task(
  subagent_type="general-purpose",
  model="opus" if MODE in ("core","thorough") else "sonnet",
  prompt="
You are the {AGENT_NAME} depth agent.
Read your agent definition: {{SKILL_ROOT}}/{AGENT_DEF_PATH}

## Your inputs
- Canonical findings to investigate (filter by routing rule):
{FILTERED_FINDINGS_JSON_BLOCK}
- {{SCRATCHPAD}}/attack_surface.md
- {{SCRATCHPAD}}/contract_inventory.md
- Language-specific template: {{SKILL_ROOT}}/prompts/{LANGUAGE}/phase4b-{lowlevel|runtime}-templates.md   # only for depth-lowlevel + depth-runtime
- Source files referenced in your findings (Read on demand)

## Your task
For EACH assigned finding:
1. Read the finding's location.file:location.line_start-line_end in full
2. Apply your agent's depth methodology (see your agent definition for tags + steps)
3. Either CONFIRM the bug with concrete evidence (boundary values, traces, parameter variations), REFUTE it with a proof, or mark it PARTIAL with the missing precondition.

## Output format
Write to {{SCRATCHPAD}}/depth_{AGENT_SHORT}_findings.md using the pipe-delimited FINDING/LEAD format from {{SKILL_ROOT}}/agents/hacking-agents/shared-rules.md, prefixed with the depth-specific Depth Evidence Tags from your agent definition:
- depth-token-flow:    [DTF-1], [DTF-2]...
- depth-state-trace:   [DST-1], [DST-2]...
- depth-edge-case:     [DEC-1], [DEC-2]...
- depth-external:      [DEX-1], [DEX-2]...
- depth-lowlevel:      [DLL-1], [DLL-2]...
- depth-runtime:       [DRT-1], [DRT-2]...

Include schema-aligned fields when known: severity, impact, likelihood, realism_filter, location, evidence (with boundary/variation/trace tags), preconditions, postconditions.

Also include a Chain Summary table at the end of your output:
| Finding ID | Verdict | Postconditions | Missing Preconditions |

Phase 4c will use this to compose chains.

SCOPE: Write ONLY to your assigned output file ({{SCRATCHPAD}}/depth_{AGENT_SHORT}_findings.md). Do NOT read or write other agents' output files. Do NOT proceed to chain analysis, verification, or report. Return your findings and stop.
"
)
```

Substitute per agent:

| AGENT_NAME | AGENT_DEF_PATH | AGENT_SHORT | DEPTH_TAG_PREFIX |
|------------|---------------|-------------|------------------|
| depth-token-flow | agents/depth-token-flow.md *(if missing, use methodology in `references/attack-vectors/`)* | token_flow | DTF |
| depth-state-trace | agents/depth-state-trace.md *(if missing, generalist — use shared-rules.md)* | state_trace | DST |
| depth-edge-case | agents/depth-edge-case.md *(if missing, generalist)* | edge_case | DEC |
| depth-external | agents/depth-external.md *(if missing, generalist)* | external | DEX |
| depth-lowlevel | agents/depth-lowlevel.md | lowlevel | DLL |
| depth-runtime | agents/depth-runtime.md | runtime | DRT |

For the language-specific templates (depth-lowlevel and depth-runtime), use the detected `{LANGUAGE}` from preflight.md to choose the right `prompts/{evm|solana|stellar|aptos|sui|cpp}/phase4b-{lowlevel|runtime}-templates.md`.

### Mode adjustment

- **Light**: spawn only 4 standard agents (token-flow, state-trace, edge-case, external). Skip lowlevel + runtime.
- **Core** / **Thorough**: spawn all 6.

### Inputs filtering (Rule AD-3 from confidence scoring)

Each agent receives at most **5 uncertain findings** in its domain. If more than 5 exist, prioritize by lowest composite confidence first, then by highest severity.

### Iteration 1 only

This phase produces depth iteration 1. Iterations 2-3 (adaptive depth loop per `rules/phase4-confidence-scoring.md`) are NOT in v1.13.1 scope. Confidence scoring + iteration 2+ is v1.13.2+ work. For now, every uncertain finding gets exactly one depth agent pass.

## Required outputs (driver gate checks for these)

- `{{SCRATCHPAD}}/depth_*_findings.md` (glob; ≥ 1 file required)

Each file must contain at least one `FINDING |` or `LEAD |` header plus a Chain Summary table.

## Retry hint (if any)

{{RETRY_HINT}}

When every spawned depth agent has written its output file with the expected content, exit cleanly. Do NOT run chain analysis or verification — the driver invokes Phase 4c separately.
