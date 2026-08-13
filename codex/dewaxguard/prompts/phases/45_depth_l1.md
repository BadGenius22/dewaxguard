# Phase: Depth — L1 Agent Set (Phase 4b, L1 mode only, v1.14+)

> Fresh `codex exec --json` subprocess. No prior context. Treat this prompt as your entire task.
> This is the L1 variant of `45_depth.md`. It REPLACES depth-state-trace + depth-external with the two L1-specific agents: depth-consensus-invariant + depth-network-surface. The other 4 smart-contract depth agents (token-flow, edge-case, lowlevel, runtime) still run when there's smart-contract code in scope (Cosmos SDK with CosmWasm modules, etc.).

## Audit context

- **Audit ID**: `{{AUDIT_ID}}`
- **Mode**: `{{MODE}}` (with `--l1` flag set)
- **Source path**: `{{SRC_PATH}}`
- **Scratchpad**: `{{SCRATCHPAD}}`
- **Skill root**: `{{SKILL_ROOT}}`
- **Phase budget**: `{{TIMEOUT_SECONDS}}` seconds

## Pre-requisites

- `{{SCRATCHPAD}}/findings_routed.json` (from inventory)
- `{{SCRATCHPAD}}/bake/` directory with at least the 8 bake artifacts (from Phase 05 L1 Bake)
- `{{SCRATCHPAD}}/attack_surface.md`, `contract_inventory.md` (from recon)

If `bake/` directory is missing, write `{{SCRATCHPAD}}/depth_failed.md` ("L1 mode requires Phase 05 Bake to have run") and exit.

---

## STEP 1 — Read project state, route findings

Read `findings_routed.json`. For each canonical finding (`canonical_id is null`), decide which L1 depth agent should investigate it.

### L1 routing rule

| bug_class root tokens | L1 depth agent |
|----------------------|---------------|
| consensus, state-machine, slashing, fork-choice, finality, validator-set, ibc, bridge, block-validation, reward, penalty, lifecycle, non-determinism | depth-consensus-invariant |
| p2p, network, gossip, peer, mempool, rpc, sync, transport, dos, eclipse, sybil, rate-limit, auth-bypass-rpc, score | depth-network-surface |
| token, balance, share, donation, fee, accrual, transfer | depth-token-flow (smart-contract; only if CosmWasm/EVM modules in scope) |
| precision, rounding, overflow, boundary, zero, first, last, dust | depth-edge-case (only if SC modules in scope) |
| cast, unsafe, memory, serial, layout, type | depth-lowlevel |
| ordering, compose, resource, account-alias, vm, pda | depth-runtime |

Findings that match multiple agents are sent to the most-specific one. If ambiguous between L1 agents, send to depth-consensus-invariant (it's the generalist for state-machine bugs).

Per-agent input cap is **5 findings** (Rule AD-3 from confidence scoring).

---

## STEP 2 — Spawn agents in parallel

Spawn all required agents in ONE message via Codex subagent delegation. For an L1 audit that's pure consensus client (no SC modules), spawn:

1. depth-consensus-invariant (always)
2. depth-network-surface (always)
3. depth-lowlevel (always — covers Go quirks)
4. depth-runtime (always — covers runtime ordering)

For a chain with smart-contract modules (Cosmos SDK + CosmWasm, Ethereum L2 sequencer):

5. depth-token-flow (if any finding routes here)
6. depth-edge-case (if any finding routes here)

### Agent dispatch template (depth-consensus-invariant)

```
spawn_agent(
  task_name="{TASK_NAME}",
  fork_turns="none",
  reasoning_effort="high" if MODE in ("core","thorough") else "medium",
  message="
You are the depth-consensus-invariant agent (L1 mode).

## Mandatory reading
1. Your agent definition: {{SKILL_ROOT}}/agents/l1/depth-consensus-invariant.md
2. Platform quirks: {{SKILL_ROOT}}/platform-quirks/{LANGUAGE}.md (MANDATORY for Go and C++)
3. L1 severity matrix: {{SKILL_ROOT}}/rules/l1-severity-matrix.md
4. Shared output rules: {{SKILL_ROOT}}/agents/hacking-agents/shared-rules.md
5. Plain-English style: {{SKILL_ROOT}}/rules/plain-english-style.md

## Inputs
- Canonical findings to investigate:
{FILTERED_FINDINGS_JSON_BLOCK}
- {{SCRATCHPAD}}/bake/non_deterministic_calls.md
- {{SCRATCHPAD}}/bake/consensus_state_machine.md
- {{SCRATCHPAD}}/bake/slashing_conditions.md
- {{SCRATCHPAD}}/bake/validator_lifecycle.md
- {{SCRATCHPAD}}/bake/known_issues_index.md (if present)
- {{SCRATCHPAD}}/attack_surface.md
- {{SCRATCHPAD}}/contract_inventory.md
- Source files referenced in findings (Read on demand)

## Method
Apply the 6-step methodology from your agent definition:
1. Cross-validator divergence trace
2. Differential against reference implementation
3. Spec conformance
4. Fuzz exploration
5. Slashing-condition matrix (if applicable)
6. Validator lifecycle race (if applicable)

## L1 evidence tags
Use these in your output's `evidence:` field:
- [DIFF-PASS] — differential against reference implementation found divergence
- [NON-DET-PASS] — same input on two same-version nodes yields different state
- [CONFORMANCE-PASS] — spec invariant violation
- [FUZZ-PASS] — fuzz counterexample
- [CODE-TRACE] — manual trace only

## Output
Write to {{SCRATCHPAD}}/depth_consensus_invariant_findings.md using the pipe-delimited FINDING/LEAD format with IDs [DCI-1], [DCI-2]...
Include schema-aligned fields: severity, impact, likelihood, realism_filter, location, evidence (L1 tags), preconditions, postconditions.
Include the Chain Summary table at the end:
| Finding ID | Verdict | Postconditions | Missing Preconditions |

SCOPE: Write only to {{SCRATCHPAD}}/depth_consensus_invariant_findings.md. Return findings and stop.
"
)
```

### Agent dispatch template (depth-network-surface)

```
spawn_agent(
  task_name="{TASK_NAME}",
  fork_turns="none",
  reasoning_effort="high" if MODE in ("core","thorough") else "medium",
  message="
You are the depth-network-surface agent (L1 mode).

## Mandatory reading
1. Your agent definition: {{SKILL_ROOT}}/agents/l1/depth-network-surface.md
2. Platform quirks: {{SKILL_ROOT}}/platform-quirks/{LANGUAGE}.md (section #11 p2p / Networking Surface for Go)
3. L1 severity matrix: {{SKILL_ROOT}}/rules/l1-severity-matrix.md
4. Shared output rules: {{SKILL_ROOT}}/agents/hacking-agents/shared-rules.md

## Inputs
- Canonical findings: {FILTERED_FINDINGS_JSON_BLOCK}
- {{SCRATCHPAD}}/bake/p2p_message_handlers.md
- {{SCRATCHPAD}}/bake/rpc_methods.md
- {{SCRATCHPAD}}/bake/mempool_admission.md
- {{SCRATCHPAD}}/bake/peer_scoring_rules.md
- {{SCRATCHPAD}}/bake/known_issues_index.md (if present)
- {{SCRATCHPAD}}/attack_surface.md, contract_inventory.md, integration-map.md (if present)
- Source files referenced in findings

## Method
Apply the 6-step methodology from your agent definition:
1. Resource budget audit
2. Per-attack-vector enumeration (eclipse, sybil, mempool DoS, etc.)
3. Peer-scoring symmetry check
4. Authentication ladder
5. Differential against reference implementation
6. Fuzz the wire format

## L1 evidence tags
(same as depth-consensus-invariant)

## Output
Write to {{SCRATCHPAD}}/depth_network_surface_findings.md using FINDING/LEAD format with IDs [DNS-1], [DNS-2]...
Include schema-aligned fields and Chain Summary table.

SCOPE: write only to that file. Return findings and stop.
"
)
```

### Agent dispatch template (depth-lowlevel — Go-aware)

```
spawn_agent(
  task_name="{TASK_NAME}",
  fork_turns="none",
  reasoning_effort="high" if MODE in ("core","thorough") else "medium",
  message="
You are the depth-lowlevel agent (L1 mode, Go-aware).

## Mandatory reading
1. Your agent definition: {{SKILL_ROOT}}/agents/depth-lowlevel.md
2. Platform quirks: {{SKILL_ROOT}}/platform-quirks/{LANGUAGE}.md
   — Pay special attention to: #2 slice aliasing, #5 defer ordering, #6 integer overflow silent, #7 typed nil interface, #8 concurrent map access panic, #9 JSON/RLP/Borsh type confusion.

## Inputs
- Canonical findings: {FILTERED_FINDINGS_JSON_BLOCK}
- {{SCRATCHPAD}}/bake/non_deterministic_calls.md (for the 'go func' goroutine list — leaks live here)
- Source files

## Output
Write to {{SCRATCHPAD}}/depth_lowlevel_findings.md with [DLL-N] IDs and Chain Summary table.
SCOPE: write only to that file.
"
)
```

### Agent dispatch template (depth-runtime)

```
spawn_agent(
  task_name="{TASK_NAME}",
  fork_turns="none",
  reasoning_effort="high" if MODE in ("core","thorough") else "medium",
  message="
You are the depth-runtime agent (L1 mode).

## Mandatory reading
1. Your agent definition: {{SKILL_ROOT}}/agents/depth-runtime.md
2. Platform quirks: {{SKILL_ROOT}}/platform-quirks/{LANGUAGE}.md (section #4 goroutine leaks + scheduling, section #12 consensus determinism)

## Inputs
- Canonical findings: {FILTERED_FINDINGS_JSON_BLOCK}
- {{SCRATCHPAD}}/bake/non_deterministic_calls.md (goroutine spawning)
- {{SCRATCHPAD}}/bake/consensus_state_machine.md (state transition ordering)
- Source files

## Output
Write to {{SCRATCHPAD}}/depth_runtime_findings.md with [DRT-N] IDs and Chain Summary table.
SCOPE: write only to that file.
"
)
```

---

## STEP 3 — Wait, self-check

After all spawned agents return:

1. Verify each output file exists
2. Verify each contains ≥ 1 FINDING/LEAD header
3. Verify each ends with a Chain Summary table

If any agent's output is missing, re-spawn ONCE with a retry hint. The driver content gate will catch persistent failure.

---

## Required outputs (driver gate checks for these)

- `{{SCRATCHPAD}}/depth_*_findings.md` (glob; ≥ 1 file required; should include at least depth_consensus_invariant_findings.md and depth_network_surface_findings.md)

## Retry hint (if any)

{{RETRY_HINT}}

When all spawned agents have written valid output files, exit cleanly. Do not run chain analysis or verification — the driver invokes those separately.
