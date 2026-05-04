# Agent Tool-Call Budgets

> **Phase**: 3 (breadth) and 4b (depth) — every agent's prompt embeds a hard cap on Read/Grep calls
> **Purpose**: Prevent runaway agents that spend their entire context on tool-call output, leaving no room to reason. Tool budgets force agents to plan, prioritize, and downgrade rather than thrash.
> **Origin**: Ported from cosminmarian53/skills `soroban-auditor` ("Tool budget: 5 Read/Grep calls").

---

## Why budgets exist

Without a cap:
- Agents Read every file mentioned in the bundle's manifest, then run out of context before they finish reasoning.
- Agents Grep speculatively for every hypothesis they entertain, producing thousand-line search dumps.
- Agents resolve uncertainty by widening the search rather than downgrading the finding to LEAD.

With a cap:
- Agents must rank hypotheses BEFORE searching. Higher-value hypotheses get the budget.
- Unresolvable hypotheses are forced into LEADs (correct outcome — let the validator/depth pass resolve them).
- Tool output stays bounded, so the reasoning portion of the agent's context survives.

---

## Per-agent budgets

| Agent | Read calls | Grep calls | Notes |
|---|---|---|---|
| **Breadth (Phase 3)** | | | |
| vector-scan | 4 | 6 | Pattern matching is grep-heavy by design. |
| math-precision | 6 | 4 | Needs to read math libraries to confirm direction-of-rounding. |
| access-control | 5 | 6 | One Grep against `guard-map.md` is mandatory, not optional. |
| economic-security | 6 | 4 | Token-flow tracing requires reading multiple call sites. |
| execution-trace | 6 | 4 | Reentrancy/CEI tracing needs callee-side reads. |
| invariant | 5 | 5 | Needs to read both halves of paired writes. |
| periphery | 5 | 4 | External-protocol assumption checks. |
| first-principles | 4 | 4 | Lower budget — this agent should question assumptions, not exhaustively trace. |
| **Depth (Phase 4b)** | | | |
| depth-token-flow | 8 | 6 | Multi-step accounting traces need more reads. |
| depth-state-trace | 8 | 6 | Cross-function state mutation tracing. |
| depth-edge-case | 6 | 4 | Boundary substitution requires the boundary, not the whole call graph. |
| depth-external | 6 | 6 | External call surface mapping. |
| depth-lowlevel | 5 | 5 | Type/serialization checks are localized. |
| depth-runtime | 6 | 5 | VM/runtime exploits often span 2-3 files. |
| **Nemesis (Phase 4b.1)** | | | |
| feynman | 6 | 4 | Question-driven, not search-driven. |
| state-inconsistency | 8 | 6 | Coupled-state map needs both writers. |
| **Validator (Phase 5d)** | | | |
| bug-validator | 12 | 8 | Validation is the place to spend budget. |

These are **defaults** — `light` mode halves them; `thorough` mode allows +50% on depth/validator agents.

---

## Mandatory grep targets (count against budget)

Some agents have grep calls that are MANDATORY, not optional. They count against the budget but cannot be skipped:

| Agent | Mandatory greps |
|---|---|
| access-control | 1× grep against `{SCRATCHPAD}/guard-map.md` (when present) for every "missing auth" claim |
| invariant | 1× grep against `{SCRATCHPAD}/state-flags.md` for every state-coupling claim |
| periphery | 1× grep against `{SCRATCHPAD}/integration-map.md` for every cross-contract claim |
| math-precision | 1× grep against `{SCRATCHPAD}/math-map.md` for every rounding-direction claim |
| bug-validator | 1× grep against `{SCRATCHPAD}/docs-intent-map.md` for every PASS finding (per `rules/docs-intent-map.md`) |

Skipping a mandatory grep is a workflow violation. The validator (Phase 5d) auto-fails any finding whose source agent didn't perform its mandatory greps (visible in the agent's tool-call log).

---

## Over-budget protocol

When an agent reaches its budget but has unresolved hypotheses:

1. Do NOT continue tool-calling. The budget is hard.
2. Convert each unresolved hypothesis into a LEAD with `tool_budget_exhausted: true` flag.
3. Emit the LEAD with whatever evidence was gathered. The depth pass (Phase 4b) or the validator (Phase 5d) will resolve them.
4. Do NOT speculate about what the unread code might contain. "I would need to read X to confirm" is acceptable; "X probably contains Y" is not.

LEADs flagged `tool_budget_exhausted: true` are prioritized in the next phase. They get first claim on the deeper agent's budget.

---

## Per-finding `verified:` is exempt

`rules/finding-output-format.md` requires every FINDING to include a `verified:` quote — a paste of the actual line(s) being claimed as buggy. The Reads needed to populate `verified:` count as 1 Read per finding regardless of how many lines are quoted (use `offset` + `limit` to get the right slice in one call).

If an agent cannot fit `verified:` populations within its budget, those findings DOWNGRADE to LEAD by default. A FINDING without `verified:` is auto-rejected.

---

## How agents declare their budget usage

Every agent's output MUST end with a one-line budget receipt:

```
budget: reads=4/5 greps=5/6 — 1 read remaining (deferred to LEAD #2 follow-up)
budget: reads=5/5 greps=4/4 — exhausted; 2 LEADs flagged tool_budget_exhausted
budget: reads=2/5 greps=3/4 — under-spent; no further hypotheses worth investigating
```

The orchestrator uses this receipt to:
- Detect agents that systematically under-spend (suggests the agent is too cautious — adjust prompt).
- Detect agents that systematically exhaust their budget (suggests the budget is too tight — adjust here).
- Prioritize LEAD follow-up in subsequent phases.
