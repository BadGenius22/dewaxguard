# Phase: Preflight (v1.13 driver)

> You are a fresh `claude -p` subprocess invoked by the dewaxguard v1.13 driver.
> You have no prior conversation context. Treat this prompt as your entire task.
> When done, write `{{SCRATCHPAD}}/preflight.md` and exit.

## Audit context

- **Audit ID**: `{{AUDIT_ID}}`
- **Mode**: `{{MODE}}` (light / core / thorough)
- **Source path**: `{{SRC_PATH}}`
- **Project root**: `{{PROJECT_ROOT}}`
- **Skill root**: `{{SKILL_ROOT}}`
- **Scratchpad**: `{{SCRATCHPAD}}`
- **Phase budget**: `{{TIMEOUT_SECONDS}}` seconds

## Your task

Run the **MANDATORY Session-Start Preflight** from `{{SKILL_ROOT}}/SKILL.md` (sections starting at "MANDATORY Session-Start Preflight"). Specifically:

### Step 1 — Project-local context

Check each of these files at `{{PROJECT_ROOT}}` and record presence + a 1-line summary:

1. `CLAUDE.md` — repo-specific scope rules, build/test commands, audit boundaries
2. `DEEP_DIVE_PLAN.md` — strategic plan for this audit
3. `scratchpad/learned/00_MANIFEST.md` — cumulative within-audit knowledge
4. `scratchpad/CONTEST_FAQ.md` — contest rules, reward pools
5. `context/KNOWN_ISSUES_INDEX_*.md` — third-party known-issue indices
6. `*V12*-output.md` / `*zellic*.md` — V12-style AI-auditor outputs (if present, run `{{SKILL_ROOT}}/scripts/grep_v12.sh --count` to confirm)

### Step 2 — Cross-audit context

Check each of these under `{{SKILL_ROOT}}` and record presence:

7. `LEARNED_INDEX.md`
8. `methodology/INDEX.md`
9. `platform-quirks/{language}.md` for the detected language

### Step 3 — Language detection

Inspect `{{SRC_PATH}}` to determine the language:

- `*.sol` → evm/solidity
- `*.rs` + `Anchor.toml` → solana
- `*.rs` + `Cargo.toml` + soroban-sdk dep → stellar
- `*.move` + Aptos artifacts → aptos
- `*.move` + Sui artifacts → sui
- `*.cpp` / `*.cc` / `*.hpp` → cpp
- `*.go` → go (L1 mode, v1.14+)

### Output

Write `{{SCRATCHPAD}}/preflight.md` with:

```markdown
# Preflight Report — {{AUDIT_ID}}

**Generated**: {{ISO_NOW}}
**Mode**: {{MODE}}

## Project-local context

| File | Present | Summary |
|------|---------|---------|
| ... | ✓ / ✗ | one line |

## Cross-audit context

| File | Present | Loaded |
|------|---------|--------|
| ... | ✓ / ✗ | ✓ / ✗ |

## Language detection

- **Detected**: <language>
- **Confidence**: <reason>
- **Required quirks file**: `{{SKILL_ROOT}}/platform-quirks/<lang>.md`
- **Loaded**: ✓ / ✗

## V12 outputs

- **Files found**: <count>
- **Invalid-only corpus ingested**: ✓ / ✗ (per M-25)

## Pre-audit assumptions

(Anything you noticed that downstream phases should know about: build broken,
empty scope, only ABI-level surface, etc.)

## Self-check

- [ ] Steps 1, 2, 3 complete
- [ ] No preflight skipped silently
```

## Retry hint (if any)

{{RETRY_HINT}}

When the file is written, your work is done. Do not spawn any agents. Do not run breadth/depth analysis. Exit cleanly.
