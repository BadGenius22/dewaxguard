# Phase: Recon (v1.13 driver)

> Fresh `claude -p` subprocess. No prior context. Treat this prompt as your entire task.

## Audit context

- **Audit ID**: `{{AUDIT_ID}}`
- **Mode**: `{{MODE}}`
- **Source path**: `{{SRC_PATH}}`
- **Project root**: `{{PROJECT_ROOT}}`
- **Scratchpad**: `{{SCRATCHPAD}}`
- **Skill root**: `{{SKILL_ROOT}}`

## Your task

You are the recon phase. Follow the methodology in `{{SKILL_ROOT}}/SKILL.md`, sections **PHASE 1.0** (Deterministic preprocessors) and **PHASE 1.1** (Recon agents). Specifically:

### Step 1 — Run deterministic preprocessors

```bash
bash {{SKILL_ROOT}}/scripts/build_recon_maps.sh \
    --lang $LANGUAGE \
    --src {{SRC_PATH}} \
    --out {{SCRATCHPAD}} \
    --docs {{PROJECT_ROOT}}
```

(Determine `$LANGUAGE` from preflight output at `{{SCRATCHPAD}}/preflight.md`.)

If the language is Rust, also run the squeezer per SKILL.md Phase 1.0.

### Step 2 — Recon analysis

Working through `{{SRC_PATH}}` files in scope:

1. **Build status** — compile if possible; record errors/warnings in `{{SCRATCHPAD}}/build_status.md`. Set `RAG_TOOLS_AVAILABLE: true|false` flag.
2. **Design context** — what the protocol does, in plain English. Write `{{SCRATCHPAD}}/design_context.md`.
3. **Attack surface** — entry points, externally-callable functions, privileged roles, trust boundaries. Write `{{SCRATCHPAD}}/attack_surface.md`.
4. **Contract inventory** — every contract/module in scope with line count, primary purpose, inheritance/imports. Write `{{SCRATCHPAD}}/contract_inventory.md`.

For Mode `core` or `thorough`, additionally:

5. **Template recommendations** — which methodology entries from `{{SKILL_ROOT}}/methodology/INDEX.md` apply (run `trigger_grep:` patterns). Write `{{SCRATCHPAD}}/template_recommendations.md`.
6. **Niche agents needed** — which niche agents to spawn in Phase 4b (event completeness, signature verification, etc.). Append to `template_recommendations.md`.

## Required outputs (driver gate checks for these)

- `{{SCRATCHPAD}}/build_status.md`
- `{{SCRATCHPAD}}/design_context.md`
- `{{SCRATCHPAD}}/attack_surface.md`
- `{{SCRATCHPAD}}/contract_inventory.md`

## Retry hint (if any)

{{RETRY_HINT}}

When all required outputs exist with real content (not stub placeholders), exit cleanly. Do not start breadth analysis; the driver invokes that separately.
