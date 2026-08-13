---
name: dewaxguard
description: Accounting-first, multi-language smart-contract and blockchain security audit workflow with target-specific threat modeling, adversarial breadth/depth passes, deterministic finding deduplication, PoC integrity checks, and platform-aware validation. Use when the user invokes $dewaxguard or asks for a DewaxGuard audit of Solidity/EVM, Solana/Rust, Stellar/Soroban, Aptos/Move, Sui/Move, C/C++, or Go/L1 code. Supports light, core, and thorough modes and Code4rena, Sherlock, Cantina, Immunefi, and HackenProof outputs.
---

# DewaxGuard for Codex

Run an authorized, evidence-first security audit. Preserve the upstream money-model-first methodology while using Codex-native paths, tools, agents, models, and subprocesses.

## Invocation

Interpret prompts such as:

- `$dewaxguard light .`
- `$dewaxguard core contracts platform:sherlock`
- `$dewaxguard thorough . network:ethereum`
- `$dewaxguard core . --driver`
- `$dewaxguard improve`

Default to `core` and the current repository when mode or path is omitted. Resolve this file's directory as `SKILL_ROOT`; never hard-code a Claude directory.

## Non-negotiable audit rules

1. Audit only the repository, deployment, accounts, networks, and evidence the user placed in scope.
2. Read applicable `AGENTS.md` files before audit work. Also read `CLAUDE.md` when present because it may contain legacy target instructions; `AGENTS.md` wins on conflict.
3. At the start of every audit or threat model, read `~/.codex/audit-references/threat-model-references.md` when available. Treat its links as methodology and examples, revalidate moving claims, and derive the actual threat model from the target.
4. Record scope, exclusions, assumptions, assets, actors, trust boundaries, invariants, entry points, value flows, attack surfaces, threats, validation status, deployment provenance, and code references.
5. A quiet pass is not coverage. Reserve “coverage” for mechanically enumerated surfaces and publish negative space.
6. Any load-bearing mechanism claim crossing an agent or phase boundary needs a `file:line` citation. Treat uncited claims as hypotheses.
7. A PoC is evidence only after mutation check, positive control, real-path audit, and attacker-benefit assertion. Otherwise cap it at `[CODE-TRACE]`.
8. Preserve user changes and isolate concurrent PoC writers with worktrees or unique directories.
9. Verify time-sensitive platform rules, deployed configuration, source provenance, known issues, and external integrations with current primary evidence.

Read `references/full-pipeline.md` when running a complete audit, and use the resource routing below rather than loading every file indiscriminately.

## Parse inputs

Support:

| Input | Meaning |
|---|---|
| `light` | Quick pass; 4 breadth lenses, reduced depth, no fork-PoC requirement |
| `core` | Default; 8 breadth lenses, blind reruns, 6 depth lanes, validation |
| `thorough` | 13 breadth lenses, blind reruns, Nemesis cross-feed, full validation |
| `platform:<name>` | `c4`, `sherlock`, `cantina`, `immunefi`, or `hackenproof` |
| `network:<name>` | Fork/deployment network |
| `scope:<file>` | Explicit scope file |
| `docs:<url>` | Target documentation |
| `nodocs` | Skip optional docs review, not target-owned specs already in the repository |
| `proven-only:true` | Cap findings lacking proof at Low |
| `--driver` | Use the deterministic Codex subprocess driver |
| `--l1` | Use Go/Rust node-client lanes and L1 severity rules |

Do not silently infer a contest platform when severity or submission routing depends on it. If local files do not resolve the platform, continue with neutral severity and state the assumption.

## Mandatory preflight

Before recon, read or explicitly record absence of:

1. Applicable `AGENTS.md`, then target `CLAUDE.md` if present.
2. `DEEP_DIVE_PLAN.md`.
3. `scratchpad/learned/00_MANIFEST.md`.
4. `scratchpad/CONTEST_FAQ.md`.
5. `context/KNOWN_ISSUES_INDEX_*.md` and V12/Zellic-style outputs.
6. `~/.codex/audit-references/threat-model-references.md`.
7. `SKILL_ROOT/LEARNED_INDEX.md`.
8. `SKILL_ROOT/methodology/INDEX.md`.
9. `SKILL_ROOT/refuted/INDEX.md`.
10. `SKILL_ROOT/failure-modes/INDEX.md`.

Then:

1. Run `scripts/detect_language.sh --src <scope>` and use its `LANGUAGE`, `QUIRKS`, and `L1_CANDIDATE` outputs.
2. Read the detected platform-quirks file in full.
3. Run `scripts/match_methodologies.sh --src <scope> --lang <language> --out <scratchpad>` and read `applicable-methodologies.md`.
4. If at least three artifact/code methodologies fire, use `agents/methodology-adversary.md` to KEEP, DEMOTE, or KILL each before breadth.
5. Write `scratchpad/preflight.md` with scope, provenance, assumptions, blockers, current evidence, and the self-check.

## Build the money and threat model first

Before vulnerability hunting, create:

- asset and custody ledger;
- actor and privilege matrix;
- trust-boundary and integration map;
- state-transition map;
- value-inflow, internal-accounting, and outflow map;
- invariants with enforcing `file:line` or `NOT ENFORCED IN CODE`;
- attacker goals and realistic capabilities;
- deployment/source/configuration differences;
- explicit negative-space ledger.

Write the findings-blind model to `scratchpad/protocol-model.md`. Do not seed that pass with existing findings, known issues, or refuted hypotheses.

## Run the audit pipeline

1. **Recon and preprocess**: build deterministic recon maps with `scripts/build_recon_maps.sh`; review docs, build status, source provenance, tests, privileged paths, external calls, and language-specific runtime semantics.
2. **Test-gap map**: classify each in-scope entry point and invariant as `UNTESTED`, `HAPPY-ONLY`, `ADVERSARIAL`, or `FUZZED`; record what fuzz properties actually assert.
3. **Breadth**: run the mode-selected lenses from `agents/hacking-agents/`. Give each a bounded scope, read/grep budget, required evidence quotes, quirks file, and unique output under `scratchpad/analysis_*.md`.
4. **Blind rerun** (`core`/`thorough`): rerun invariant, economic-security, and first-principles lenses without pass-one findings or exclusion lists. Measure stability and ingest unique results.
5. **Inventory**: run `parse_findings.py`, `dedup.py`, and `severity_router.py`. Use an agent only for pairs left ambiguous by the deterministic pipeline.
6. **Depth**: run token-flow, state-trace, edge-case, external, low-level, and runtime lanes. Prioritize `UNTESTED` and `HAPPY-ONLY` surfaces alongside finding-derived targets.
7. **Nemesis** (`thorough`): alternate Feynman and state-inconsistency passes on the highest-risk code until the configured stopping heuristic or pass limit. Never describe convergence as proof of absence.
8. **Chain analysis**: enumerate enabling conditions and compose findings across calls, contracts/programs, roles, time, and external systems.
9. **Verify**: trace every candidate, build proportionate tests, perform fork checks where authorized and feasible, and attach evidence tags. Follow `rules/fork-poc-execution.md` and `rules/plain-english-style.md`.
10. **RAG/precedent sweep**: use the current tools and fallback chain in `rules/rag-validation-sweep.md`; verify precedent against primary code and current platform rules.
11. **Validate**: apply target-platform gates, severity decision tree, realistic-attacker filter, known-issue dedup, claim ledger, and submission routing.
12. **Report**: write `AUDIT_REPORT.md` with reproducible evidence, fixes, validation scores, and the mandatory “What this audit did not cover” section.

## Agent coordination

Use Codex subagents when available and allowed by the current session. The skill explicitly calls for bounded delegation in breadth, depth, Nemesis, chain, verification, and report lanes.

- Keep scopes independent and outputs uniquely named.
- Inherit the current model by default; use role-based reasoning effort from `rules/model-tiering.md` when supported.
- Do not use Anthropic aliases (`haiku`, `sonnet`, `opus`, `fable`) as Codex model names.
- Treat agent conclusions as claims and verify load-bearing evidence locally before reporting.
- When subagents are unavailable, execute the same lanes sequentially and record reduced independence in negative space.

## Deterministic driver

Prefer prompt-native execution for interactive audits. Use driver mode when the user requests it, when crash-resume matters, or when phase gates materially improve reliability:

```bash
python3 "$SKILL_ROOT/scripts/dewaxguard_driver.py" \
  --backend codex \
  --mode core \
  --src ./contracts \
  --project-root . \
  --resume
```

Before a real driver run, execute `--dry-run` and inspect the selected phases, paths, prompts, and write targets. The driver uses `codex exec --json` and stores JSONL transcripts under `scratchpad/driver/`. Never use sandbox-bypass flags. Obtain approvals through normal Codex permissions.

## Resource routing

| Need | Read/use |
|---|---|
| Complete phase detail | `references/full-pipeline.md` |
| Threat-model examples | `~/.codex/audit-references/threat-model-references.md` |
| Finding schema and evidence | `agents/hacking-agents/shared-rules.md`, `rules/finding-output-format.md` |
| Language semantics | `platform-quirks/<language>.md`, `prompts/<language>/` |
| Triggered audit methods | `methodology/INDEX.md`, then only fired M-files |
| Known false-positive shapes | `refuted/INDEX.md`, `failure-modes/INDEX.md` |
| Severity and realism | `rules/severity-decision-tree.md`, `rules/realism-filter.md`, platform criteria |
| PoC validation | `rules/fork-poc-execution.md` |
| Report structure | `rules/report-template.md`, `references/report-formatting.md` |
| Driver recovery | `rules/agent-failure-recovery.md`, `scripts/dewaxguard_driver.py` |

## Completion gates

Before declaring the audit complete, verify:

- the report maps each surviving claim to code or current external evidence;
- deterministic parsers and gates pass;
- proof receipts are present or evidence is downgraded;
- platform routing and severity are explicit;
- unresolved assumptions and negative space are published;
- the original Claude skill was not modified;
- no “clean” or “full coverage” claim exceeds the evidence.

For post-result calibration, read only the relevant file under `improve/` and update the Codex copy's learning ledgers after ground truth is available.
