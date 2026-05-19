# Phase: Recon (v1.13.2 driver)

> Fresh `claude -p` subprocess invoked by the dewaxguard v1.13 driver.
> You have no prior conversation context. This prompt is self-contained — do NOT chase cross-references unless the prompt directs you to.
> Every downstream phase (breadth, inventory, depth, chain, verify, validator, report) depends on the artifacts you produce. Treat coverage of the required outputs as the success criterion.

## Audit context

- **Audit ID**: `{{AUDIT_ID}}`
- **Mode**: `{{MODE}}` (light / core / thorough)
- **Source path**: `{{SRC_PATH}}`
- **Project root**: `{{PROJECT_ROOT}}`
- **Scratchpad**: `{{SCRATCHPAD}}`
- **Skill root**: `{{SKILL_ROOT}}`
- **Phase budget**: `{{TIMEOUT_SECONDS}}` seconds

## Pre-requisites

- `{{SCRATCHPAD}}/preflight.md` MUST exist (written by Phase 00). Read its "Language detection" section first — it determines which preprocessors and platform-quirks file to load.
- `{{SRC_PATH}}` must exist and contain source files.

If either is missing, write `{{SCRATCHPAD}}/recon_failed.md` with the diagnostic and exit.

---

## STEP 1 — Language detection (re-verify from preflight)

Re-confirm the language by inspecting `{{SRC_PATH}}` (preflight may be stale if the user re-pointed `--src`):

| Indicator | LANGUAGE value |
|-----------|----------------|
| `*.sol` + `foundry.toml` / `hardhat.config.*` | `evm` |
| `*.rs` + `Anchor.toml` / `solana-program` dep | `solana` |
| `*.rs` + `soroban-sdk` dep (no `solana-program` / `anchor-lang`) | `stellar` |
| `*.move` + `aptos_framework` import | `aptos` |
| `*.move` + `sui::object` import | `sui` |
| `*.cpp` / `*.cc` / `*.hpp` / `*.h` + `CMakeLists.txt` / `conanfile.py` (rippled, Bitcoin Core class) | `cpp` |
| `*.go` + go.mod + consensus/p2p subdirs (v1.14 only) | `go` |

If detection is ambiguous (e.g., both Rust and Move present), default to the language with the most source files in scope. Record the choice and reasoning in the build_status output.

---

## STEP 2 — Load language-specific quirks

For the detected language, the following platform-quirks file is **mandatory reading** before any analysis:

| LANGUAGE | Quirks file |
|----------|-------------|
| `evm` | none required (handled inline by agents) |
| `solana` | `{{SKILL_ROOT}}/platform-quirks/solana.md` (if present) |
| `stellar` | `{{SKILL_ROOT}}/platform-quirks/stellar.md` — **MANDATORY**, archive-restore semantics |
| `aptos` | `{{SKILL_ROOT}}/platform-quirks/aptos.md` (if present) |
| `sui` | `{{SKILL_ROOT}}/platform-quirks/sui.md` (if present) |
| `cpp` | `{{SKILL_ROOT}}/platform-quirks/cpp.md` — **MANDATORY**, 11 rippled-specific behaviors |
| `go` | `{{SKILL_ROOT}}/platform-quirks/go.md` (v1.14+) |

Read the quirks file in full. Record a 1-line summary of each quirk in your build_status output so downstream phases can reference it. The quirks file also contains baseline known-issue lists for deduplication — note these are not internal findings, they are upstream public issues to dedupe against.

---

## STEP 3 — Deterministic preprocessors (Phase 1.0)

Run two deterministic scripts before spawning recon agents. They emit stable greppable artifacts that every downstream agent consumes, lowering token cost and ensuring source-of-truth consistency.

### 3a — Build recon maps

```bash
bash {{SKILL_ROOT}}/scripts/build_recon_maps.sh \
    --lang $LANGUAGE \
    --src  {{SRC_PATH}} \
    --out  {{SCRATCHPAD}} \
    --docs {{PROJECT_ROOT}}
```

If the script exits non-zero, capture stdout+stderr in `{{SCRATCHPAD}}/recon_preprocessor_errors.md` and continue with degraded recon (agents do their own grep). If the script is missing entirely, note "preprocessors unavailable" in build_status and proceed to STEP 4.

Expected artifacts under `{{SCRATCHPAD}}/` (per `{{SKILL_ROOT}}/rules/docs-intent-map.md` + `{{SKILL_ROOT}}/rules/auth-critical-files.md`):

| Artifact | Consumer | Purpose |
|----------|----------|---------|
| `guard-map.md` | breadth (access-control) + depth-state-trace | every modifier/require/auth check site |
| `state-flags.md` | breadth (invariant) + depth-state-trace | every state-modifying assignment |
| `integration-map.md` | breadth (periphery) + depth-external | every external call / CPI / import edge |
| `math-map.md` | breadth (math-precision) + depth-edge-case | every arithmetic op + cast |
| `unsafe-map.md` | breadth (first-principles) + depth-lowlevel | every `unsafe` / `assembly` / raw pointer |
| `logic-anomaly-map.md` | breadth (vector-scan) | classifier output: dead code, TODOs, magic numbers |
| `blackhat-maps.md` | breadth (vector-scan) | known attack pattern matches |
| `divergence-map.md` | breadth (first-principles) | spec-vs-code drift |
| `invariant-extract.md` | breadth (invariant) + chain analysis | declared invariants from docs + comments |
| `docs-intent-map.md` | Phase 5d Gate 1a (HARD) | every doc claim that touches a security primitive |
| `auth-critical-files.txt` | squeezer + every agent claiming missing-auth | file allowlist for full-body reads |

If any artifact is missing after the script runs, note it in build_status — downstream phases can still proceed without missing maps but will be slower/noisier.

### 3b — Source squeezer (Rust only, today)

If `LANGUAGE=solana` or `LANGUAGE=stellar`, run the Rust squeezer to build a body-collapsed source bundle. The squeezer keeps full bodies for auth-critical files (from the allowlist) and collapses bodies for the rest. This dramatically reduces token consumption in breadth agents that need cross-file scope.

```bash
python3 {{SKILL_ROOT}}/scripts/squeezers/squeezer_rust.py \
    --collapse-bodies --numbered \
    --keep-full "$(tr '\n' ',' < {{SCRATCHPAD}}/auth-critical-files.txt)" \
    $(find {{SRC_PATH}} -name '*.rs' -not -path '*/target/*' -not -path '*/tests/*' -not -name '*test*.rs') \
    > {{SCRATCHPAD}}/core-minified.rs
```

Solidity, Move, and C++ squeezers are follow-ons (v1.13.3+). For those languages, agents read full source files directly.

---

## STEP 4 — Recon agents (Phase 1.1, 4 in parallel)

Spawn 4 recon sub-agents via the Task tool. They run in parallel — do NOT chain them sequentially. Each writes its assigned output and stops.

### Agent 1A — RAG probe (fire-and-forget)

```
Task(
  subagent_type="general-purpose",
  model="haiku",
  prompt="
You are Recon Agent 1A: RAG availability probe.
Make ONE call to mcp__unified-vuln-db__validate_hypothesis with a trivial test
hypothesis like 'reentrancy in withdraw'. If the call returns within 10 seconds
with any response, RAG is available. If it times out, errors, or the tool is
not present, RAG is unavailable.

Write the result to {{SCRATCHPAD}}/rag_probe.md:

# RAG Probe
RAG_TOOLS_AVAILABLE: true|false
Reason: <one line>

Do NOT make additional MCP calls. Do NOT analyze any source. Exit cleanly.
SCOPE: write only to {{SCRATCHPAD}}/rag_probe.md.
"
)
```

This agent is fire-and-forget. The driver does not block on it. Phase 4b.5 (RAG Sweep) reads `RAG_TOOLS_AVAILABLE` and falls back to WebSearch if `false`.

### Agent 1B — Docs + External

```
Task(
  subagent_type="general-purpose",
  model="opus" if MODE in ("core","thorough") else "sonnet",
  prompt="
You are Recon Agent 1B: Docs + Fork Ancestry + External Programs.

## Inputs to read
- {{SCRATCHPAD}}/docs-intent-map.md (already emitted by Phase 1.0 preprocessors)
- {{PROJECT_ROOT}}/README.md, {{PROJECT_ROOT}}/docs/**/*.md
- Any whitepaper or design doc cited in CLAUDE.md or CONTEST_FAQ.md
- {{PROJECT_ROOT}}/CLAUDE.md (audit-specific scope, reward pools)
- {{PROJECT_ROOT}}/scratchpad/CONTEST_FAQ.md (if present)

## Method
1. **Design intent**: read every doc. Write a 200-400 word plain-English summary of what the protocol does — primary user flows, value movement, trust assumptions. NO auditor jargon; this is for downstream depth agents.
2. **Fork ancestry**: identify whether this is a fresh codebase or a fork. If forked, name the upstream (Uniswap v3, Compound v2, Aave v3, Solana program library, etc.) and the upstream version. List the diff scope — which functions/files materially changed.
3. **External programs**: enumerate every external program / cross-program-invocation / oracle / bridge / dependency outside the audit scope. For each, record: name, version, called from <files>, called for <purpose>, assumed behavior (the assumption your contract makes — if violated, what breaks).
4. **Augment docs-intent-map**: read the preprocessor's docs-intent-map.md. For each intent claim, mark which are LOAD-BEARING (a violation would be a security finding) vs DECORATIVE (general protocol description). Phase 5d Gate 1a will read this.

## Output
Write to {{SCRATCHPAD}}/design_context.md with sections:
  # Design Context
  ## Plain-English overview
  ## Fork ancestry (Upstream + diff scope + version pinning)
  ## External programs (table: name | version | purpose | assumption)
  ## Load-bearing docs claims (list with file:line for each)
  ## Audit-specific scope (from CLAUDE.md / CONTEST_FAQ.md)

SCOPE: write only to {{SCRATCHPAD}}/design_context.md.
"
)
```

### Agent 2 — Build + Static analysis

```
Task(
  subagent_type="general-purpose",
  model="sonnet",
  prompt="
You are Recon Agent 2: Build + Static Analysis.

## Method
1. **Compile attempt**: try the project's build command. For:
   - EVM Foundry: `forge build`
   - EVM Hardhat: `npx hardhat compile`
   - Solana Anchor: `anchor build` (or `cargo build-sbf`)
   - Solana native: `cargo build-sbf`
   - Stellar: `stellar contract build` or `cargo build --release --target wasm32-unknown-unknown`
   - Aptos: `aptos move compile`
   - Sui: `sui move build`
   - C/C++ rippled: `cmake --build build` (best-effort; full build may not be possible)
   Record: SUCCESS | FAILED | NOT_ATTEMPTED, with stderr summary on failure.

2. **Static analyzer**: if available, run one pass:
   - EVM: slither (if installed)
   - Solana: solana-fender or clippy
   - Aptos/Sui: aptos move prove / sui move build --doc (warning surface)
   - C/C++: cppcheck if installed
   Record findings as raw output; do NOT classify yet (that's breadth's job).

3. **Static greps for known patterns**: cross-reference {{SCRATCHPAD}}/unsafe-map.md (already emitted). Add any pattern matches that the preprocessor missed:
   - EVM: tx.origin, delegatecall, selfdestruct, low-level call without check
   - Solana: skipping is_signer, unchecked AccountInfo
   - Stellar: storage::set without TTL bump, Address::require_auth missing
   - Aptos/Sui: capability transfer in public function
   - C/C++: integer overflow patterns, missing null-check after dynamic cast

4. **Tool probe**: probe MCP tools (slither-analyzer, solana-fender, unified-vuln-db). Mark availability per tool.

## Output
Write to {{SCRATCHPAD}}/build_status.md with sections:
  # Build Status — {{AUDIT_ID}}
  ## Compilation
  Status: SUCCESS|FAILED|NOT_ATTEMPTED
  Errors:
  Warnings:
  ## Static analyzer
  Tool: <name> Version: <ver>
  Findings: N
  ## Pattern matches (augmenting unsafe-map.md)
  ## Tool availability
  RAG_TOOLS_AVAILABLE: true|false   # read from rag_probe.md when written
  SLITHER_AVAILABLE: ...
  SOLANA_FENDER_AVAILABLE: ...
  TRIDENT_AVAILABLE: ...   # Solana only

SCOPE: write only to {{SCRATCHPAD}}/build_status.md.
"
)
```

### Agent 3 — Attack Surface + Template Recommendations

```
Task(
  subagent_type="general-purpose",
  model="opus" if MODE in ("core","thorough") else "sonnet",
  prompt="
You are Recon Agent 3: Attack Surface Mapping + Methodology Template Recommendations.

## Inputs to read
- {{SCRATCHPAD}}/guard-map.md (preprocessor — every auth check site)
- {{SCRATCHPAD}}/state-flags.md (preprocessor — every state-modifying assignment)
- {{SCRATCHPAD}}/integration-map.md (preprocessor — every external call edge)
- {{SCRATCHPAD}}/auth-critical-files.txt (preprocessor — allowlist)
- {{SRC_PATH}}/** (all in-scope source — use Read on individual files as needed)

## Method
1. **Contract/module inventory**: list every contract/module in scope. For each: file path, line count, primary purpose, inheritance / imports / dependencies. Include parent contracts even if out-of-primary-scope when the child overrides their virtual functions (mark `PARENT_CONDITIONAL_OVERRIDE`).

2. **Entry points**: enumerate every externally-callable function. For each: function signature, contract, caller class (anyone / role X / admin / cross-contract only), state read, state written.

3. **Privileged roles**: list every role/capability/auth type. For each: how granted, how revoked, who currently holds (if knowable), what it can do.

4. **Trust boundaries**: identify every boundary where a less-trusted actor invokes a more-trusted contract or vice versa. Examples: user → vault, vault → strategy, governance → timelock, oracle → consumer.

5. **Protocol type classification** (drives injectable skills): is this a vault? DEX? lending? bridge? NFT marketplace? AMM? governance? oracle consumer? account abstraction? Pick all that apply. For each, list the matching injectable skill from `{{SKILL_ROOT}}/methodology/INDEX.md`.

6. **Niche-agent flag detection**: examine code for these triggers and emit flags:
   - `MISSING_EVENT` — if any state-changing function lacks an event emit, flag for EVENT_COMPLETENESS niche
   - `HAS_SIGNATURES` — if ecrecover / ECDSA.recover / EIP712Domain / permit / isValidSignature appear, flag for SIGNATURE_VERIFICATION_AUDIT niche
   - `HAS_DOCS` — if docs-intent-map.md is non-trivial (≥ 5 load-bearing claims), flag for SPEC_COMPLIANCE_AUDIT niche
   - `HAS_MULTI_CONTRACT` — if ≥ 2 contracts share parameters/formulas, flag for SEMANTIC_CONSISTENCY_AUDIT niche
   - `MISSING_INVARIANT_TESTS` — if no invariant/fuzz test file exists for the in-scope contracts
   - `HAS_UPGRADEABLE_PROXY` — if proxy/upgrade pattern detected (EVM) or UpgradeCap (Sui) or version mapping (Solana)

7. **Methodology recommendations**: run the trigger_grep patterns from `{{SKILL_ROOT}}/methodology/INDEX.md` against {{SRC_PATH}}. For each M-NN whose trigger fires, list it.

## Outputs
Write to {{SCRATCHPAD}}/contract_inventory.md (sections: per-contract entries with file/lines/purpose/inheritance + PARENT_CONDITIONAL_OVERRIDE flags).

Write to {{SCRATCHPAD}}/attack_surface.md (sections: entry points, privileged roles, trust boundaries, protocol type, niche flags raised).

Write to {{SCRATCHPAD}}/template_recommendations.md with these sections:
  # Template Recommendations — {{AUDIT_ID}}
  ## Protocol Type
  Detected types: <list>
  ## Injectable Skills (M4-merged into breadth/depth agents)
  - SKILL_NAME — trigger reason — inject into: <agent>
  ## Niche Agents (standalone, flag-triggered, 1 budget slot each)
  - EVENT_COMPLETENESS — trigger: MISSING_EVENT flag
  - SIGNATURE_VERIFICATION_AUDIT — trigger: HAS_SIGNATURES
  - SPEC_COMPLIANCE_AUDIT — trigger: HAS_DOCS
  - SEMANTIC_CONSISTENCY_AUDIT — trigger: HAS_MULTI_CONTRACT
  ## Methodology entries (M-NN) that apply
  - M-08: trigger matched at <file:line>, reason: cheap-plant + admin-op
  - M-XX: ...
  ## State variable index (for chain analysis)
  ## Function list (full signature inventory)

SCOPE: write only to {{SCRATCHPAD}}/contract_inventory.md, {{SCRATCHPAD}}/attack_surface.md, and {{SCRATCHPAD}}/template_recommendations.md.
"
)
```

---

## STEP 5 — Self-checks (orchestrator inline)

After all 4 recon sub-agents return, verify the required artifacts. **Do NOT exit cleanly until all of these are true**:

| Artifact | Existence | Content shape |
|----------|-----------|---------------|
| `{{SCRATCHPAD}}/build_status.md` | exists, > 500 bytes | has `Status:` line + tool availability flags |
| `{{SCRATCHPAD}}/design_context.md` | exists, > 1000 bytes | has "Plain-English overview" section + ≥ 1 external program entry |
| `{{SCRATCHPAD}}/attack_surface.md` | exists, > 1000 bytes | has "Entry points" section + ≥ 1 row |
| `{{SCRATCHPAD}}/contract_inventory.md` | exists, > 500 bytes | has ≥ 1 per-contract entry with file/lines/purpose |
| `{{SCRATCHPAD}}/template_recommendations.md` | exists, > 300 bytes | has "Protocol Type" + "Methodology entries" sections |
| `{{SCRATCHPAD}}/rag_probe.md` | optional | RAG_TOOLS_AVAILABLE flag set |

If any required artifact failed, re-spawn the responsible agent ONCE with a retry hint that names the missing artifact and its content shape requirements. If it fails again, write the partial state to `{{SCRATCHPAD}}/recon_partial.md` describing what's missing and exit — the driver gate will catch it and route to a driver-level retry.

---

## Required outputs (driver gate checks for these)

- `{{SCRATCHPAD}}/build_status.md`
- `{{SCRATCHPAD}}/design_context.md`
- `{{SCRATCHPAD}}/attack_surface.md`
- `{{SCRATCHPAD}}/contract_inventory.md`

Optional (improves downstream phases when present):
- `{{SCRATCHPAD}}/template_recommendations.md`
- `{{SCRATCHPAD}}/rag_probe.md`
- All Phase 1.0 preprocessor maps under `{{SCRATCHPAD}}/`

## Retry hint (if any)

{{RETRY_HINT}}

When all required outputs exist with the content shape above, exit cleanly. Do NOT start breadth analysis — the driver invokes Phase 3 separately.
