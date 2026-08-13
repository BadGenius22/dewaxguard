# Phase: Breadth — Hacking Agents (v1.13.2 driver)

> Fresh `codex exec --json` subprocess. No prior context. Treat this prompt as your entire task.
> You are the breadth dispatcher — your job is to spawn N parallel sub-agents and coordinate their outputs. You do NOT analyze source code yourself. You spawn the agents, wait for them, and self-check the outputs.

## Audit context

- **Audit ID**: `{{AUDIT_ID}}`
- **Mode**: `{{MODE}}` (light / core / thorough)
- **Source path**: `{{SRC_PATH}}`
- **Project root**: `{{PROJECT_ROOT}}`
- **Scratchpad**: `{{SCRATCHPAD}}`
- **Skill root**: `{{SKILL_ROOT}}`
- **Phase budget**: `{{TIMEOUT_SECONDS}}` seconds

## Pre-requisites

These must all exist (from prior recon phase):

- `{{SCRATCHPAD}}/build_status.md` — language, tool availability flags
- `{{SCRATCHPAD}}/design_context.md` — protocol overview, fork ancestry, external programs
- `{{SCRATCHPAD}}/attack_surface.md` — entry points, privileged roles, niche flags
- `{{SCRATCHPAD}}/contract_inventory.md` — every in-scope file with line count + purpose
- `{{SCRATCHPAD}}/template_recommendations.md` — injectable skills, niche flags (optional but improves agent prompts)
- Phase 1.0 preprocessor maps (`guard-map.md`, `state-flags.md`, `integration-map.md`, `math-map.md`, `unsafe-map.md`, `logic-anomaly-map.md`, `blackhat-maps.md`, `divergence-map.md`, `invariant-extract.md`, `auth-critical-files.txt`)

If any of the **required** artifacts (first 4) is missing, write `{{SCRATCHPAD}}/breadth_failed.md` with the diagnostic and exit cleanly. The driver content gate will flag this and retry recon.

---

## STEP 1 — Read project state, decide agent set

Read the inputs above (use the Read tool). Specifically extract:

- **LANGUAGE** from `build_status.md` (`evm` / `solana` / `stellar` / `aptos` / `sui` / `cpp` / `go`)
- **In-scope file list** from `contract_inventory.md` — every file you spawn an agent for MUST be covered by at least one agent
- **Niche flags** from `attack_surface.md` (these spawn additional niche agents in Phase 42, NOT here — but breadth agents should be aware)
- **Injectable skills** from `template_recommendations.md` — for each Required injectable, the matching breadth agent gets the skill methodology appended to its prompt

### Agent set per mode

| Mode | Agents spawned | Models |
|------|----------------|--------|
| `light` | 4: vector-scan, math-precision, access-control, economic-security | all `worker` |
| `core` | 8: + execution-trace, invariant, periphery, first-principles | `finding` for math-precision + access-control + invariant; `worker` for the rest |
| `thorough` | 13: core 8 + asymmetry, boundary, flow-gap, numerical-gap, trust-gap (attacker-framing agents #9-13) | all `finding` |

> **Attacker-framing agents (#9-13, thorough only, added v1.19.0 from solidity-auditor v3)**: spawned ONLY in thorough mode. The 5 agents (asymmetry, boundary, flow-gap, numerical-gap, trust-gap) hunt cross-lens "gap" bugs that the single-specialty core 8 miss. In `light`/`core` they are NOT spawned. vector-scan is retained (dewaxguard keeps it; v3 dropped it) — so thorough = 13, not 12.

---

## STEP 2 — Spawn agents in parallel

Spawn ALL agents in ONE message via Codex subagent delegation. Do NOT serialize. Each agent reads its definition file + shared rules + plain-English style and writes to its assigned output path.

### Agent dispatcher template

For each agent N, use this `spawn_agent` invocation. Substitute a unique lowercase `TASK_NAME` and the agent-specific fields from the table below.

```
spawn_agent(
  task_name="{TASK_NAME}",
  fork_turns="none",
  reasoning_effort="{REASONING_EFFORT}",
  message="
You are the {AGENT_NAME} hacking agent.

## Mandatory reading (in order)
1. Your agent definition: {{SKILL_ROOT}}/agents/hacking-agents/{AGENT_FILE}
2. Shared output rules: {{SKILL_ROOT}}/agents/hacking-agents/shared-rules.md
3. Plain-English style: {{SKILL_ROOT}}/rules/plain-english-style.md
4. Finding output format: {{SKILL_ROOT}}/rules/finding-output-format.md
{IF_QUIRKS_FILE_EXISTS}5. Platform quirks: {{SKILL_ROOT}}/platform-quirks/{LANGUAGE}.md (MANDATORY for stellar + cpp)
{IF_INJECTABLE_SKILLS}6. Injectable skill(s) appended below

## Inputs (scratchpad context)
- {{SCRATCHPAD}}/design_context.md (protocol overview)
- {{SCRATCHPAD}}/attack_surface.md (entry points + privileged roles)
- {{SCRATCHPAD}}/contract_inventory.md (in-scope file list)
{IF_PREPROCESSOR_MAP_EXISTS}- {{SCRATCHPAD}}/{MAP}.md (your domain's preprocessor map — start here for hot spots)

## Tool budget
- Reads: {READ_BUDGET}
- Greps: {GREP_BUDGET}
Per {{SKILL_ROOT}}/rules/agent-tool-budgets.md, when the budget exhausts, convert remaining hypotheses to LEADs and end with `budget: reads=N/MAX greps=N/MAX` line.

## Coverage requirement
Every file listed in {{SCRATCHPAD}}/contract_inventory.md whose 'primary purpose' touches your domain MUST be read at least once (use the Read tool, even if briefly). The driver coverage gate verifies this against your transcript.

## Method
Apply the methodology from your agent definition (file in step 1 above) to {{SRC_PATH}}. The definition contains:
- What you ARE looking for (your domain)
- What you are NOT looking for (other agents' domains)
- Attack surfaces specific to {LANGUAGE}
- Output-field requirements

## Injectable skills (when present)
{INJECTED_SKILL_METHODOLOGY}

## Output
Write to {{SCRATCHPAD}}/{OUTPUT_FILE} using the FINDING/LEAD pipe-delimited format from shared-rules.md. Include the optional schema-aligned fields when known: `severity:`, `impact:`, `likelihood:`, `realism_filter:`, `location:`, `evidence:`. These feed the v1.12 mechanical inventory pipeline directly.

End your output with the budget receipt line.

SCOPE: Write ONLY to {{SCRATCHPAD}}/{OUTPUT_FILE}. Do NOT read or write other agents' output files. Do NOT proceed to inventory, depth, chain, verification, or report. Return your findings and stop.
"
)
```

### Agent table

| # | AGENT_NAME | AGENT_FILE | OUTPUT_FILE | Preprocessor MAP | READ_BUDGET | GREP_BUDGET |
|---|------------|-----------|-------------|------------------|-------------|-------------|
| 1 | Vector Scan | vector-scan-agent.md | analysis_vector_scan.md | blackhat-maps + logic-anomaly-map | 30 | 50 |
| 2 | Math Precision | math-precision-agent.md | analysis_math_precision.md | math-map | 40 | 40 |
| 3 | Access Control | access-control-agent.md | analysis_access_control.md | guard-map | 40 | 60 |
| 4 | Economic Security | economic-security-agent.md | analysis_economic_security.md | integration-map | 40 | 50 |
| 5 | Execution Trace | execution-trace-agent.md | analysis_execution_trace.md | state-flags + integration-map | 40 | 40 |
| 6 | Invariant | invariant-agent.md | analysis_invariant.md | state-flags + invariant-extract | 40 | 40 |
| 7 | Periphery | periphery-agent.md | analysis_periphery.md | integration-map | 30 | 40 |
| 8 | First Principles | first-principles-agent.md | analysis_first_principles.md | unsafe-map + divergence-map | 40 | 50 |
| 9 | Asymmetry | asymmetry-agent.md | analysis_asymmetry.md | divergence-map + state-flags | 40 | 50 |
| 10 | Boundary | boundary-agent.md | analysis_boundary.md | integration-map + unsafe-map | 40 | 50 |
| 11 | Flow Gap | flow-gap-agent.md | analysis_flow_gap.md | state-flags + integration-map | 40 | 50 |
| 12 | Numerical Gap | numerical-gap-agent.md | analysis_numerical_gap.md | math-map + invariant-extract | 40 | 40 |
| 13 | Trust Gap | trust-gap-agent.md | analysis_trust_gap.md | guard-map + integration-map | 40 | 50 |

> **Rows 9-13 (asymmetry, boundary, flow-gap, numerical-gap, trust-gap) are thorough-mode ONLY.** Skip them in `light` and `core`. They are attacker-framing cross-lens agents ported from solidity-auditor v3 (dewaxguard v1.19.0). They reuse existing preprocessor maps (no new recon artifacts required).

**Budget tuning per mode**: in `light` mode, halve all budgets. In `thorough` mode, multiply by 1.5. Round to nearest 5.

### Injectable skills (when template_recommendations.md has them)

Read `{{SCRATCHPAD}}/template_recommendations.md` "Injectable Skills" section. For each entry, the methodology file (e.g., `{{SKILL_ROOT}}/methodology/skills/injectable/vault_accounting.md`) is appended to the matching breadth agent's prompt under `## Injectable skills`. The mapping:

| Injectable skill | Inject into |
|-----------------|-------------|
| VAULT_ACCOUNTING | invariant-agent OR economic-security-agent (whichever covers your protocol type) |
| ACCOUNT_ABSTRACTION_SECURITY | access-control-agent + execution-trace-agent |
| NFT_PROTOCOL_SECURITY | economic-security-agent + periphery-agent |
| GOVERNANCE_ATTACK_VECTORS | access-control-agent + invariant-agent |
| OUTCOME_DETERMINISM | first-principles-agent + execution-trace-agent |
| LENDING_PROTOCOL_SECURITY | economic-security-agent + math-precision-agent + invariant-agent |
| DEX_INTEGRATION_SECURITY | periphery-agent + economic-security-agent |

If the methodology file doesn't exist on disk, skip the injection silently (note in your dispatch log).

---

## STEP 3 — Wait for completion, self-check

After all agents return:

1. **File existence**: verify every assigned `analysis_*.md` was written. If any agent's output is missing, the agent failed silently — re-spawn it ONCE with a retry hint.

2. **Content shape**: each file must contain at least one `FINDING |` or `LEAD |` header. A file with only a `budget:` receipt and no findings is a valid output (agent found nothing) — that's fine.

3. **Coverage**: every file listed in `contract_inventory.md` should appear as a `Read` invocation in at least one agent's transcript. The driver coverage gate enforces this — failures generate targeted retry hints with the missed file paths.

4. **Budget receipts**: every output file ends with a `budget:` line. Missing budget receipts are a soft failure — note in your dispatch log but don't retry.

5. **`verified:` quotes on FINDINGs**: per shared-rules.md, every FINDING must include `verified:` with ±2 lines pasted from the source. Findings without `verified:` downgrade to LEAD (the inventory phase will handle this mechanically). Don't fail this here.

---

## STEP 4 — Write dispatch log

Write `{{SCRATCHPAD}}/breadth_dispatch.md` summarizing what was spawned:

```markdown
# Breadth Dispatch Log — {{AUDIT_ID}}

**Generated**: {{ISO_NOW}}
**Mode**: {{MODE}}
**Agents spawned**: <N>
**Injectables applied**: <list with target agent>
**Niche flags raised (for Phase 42 niche)**: <list>

## Per-agent dispatch

| # | Agent | Model | Output | Status | Findings | LEADs |
|---|-------|-------|--------|--------|----------|-------|

## Coverage notes

- Files in inventory: <N>
- Files touched by ≥ 1 agent: <N>
- Files NOT touched (orphaned): <list>

(Files orphaned here will fail the driver coverage gate. If empty, the gate passes.)
```

This dispatch log is informational — the driver does not gate on it but uses it for debugging.

---

## Required outputs (driver gate checks for these)

- `{{SCRATCHPAD}}/analysis_*.md` (glob; ≥ 1 file required)

Each file must contain at least one `FINDING |` or `LEAD |` header per the content gate.

## Coverage gate

The driver coverage gate parses your `codex exec --json` transcript to verify every in-scope file was read by some agent. If gaps are detected, the next retry will inject the specific missed file paths into a `RETRY_HINT` for this phase. Plan agent dispatches so coverage is exhaustive on the first pass.

## Retry hint (if any)

{{RETRY_HINT}}

When all agents have written their output files and your dispatch log is written, exit cleanly. Do not run inventory or depth — the driver invokes Phase 4a separately.
