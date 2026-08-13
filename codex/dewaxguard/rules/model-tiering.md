# Codex Model Roles

Use semantic roles instead of provider-specific aliases. The deterministic driver uses the user's configured Codex model unless the caller supplies explicit overrides.

## Roles

| Role | Work | Default |
|---|---|---|
| `mechanical` | preflight, indexing, parsing, formatting, deterministic checks | configured Codex model; lower reasoning effort when supported |
| `worker` | phase dispatch, PoC execution, code tracing, report assembly | configured Codex model; medium reasoning effort when supported |
| `finding` | breadth/depth hunting, Nemesis, chain synthesis, high-severity writing | inherit the current frontier model; high reasoning effort |
| `commander` | validation and final accept/reject judgment | configured finding model or current frontier model; high reasoning effort |

Security auditing is recall-sensitive. Do not downgrade finding or commander work merely to reduce cost. If the current session does not expose model/reasoning overrides, inherit its model and preserve the role in the prompt.

## Driver configuration

The driver accepts optional model IDs without assuming which models the user's account exposes:

```bash
python3 scripts/dewaxguard_driver.py \
  --backend codex \
  --mode core \
  --src ./contracts \
  --worker-model <codex-model-id> \
  --finding-model <codex-model-id> \
  --commander-model <codex-model-id>
```

Omit all three options to use the configured Codex default. `mechanical` phases use the worker override. `commander` falls back to the finding override, then worker override, then the configured default.

## Delegation

When Codex subagents are available:

- Label each task with its role and reasoning requirement.
- Prefer inherited models unless the user explicitly requested a model or a valid model override is already known.
- Keep dispatcher prompts bounded; finding agents receive the relevant source scope, quirks, invariants, and evidence format.
- Treat subagent output as unverified claims until load-bearing statements are checked against primary source.

When delegation is unavailable, run the same lanes sequentially and record the loss of independent passes in the negative-space section.

## Prohibitions

- Do not pass Anthropic aliases such as `haiku`, `sonnet`, `opus`, or `fable` to Codex.
- Do not use sandbox-bypass or approval-bypass flags.
- Do not claim that a stronger model converts a quiet pass into evidence of absence.
- Do not assume a child inherits a particular model or reasoning setting; state the role explicitly.
