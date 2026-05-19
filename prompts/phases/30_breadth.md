# Phase: Breadth — 8 Hacking Agents (v1.13 driver)

> Fresh `claude -p` subprocess. No prior context. Treat this prompt as your entire task.

## Audit context

- **Audit ID**: `{{AUDIT_ID}}`
- **Mode**: `{{MODE}}`
- **Source path**: `{{SRC_PATH}}`
- **Scratchpad**: `{{SCRATCHPAD}}`
- **Skill root**: `{{SKILL_ROOT}}`

## Pre-requisites

`{{SCRATCHPAD}}` must contain recon outputs: `build_status.md`, `design_context.md`, `attack_surface.md`, `contract_inventory.md`. Confirm with `ls {{SCRATCHPAD}}/` before proceeding.

## Your task

Spawn all 8 hacking agents in parallel via the Task tool. Each reads `{{SRC_PATH}}` plus its agent instructions plus `{{SKILL_ROOT}}/agents/hacking-agents/shared-rules.md`. The agent definitions:

| # | Agent | File | Output |
|---|-------|------|--------|
| 1 | Vector Scan | `{{SKILL_ROOT}}/agents/hacking-agents/vector-scan-agent.md` | `{{SCRATCHPAD}}/analysis_vector_scan.md` |
| 2 | Math Precision | `{{SKILL_ROOT}}/agents/hacking-agents/math-precision-agent.md` | `{{SCRATCHPAD}}/analysis_math_precision.md` |
| 3 | Access Control | `{{SKILL_ROOT}}/agents/hacking-agents/access-control-agent.md` | `{{SCRATCHPAD}}/analysis_access_control.md` |
| 4 | Economic Security | `{{SKILL_ROOT}}/agents/hacking-agents/economic-security-agent.md` | `{{SCRATCHPAD}}/analysis_economic_security.md` |
| 5 | Execution Trace | `{{SKILL_ROOT}}/agents/hacking-agents/execution-trace-agent.md` | `{{SCRATCHPAD}}/analysis_execution_trace.md` |
| 6 | Invariant | `{{SKILL_ROOT}}/agents/hacking-agents/invariant-agent.md` | `{{SCRATCHPAD}}/analysis_invariant.md` |
| 7 | Periphery | `{{SKILL_ROOT}}/agents/hacking-agents/periphery-agent.md` | `{{SCRATCHPAD}}/analysis_periphery.md` |
| 8 | First Principles | `{{SKILL_ROOT}}/agents/hacking-agents/first-principles-agent.md` | `{{SCRATCHPAD}}/analysis_first_principles.md` |

In `light` mode, spawn only agents 1–4. In `core` and `thorough`, spawn all 8.

**Output format**: every agent emits the pipe-delimited `FINDING | contract: ... | function: ... | bug_class: ... | group_key: ... | ...` blocks per `shared-rules.md`. Findings must include `verified:` source quotes; LEADs do not. Optional schema-aligned fields (`severity:`, `impact:`, `likelihood:`, `realism_filter:`, `location:`, `evidence:`) should be emitted when known — they feed the v1.12 mechanical inventory pipeline directly.

**Coverage**: every in-scope source file must be read by at least one agent. The driver coverage gate fails the phase if any file is unread. Use the contract_inventory.md as the ground-truth list.

## Required outputs (driver gate checks for these)

- `{{SCRATCHPAD}}/analysis_*.md` (glob; ≥ 1 file required)

Each file must contain at least one `FINDING |` or `LEAD |` header.

## Retry hint (if any)

{{RETRY_HINT}}

When all agents have written their output files, exit cleanly. Do not run dedup; the driver invokes Phase 4a (inventory) separately.
