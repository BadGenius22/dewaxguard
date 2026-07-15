# Phase: Preflight (v1.13.2 driver)

> Fresh `claude -p` subprocess. No prior context. Treat this prompt as your entire task.
> Preflight establishes the audit baseline. Every downstream phase consumes its output to determine language, scope, and known-issue indices.

## Audit context

- **Audit ID**: `{{AUDIT_ID}}`
- **Mode**: `{{MODE}}` (light / core / thorough)
- **Source path**: `{{SRC_PATH}}`
- **Project root**: `{{PROJECT_ROOT}}`
- **Skill root**: `{{SKILL_ROOT}}`
- **Scratchpad**: `{{SCRATCHPAD}}`
- **Phase budget**: `{{TIMEOUT_SECONDS}}` seconds

---

## STEP 1 — Project-local context

For each file below, check existence and record a 1-line summary. Use the Read tool sparingly — preflight should not consume more than ~15 file reads.

### 1a — Audit boundaries + scope

| File | Path | What to extract |
|------|------|-----------------|
| Repo-specific instructions | `{{PROJECT_ROOT}}/CLAUDE.md` | scope boundaries, build commands, "Platform:" line if present, "Realism filter:" overrides |
| Strategic plan | `{{PROJECT_ROOT}}/DEEP_DIVE_PLAN.md` | per-domain hypothesis lists, SCOPE_HINTs for breadth |
| Within-audit knowledge | `{{PROJECT_ROOT}}/scratchpad/learned/00_MANIFEST.md` | F-/R-/D-/T-/L- entries (refuted hypotheses, learned lessons) |
| Contest rules | `{{PROJECT_ROOT}}/scratchpad/CONTEST_FAQ.md` | platform, reward pools, scope clarifications |
| Third-party indices | `{{PROJECT_ROOT}}/context/KNOWN_ISSUES_INDEX_*.md` | upstream issues to dedup against |

For each, record `PRESENT` or `ABSENT`. Do NOT fail preflight if files are absent — only the source path itself is required.

**Provenance & claim-verification (HARD).**
- **Audited code == deployed code.** For a LIVE bounty target, confirm the in-scope source is actually what's deployed before spending depth on it — repo HEAD is a hypothesis, not ground truth. See `rules/fork-poc-execution.md` § "Deployed-code provenance" for the EVM impl-slot → selector-membership procedure and the Solana program-ID / IDL check. A divergence is itself a finding ("audited source differs from deployed").
- **Propagated claims are hypotheses.** Any load-bearing factual claim that reaches a verdict or MEMORY — "target is/isn't live", "asset is in scope", "guard X exists", "already audited" — must be checked against the PRIMARY source (on-chain `eth_getCode`, the program page, the actual code) before it is relayed as fact. A subagent's or recon's assertion is an input to verify, not a conclusion to forward.
- **Bounty scope model (Immunefi / Cantina / C4-BB).** Before spawning agents, extract the program's FULL in-scope asset list and determine its **scope model** — Primacy-of-Impact vs Primacy-of-Rules (see `references/criteria/{platform}.md`). Under Primacy-of-Rules an impact on an unlisted asset is unsubmittable; under Primacy-of-Impact it can still pay. This decides what depth budget is worth spending and what is parked as out-of-scope.

### 1b — V12-style AI-auditor outputs (M-25 trigger)

V12 outputs are structured AI-auditor finding catalogs (Zellic V12, similar). When present, they are usually the contest's official "known issues" index — internal findings that match a V12 entry get duplicated by judges. Critical to dedup against.

```bash
# Probe for V12 outputs
ls {{PROJECT_ROOT}}/*V12*-output.md {{PROJECT_ROOT}}/*zellic*.md 2>/dev/null
```

If matches exist:

```bash
# Count findings per V12 file (per scripts/grep_v12.sh --count)
bash {{SKILL_ROOT}}/scripts/grep_v12.sh --count
```

Record the per-file finding counts. Also run `--invalid-only` to ingest the platform-knowledge corpus:

```bash
bash {{SKILL_ROOT}}/scripts/grep_v12.sh --invalid-only
```

The Invalid-marked entries explain why something LOOKS like a bug but isn't (platform semantics, public-entry-point reachability, archived-but-restored storage, etc.). Read each. These prevent FALSE_POSITIVE findings downstream.

### 1c — Cross-audit context (skill-level, not project-level)

| File | Path | Why it matters |
|------|------|----------------|
| Cross-audit history | `{{SKILL_ROOT}}/LEARNED_INDEX.md` | one-line summary per past audit — recall %, RC distribution, methodology validations |
| Methodology registry | `{{SKILL_ROOT}}/methodology/INDEX.md` | M-NN templates with trigger_grep patterns |
| Refuted classes | `{{SKILL_ROOT}}/refuted/INDEX.md` | cross-audit refuted classes (RF-NN) — a hit kills a hypothesis ONLY if its structural reason also holds in this target |

Read all three. They prime cross-audit pattern recognition and pre-refute dead hypotheses.

---

## STEP 2 — Language detection

Inspect `{{SRC_PATH}}` to determine the language. Use the table below; the FIRST match wins:

| Indicator | LANGUAGE | Confidence |
|-----------|----------|-----------|
| `*.sol` files + `foundry.toml` OR `hardhat.config.*` | `evm` | HIGH |
| `*.sol` files only (no build config) | `evm` | MEDIUM |
| `*.rs` files + `Anchor.toml` OR `solana-program` in `Cargo.toml` | `solana` | HIGH |
| `*.rs` files + `soroban-sdk` in `Cargo.toml` (no `solana-program`/`anchor-lang`) | `stellar` | HIGH |
| `*.rs` files only (no signal) | inspect imports manually | MEDIUM |
| `*.move` files + `aptos_framework` import | `aptos` | HIGH |
| `*.move` files + `sui::object` import | `sui` | HIGH |
| `*.cpp` / `*.cc` / `*.hpp` / `*.h` + `CMakeLists.txt` / `conanfile.py` | `cpp` | HIGH |
| `*.go` files + go.mod + consensus/p2p/mempool subdirs | `go` (v1.14+) | HIGH |

Confidence MEDIUM is acceptable but log the ambiguity in preflight.md so downstream phases know to validate.

### Probe commands

```bash
# Count files per extension to detect dominant language
find {{SRC_PATH}} -name '*.sol' -not -path '*/node_modules/*' | wc -l
find {{SRC_PATH}} -name '*.rs' -not -path '*/target/*' | wc -l
find {{SRC_PATH}} -name '*.move' | wc -l
find {{SRC_PATH}} -name '*.cpp' -o -name '*.cc' -o -name '*.hpp' | wc -l
find {{SRC_PATH}} -name '*.go' -not -path '*/vendor/*' | wc -l

# For Rust, distinguish Solana from Stellar
grep -l 'solana-program\|anchor-lang' {{SRC_PATH}}/../Cargo.toml 2>/dev/null
grep -l 'soroban-sdk' {{SRC_PATH}}/../Cargo.toml 2>/dev/null
```

---

## STEP 3 — Load platform quirks (for the detected language)

| LANGUAGE | Required quirks file |
|----------|----------------------|
| `evm` | (none required — handled inline by agents) |
| `solana` | `{{SKILL_ROOT}}/platform-quirks/solana.md` (if present, MANDATORY) |
| `stellar` | `{{SKILL_ROOT}}/platform-quirks/stellar.md` — **MANDATORY** (archive-restore semantics) |
| `aptos` | `{{SKILL_ROOT}}/platform-quirks/aptos.md` (if present) |
| `sui` | `{{SKILL_ROOT}}/platform-quirks/sui.md` (if present) |
| `cpp` | `{{SKILL_ROOT}}/platform-quirks/cpp.md` — **MANDATORY** (11 rippled-specific behaviors) |
| `go` | `{{SKILL_ROOT}}/platform-quirks/go.md` (v1.14+) |

Read the required file in full. Record presence + a 1-line summary of each quirk in your preflight output. Downstream phases will require the same file; this preflight read lets you verify it exists before downstream agents fail.

---

## STEP 3.5 — Trigger-aware methodology selection (v1.20.0)

Run the methodology matcher with the detected language:

```bash
bash {{SKILL_ROOT}}/scripts/match_methodologies.sh --src {{SRC_PATH}} --root {{PROJECT_ROOT}} --lang <LANGUAGE> --out {{SCRATCHPAD}}
```

Read `{{SCRATCHPAD}}/applicable-methodologies.md`. FIRED templates (code/artifact-triggered) are the methodologies downstream breadth/depth agents must load FIRST; the process-type table is the per-pipeline-stage checklist. Record the FIRED list in preflight.md.

---

## STEP 4 — Output

Write `{{SCRATCHPAD}}/preflight.md`:

```markdown
# Preflight Report — {{AUDIT_ID}}

**Generated**: {{ISO_NOW}}
**Mode**: {{MODE}}
**Source path**: {{SRC_PATH}}
**Project root**: {{PROJECT_ROOT}}

## Project-local context

| File | Path | Status | 1-line summary |
|------|------|--------|----------------|
| CLAUDE.md | {{PROJECT_ROOT}}/CLAUDE.md | PRESENT/ABSENT | ... |
| DEEP_DIVE_PLAN.md | {{PROJECT_ROOT}}/DEEP_DIVE_PLAN.md | ... | ... |
| MANIFEST.md | {{PROJECT_ROOT}}/scratchpad/learned/00_MANIFEST.md | ... | ... |
| CONTEST_FAQ.md | {{PROJECT_ROOT}}/scratchpad/CONTEST_FAQ.md | ... | ... |
| KNOWN_ISSUES_INDEX | {{PROJECT_ROOT}}/context/KNOWN_ISSUES_INDEX_*.md | ... | files found: <list> |

## V12 outputs (M-25 trigger)

- **Files found**: <count + list>
- **Per-file finding counts**: <table>
- **Invalid-only corpus ingested**: ✓ / ✗ (per M-25)
- **Platform-knowledge cards** (Invalid entries, one-line each): <list>

## Cross-audit context

- LEARNED_INDEX.md: PRESENT/ABSENT — N past audits cataloged
- methodology/INDEX.md: PRESENT — <N> M-NN entries registered
- refuted/INDEX.md: PRESENT/ABSENT — <N> RF-NN refuted classes loaded

## Applicable methodologies (trigger-aware, v1.20.0)

- **FIRED (code/artifact)**: <M-XX, M-YY — 1-line match evidence each>
- **Process-type (per-stage checklist)**: see {{SCRATCHPAD}}/applicable-methodologies.md

## Language detection

- **Detected**: <LANGUAGE> (evm / solana / stellar / aptos / sui / cpp / go)
- **Confidence**: HIGH / MEDIUM
- **Reason**: <file-count breakdown + cargo deps signal>
- **Ambiguity notes**: (if MEDIUM, what's ambiguous and how it was resolved)

## Platform quirks

- **Required file**: {{SKILL_ROOT}}/platform-quirks/<lang>.md
- **Status**: PRESENT/ABSENT
- **Quirk count**: <N>
- **One-line summaries**:
  1. <quirk 1>
  2. <quirk 2>
  ...

## Pre-audit assumptions / blockers

(Things downstream phases need to know that aren't captured above. Examples:
- "Build is broken — `forge build` fails with X. Phase 2 should attempt repair before static analysis."
- "Source contains only ABI files; no implementation in scope."
- "DEEP_DIVE_PLAN says reward pool is XYZ — downstream phases should prioritize accordingly."
- "V12 has 30 Invalid entries flagging archive-restore semantics — Stellar Soroban; downstream TTL/expiry hypotheses must check archive behavior first.")

## Self-check

Before exit, verify:
- [ ] Steps 1–3 ran without bailing
- [ ] {{SCRATCHPAD}}/preflight.md is written and ≥ 1500 bytes
- [ ] Language is detected (HIGH or MEDIUM confidence)
- [ ] V12 outputs were checked for (count recorded)
- [ ] match_methodologies.sh ran; FIRED list recorded from applicable-methodologies.md
- [ ] Platform quirks file existence is recorded
- [ ] No preflight step was silently skipped
```

---

## Required outputs (driver gate checks for these)

- `{{SCRATCHPAD}}/preflight.md` — must be ≥ 1500 bytes with all sections above

## Retry hint (if any)

{{RETRY_HINT}}

When the file is written and the self-check passes, your work is done. Do NOT spawn any breadth/depth agents. Do NOT run preprocessors (that's recon's job). Exit cleanly.
