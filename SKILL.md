---
name: dewaxguard
description: "Multi-language smart contract security auditor with 8 hacking agents, Nemesis cross-feed, mainnet fork PoC verification, and platform-specific bug validation. Supports EVM/Solidity, Solana/Rust, Stellar/Soroban, Aptos/Move, Sui/Move, C/C++. Platforms: Code4rena, Sherlock, Cantina, Immunefi."
user-invocable: true
argument-hint: "[light|core|thorough] [path] [options]"
allowed-tools: Bash(*) Read(*) Write(*) Grep(*) Glob(*) Agent(*)
---

## MANDATORY Session-Start Preflight (NON-SKIPPABLE)

> Before ANY audit work begins (recon, breadth, depth, verification, report), the orchestrator MUST read the following files in order. This is a hard rule — skipping any step is a workflow violation per the post-audit improvement protocol.

### Reading order

**Step 1 — Project-local context** (skip if file does not exist; do NOT create):
1. `{PROJECT_ROOT}/CLAUDE.md` — repo-specific scope rules, build/test commands, audit boundaries
2. `{PROJECT_ROOT}/DEEP_DIVE_PLAN.md` — strategic plan for THIS audit (domain list, hypotheses, files-in-scope per domain, reward-pool framing). If present, this is the AUTHORITATIVE source for SCOPE_HINTs. Any SCOPE_HINT must derive from it (or explicitly note divergence with reasoning).
3. `{PROJECT_ROOT}/scratchpad/learned/00_MANIFEST.md` — cumulative within-audit knowledge (F-/R-/D-/T-/L- entries). Pre-refutes hypotheses, shortcuts analysis. Read EVERY session, not just first.
4. `{PROJECT_ROOT}/scratchpad/CONTEST_FAQ.md` — contest rules, reward pools, scope clarifications
5. `{PROJECT_ROOT}/context/KNOWN_ISSUES_INDEX_*.md` — third-party known-issue indices for dedup

**Step 2 — Cross-audit context** (skip if file does not exist; load from `~/.claude/skills/dewaxguard/` or equivalent):
6. `LEARNED_INDEX.md` — one-line summary per past audit; provides historical recall + RC distribution
7. `methodology/INDEX.md` — registry of M-NN templates with applicability metadata
8. `platform-quirks/{detected_language}.md` — language-specific lessons (cpp, solidity, rust, move, etc.)
9. `refuted/INDEX.md` (when this exists post-Tier-1#3 implementation) — cross-audit refuted vulnerability classes

**Step 3 — Trigger-aware methodology selection** (when Tier 1 #2 ships):
10. For each M-NN with `trigger_grep:` frontmatter, run the grep against the audit codebase. Surface matches as "Applicable methodologies for this audit: M-X, M-Y, M-Z."

### Why this is mandatory

Without these files loaded:
- Hypotheses already refuted in past sessions get re-investigated (waste)
- DEEP_DIVE_PLAN intentions diverge from SCOPE_HINTs (lost coverage)
- Cross-audit M-templates fail to apply when relevant (lost methodology multiplier)
- Past audit failure modes (RC-METHOD/SCOPE) repeat

### Failure mode

If the orchestrator skips this preflight, all subsequent breadth/depth output is suspect. The post-audit Phase A retrospective will detect this as a recall regression vs prior audits. Log "preflight skipped" to MEMORY.md as a workflow violation.

### Self-check before declaring preflight complete

Before proceeding to audit work, verify:
- [ ] DEEP_DIVE_PLAN.md was read (or absence noted)
- [ ] MANIFEST.md was read (or absence noted — first session of new audit)
- [ ] LEARNED_INDEX.md was read (or absence noted)
- [ ] methodology/INDEX.md was read
- [ ] platform-quirks/{language}.md was read for the detected language
- [ ] Any per-domain SCOPE_HINT to be written next will reference DEEP_DIVE_PLAN.md as primary source

If any check fails, RE-READ the missing file. Do not proceed.

---

# DewaxGuard — Ultimate Smart Contract Security Auditor

```
██████╗ ███████╗██╗    ██╗ █████╗ ██╗  ██╗ ██████╗ ██╗   ██╗ █████╗ ██████╗ ██████╗
██╔══██╗██╔════╝██║    ██║██╔══██╗╚██╗██╔╝██╔════╝ ██║   ██║██╔══██╗██╔══██╗██╔══██╗
██║  ██║█████╗  ██║ █╗ ██║███████║ ╚███╔╝ ██║  ███╗██║   ██║███████║██████╔╝██║  ██║
██║  ██║██╔══╝  ██║███╗██║██╔══██║ ██╔██╗ ██║   ██║██║   ██║██╔══██║██╔══██╗██║  ██║
██████╔╝███████╗╚███╔███╔╝██║  ██║██╔╝ ██╗╚██████╔╝╚██████╔╝██║  ██║██║  ██║██████╔╝
╚═════╝ ╚══════╝ ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝
```

**v1.0.0** — Multi-language smart contract security auditor combining three methodologies:
- **8 Specialized Hacking Agents** (breadth coverage)
- **Nemesis Iterative Cross-Feed** (deep business logic + state inconsistency)
- **Language-Specific Low-Level + Runtime Analysis** (what other auditors miss)
- **Mainnet Fork PoC Verification** (mechanical proof on real contracts)
- **Platform-Specific Bug Validation** (pre-submission quality gate)

> **Usage**: `/dewaxguard [light|core|thorough] [path] [options]`
> **Self-Improvement**: `/dewaxguard improve` | `/dewaxguard batch-import` | `/dewaxguard benchmark` | `/dewaxguard consolidate`
> **Languages**: Solidity, Rust/Solana, Rust/Soroban (Stellar), Move/Aptos, Move/Sui, C/C++ (native ledger nodes like rippled, Bitcoin Core)
> **Platforms**: Code4rena, Sherlock, Cantina, Immunefi, HackenProof

---

## Modes

| Mode | Agents | Pipeline |
|------|--------|----------|
| **Light** | ~15 (all Sonnet) | Recon → Breadth(4) → Depth(4) → Chain → Verify → Report |
| **Core** | ~30-40 | Recon → Breadth(8) → Inventory → Depth(6) → Chain → Fork PoC → Validate → Report |
| **Thorough** | ~50-80 | Recon → Breadth(8) → Inventory → Semantic → Depth(6) → Nemesis → Chain → Fork PoC → Validate → Report |

---

## PIPELINE OVERVIEW

```
Phase 1:    Recon (4 agents — build, docs, patterns, surface)
Phase 2:    Instantiation (orchestrator — template binding)
Phase 3:    Breadth (8 specialized hacking agents)
Phase 4a:   Inventory + Dedup
Phase 4a.5: Semantic Invariants (Core/Thorough)
Phase 4b:   Depth (6 agents: token-flow, state-trace, edge-case, external, lowlevel, runtime)
Phase 4b.1: Nemesis Cross-Feed (Thorough only — iterative Feynman + State)
Phase 4c:   Chain Analysis (enabler enumeration + composition)
Phase 5a:   Code Trace (all findings)
Phase 5b:   Unit PoC (model/math tests)
Phase 5c:   Mainnet Fork PoC (Critical/High/Medium)
Phase 4b.5: RAG Validation Sweep (Solodit precedent lookup — see rules/rag-validation-sweep.md)
Phase 5d:   Bug Validator (platform-specific scoring, uses RAG score)
Phase 5d.1: Submission Hardening (fix deductions > 5pts, re-score until >= 85)
Phase 5e:   Self-Calibration (automatic — agent FP rates, confidence accuracy)
Phase 6:    Report (submission-ready)
```

---

## PHASE 1: RECONNAISSANCE

Detect language automatically:

| Indicator | Language |
|-----------|----------|
| `*.sol` + `foundry.toml` or `hardhat.config.*` | `evm` |
| `*.rs` + `Anchor.toml` or `solana-program` | `solana` |
| `*.rs` + `soroban-sdk` in `Cargo.toml` (no `solana-program`/`anchor-lang`) | `stellar` |
| `*.move` + `aptos_framework` | `aptos` |
| `*.move` + `sui::object` | `sui` |
| `*.cpp`/`*.hpp`/`*.h`/`*.c` + `CMakeLists.txt`/`conanfile.py` (native ledger/consensus C++ codebases like rippled, Bitcoin Core) | `cpp` |

> **Stellar note**: When `LANGUAGE=stellar`, the orchestrator MUST pass `~/.claude/skills/dewaxguard/platform-quirks/stellar.md` as context to every spawned agent (recon, breadth, depth, scanners, verifiers). Stellar has critical state archival semantics (persistent/instance storage archives with preserved values on TTL expiry rather than deleting) that have historically produced invalid findings when misunderstood. See `prompts/stellar/phase4b-lowlevel-templates.md` and `prompts/stellar/phase4b-runtime-templates.md` for the depth templates.

> **C/C++ (consensus-node) note**: When `LANGUAGE=cpp`, the orchestrator MUST pass `~/.claude/skills/dewaxguard/platform-quirks/cpp.md` as context to every spawned agent. The quirks file documents 11 critical behaviors specific to XRPL/rippled-style consensus nodes (TER result class semantics, transactor phase ordering, amendment gating, SLE field access, consensus determinism, invariant coverage, Fiat-Shamir context binding, owner count accounting, cross-tx composition, assertions-are-noops, C++ UB traps) plus a baseline known-issue list (XRPL issues #6863, #6867, #6875, #6884, #6894, #6895, #6908) for deduplication. Every finding must be cross-checked against the known-issue list. See `prompts/cpp/phase4b-lowlevel-templates.md` and `prompts/cpp/phase4b-runtime-templates.md` for the depth templates.

Spawn 4 recon agents in parallel:
- **1A (RAG probe)**: Tests `mcp__unified-vuln-db__validate_hypothesis` availability with a trivial call. Sets `RAG_TOOLS_AVAILABLE = true/false` in `build_status.md`. Fire-and-forget — Phase 4b.5 reads the flag.
- **1B (Docs + External)**: Documentation, fork ancestry, external program verification.
  - **MANDATORY emit** (per `rules/docs-intent-map.md`): `{SCRATCHPAD}/docs-intent-map.md` — pre-extracted "by design / intentional / accepted trade-off / out of scope" signals from `docs/**.md`, `README.md`, and root-level `*security*.md`/`*architecture*.md`/`*spec*.md`/`*invariant*.md`/`*design*.md`. Phase 5d Gate 1a hard-fails any finding without `docs_intent_check:` populated.
- **2 (Build + Static)**: Compile, static analysis, grep vulnerability patterns
- **3 (Patterns + Surface)**: Attack surface mapping, pattern detection, template recommendations.
  - **MANDATORY emit** (per `rules/auth-critical-files.md`): `{SCRATCHPAD}/auth-critical-files.txt` — the per-audit list of files matching the auth-critical allowlist. Files on this list keep full bodies in any squeezed/skeleton bundle; files off the list may be body-collapsed for context efficiency.

Output: 16+ scratchpad artifacts (including `docs-intent-map.md`, `auth-critical-files.txt`).

> **Tool-call budgets** (per `rules/agent-tool-budgets.md`): every breadth/depth/Nemesis agent operates under a hard Read/Grep cap. Cap defaults are halved in `light` mode, +50% on depth/validator agents in `thorough` mode. Agents end every output with a `budget:` receipt. Findings without `verified:` quotes downgrade to LEAD by default; see `rules/finding-output-format.md`.

---

## PHASE 3: BREADTH — 8 SPECIALIZED HACKING AGENTS

Spawn ALL 8 in parallel. Each reads the full source + their agent instructions.

| Agent | Focus | File |
|-------|-------|------|
| 1 | Vector Scan — known attack patterns | `agents/hacking-agents/vector-scan-agent.md` |
| 2 | Math Precision — rounding, overflow, precision loss | `agents/hacking-agents/math-precision-agent.md` |
| 3 | Access Control — auth bypass, privilege escalation | `agents/hacking-agents/access-control-agent.md` |
| 4 | Economic Security — token flow, MEV, price manipulation | `agents/hacking-agents/economic-security-agent.md` |
| 5 | Execution Trace — reentrancy, state ordering, callbacks | `agents/hacking-agents/execution-trace-agent.md` |
| 6 | Invariant — state invariants, coupled variable consistency | `agents/hacking-agents/invariant-agent.md` |
| 7 | Periphery — integration bugs, external protocol assumptions | `agents/hacking-agents/periphery-agent.md` |
| 8 | First Principles — question everything, language-level bugs | `agents/hacking-agents/first-principles-agent.md` |

Each agent uses `agents/hacking-agents/shared-rules.md` for output format.

---

## PHASE 4b: DEPTH — 6 AGENTS

Standard 4 (from Plamen methodology):
- **depth-token-flow**: Vault accounting, donation attacks, fee-on-transfer, share inflation
- **depth-state-trace**: Cross-function state mutations, invariant enforcement
- **depth-edge-case**: Zero state, boundary values, overflow, first/last operations
- **depth-external**: CPI/external call side effects, oracle manipulation, callback safety

NEW 2 (language + runtime specific):
- **depth-lowlevel**: Type casts, unsafe code, serialization, memory safety → `prompts/{LANGUAGE}/phase4b-lowlevel-templates.md`
- **depth-runtime**: VM exploits, tx composition, resource exhaustion, account aliasing → `prompts/{LANGUAGE}/phase4b-runtime-templates.md`

---

## PHASE 4b.1: NEMESIS CROSS-FEED (Thorough only)

Iterative back-and-forth between Feynman Auditor and State Inconsistency Auditor:

```
Pass 1 (Feynman): Question every line, ordering, assumption → Suspects
Pass 2 (State):   Map coupled state pairs, find gaps → Gaps
Pass 3 (Feynman): Re-interrogate State's gaps → Root causes
Pass 4 (State):   Expand from Feynman's root causes → New gaps
... continue until convergence (max 6 passes)
```

Scope: Top 5K lines identified by recon (highest-risk functions only).
Input: Enriched by Phase 4b depth findings.
Output: Feeds into Phase 4c chain analysis.

See: `agents/nemesis/feynman.md` and `agents/nemesis/state-inconsistency.md`

---

## PHASE 5c: MAINNET FORK PoC (Critical/High/Medium)

For each finding with severity >= Medium:

### EVM (Foundry):
```bash
forge test --match-test testExploit --fork-url {RPC_URL} -vvv
```
- Use `vm.prank()` for caller impersonation
- Use `vm.store()` for state setup
- Use `vm.warp()` / `vm.roll()` for time/block advancement
- Call REAL deployed contract functions
- Assert exploit outcome

### Solana:
```bash
solana-test-validator --bpf-program {PROGRAM_ID} target/deploy/{PROGRAM}.so --url {RPC}
# OR
cargo test --test fork_poc -- --nocapture
```
- Use anchor test framework with forked validator
- Load real program from mainnet
- Create test accounts with `vm.deal` equivalent

### Move (Aptos/Sui):
- Local simulation with mainnet state snapshot
- Or testnet deployment for full E2E

### Evidence Tags:
| Tag | Weight | Meaning |
|-----|--------|---------|
| `[FORK-PASS]` | Strongest | Exploit confirmed on mainnet fork |
| `[POC-PASS]` | Strong | Unit test passes against model code |
| `[CODE-TRACE]` | Moderate | Manual trace with concrete values |
| `[FORK-FAIL]` | Negative | Fork test failed — likely false positive |

---

## PHASE 5d: BUG VALIDATOR (Pre-Submission Quality Gate)

Before including a finding in the final report, score it against the target platform's judging criteria.

### Supported Platforms:
| Platform | Criteria File |
|----------|---------------|
| Code4rena (Competitive) | `references/criteria/c4-competitive.md` |
| Code4rena (Bug Bounty) | `references/criteria/c4-bounty.md` |
| Sherlock (Competitive) | `references/criteria/sherlock-competitive.md` |
| Sherlock (Bug Bounty) | `references/criteria/sherlock-bounty.md` |
| Cantina | `references/criteria/cantina.md` |
| Immunefi | `references/criteria/immunefi.md` |

### Validation Pipeline (per finding):
1. **Gate 1 — Refutation**: Find the guard that kills the attack
   - **Sub-gate 1a — Docs intent check** (HARD, per `rules/docs-intent-map.md`): grep `{SCRATCHPAD}/docs-intent-map.md` for the function/feature; REJECT if the docs mark the behavior as `by design`/`intentional`/`accepted trade-off`/`out of scope`/`known limitation`. Emit `docs_intent_check:` field.
   - **Sub-gate 1b — Auth check** (when finding alleges missing auth, per `rules/auth-critical-files.md`): confirm whether the source file was emitted `[full-bodies]` or `[collapsed]`; if collapsed, the body must be Read before the finding can stand. Emit `auth_check:` field.
2. **Gate 2 — Reachability**: Prove the vulnerable state exists in production
3. **Gate 3 — Trigger**: Prove an unprivileged actor can execute
4. **Gate 4 — Impact**: Prove material harm to identifiable victim
   - **Sub-gate 4a — Severity decision tree** (HARD, per `rules/severity-decision-tree.md`): apply the a/b/c questions IN ORDER. The first YES determines severity. Emit `severity_check:` field. Findings whose claimed severity exceeds the tree result get a 10-30 point deduction in the validator score.

### Gate 4.5 — Submission-Slot Routing (Code4rena specific):

After Gate 4, BEFORE writing the finding to its severity slot, apply the platform's submission format rules. For Code4rena specifically (per `references/criteria/c4-competitive.md` Submission Format Rules):

- If finding's trigger is privileged-role action AND defense relies on "normal lifecycle" framing → governance/centralization-class → route to **QA-Bundle as L-N entry** (NOT separate Medium file)
- If AI-4 is contested in validation → governance/centralization-class → same routing
- If finding's only victim is a trusted actor (operator/governor self-attack with no permissionless extraction) → QA-Bundle
- All Lows + Informationals → SINGLE consolidated `QA-Bundle.md`
- Only findings with permissionless trigger AND no admin dependency → separate Medium+ file

**Mandatory pre-submission consolidation gate**: enumerate every Medium/Low candidate and apply the routing matrix. Splitting Lows across multiple files violates Code4rena's one-bundle rule and risks losing QA points.

### Scoring:
- Start at 100, deduct for each issue
- **70+**: Include in report as FINDING
- **40-69**: Include as LEAD with improvement suggestions
- **<40**: Exclude (likely rejected)

### Output per finding:
```
Finding X-NN: [Title]
├─ Platform: [C4/Sherlock/etc]
├─ Claimed Severity: [Critical/High/Medium]
├─ Predicted Severity: [same/downgraded]
├─ Score: XX/100
├─ Evidence: [FORK-PASS/POC-PASS/CODE-TRACE]
├─ Verdict: ✅ LIKELY VALID / ⚠️ BORDERLINE / ❌ LIKELY REJECTED
└─ Improvements: [if borderline]
```

---

## PHASE 4b.5: RAG VALIDATION SWEEP (Solodit Database)

After depth loop exits, validate every finding against historical precedent in the Solodit database.

**See full spec**: `rules/rag-validation-sweep.md`

**MCP tools used** (in priority order):
1. `mcp__unified-vuln-db__validate_hypothesis` — primary validation, returns 0-10 confidence score
2. `mcp__unified-vuln-db__search_solodit_live` — live Solodit search, returns historical matches
3. `mcp__unified-vuln-db__get_similar_findings` — fallback if above fail
4. `mcp__unified-vuln-db__get_common_vulnerabilities` — secondary fallback
5. `mcp__unified-vuln-db__analyze_code_pattern` — pattern-based lookup
6. `mcp__unified-vuln-db__get_root_cause_analysis` — root cause taxonomy lookup
7. `mcp__unified-vuln-db__get_attack_vectors` — attack vector enumeration
8. **WebSearch fallback**: `site:solodit.xyz {keywords}` if all MCP tools fail

**Output**: `{SCRATCHPAD}/rag_validation.md` — consumed by Phase 5d (bug validator) and Phase 5d.1 (submission hardening).

---

## PHASE 5d.1: SUBMISSION HARDENING

For each finding scored **< 85** by the bug validator:

1. Read the validator's deduction breakdown
2. For each deduction > 5 points, apply the targeted fix:
   - **"AI-21/weird token risk"** → Run Inconsistency Check: grep codebase for correct pattern used elsewhere. Add `precedent:` evidence.
   - **"Trust debate risk"** → Add Trust Boundary section: role type (admin/infra/user), compromise impact, immune paths.
   - **"Loss not quantified"** → Add Platform Threshold math from `rules/report-template.md` quantification rules.
   - **"Likely dup"** → Ensure finding has differentiating evidence (fork PoC, unique analysis angle, inconsistency proof).
   - **"Missing PoC"** → Escalate to Phase 5c fork PoC queue.
3. Re-score after hardening. If still < 70 → downgrade to LEAD.

---

## PHASE 6: REPORT

Output: `AUDIT_REPORT.md` in project root.

Format: Platform-specific (C4 submission format, Sherlock format, etc.)

For each finding:
- Clean sequential IDs (C-01, H-01, M-01, L-01)
- Full description with code snippets
- PoC (fork test preferred)
- Recommended fix with diff
- Validation score

---

## OPTIONS

| Flag | Effect |
|------|--------|
| `light` | Sonnet-only, no Nemesis, no fork PoC |
| `core` | Opus+Sonnet, fork PoC for Medium+, no Nemesis |
| `thorough` | Full pipeline including Nemesis, fork PoC for all, bug validator |
| `nodocs` | Skip documentation analysis |
| `docs:{url}` | Provide documentation URL |
| `network:{name}` | Set chain for fork testing (ethereum, arbitrum, base, solana, etc.) |
| `platform:{name}` | Set judging platform (c4, sherlock, cantina, immunefi) |
| `scope:{file}` | Limit audit scope |
| `proven-only:true` | Cap unproven findings at Low severity |

---

## FILE STRUCTURE

```
dewaxguard/
├── SKILL.md                          # This file (orchestrator)
├── VERSION                           # Skill version
├── README.md                         # Setup + usage guide
├── MEMORY.md                         # Metrics ledger (one line per audit)
├── CHANGELOG.md                      # Version history
├── improve/
│   ├── IMPROVE.md                    # Post-audit improvement (needs ground truth)
│   ├── SELF-CALIBRATE.md             # Auto-runs after each audit (no ground truth)
│   ├── BATCH-IMPORT.md               # Bulk-process public audit reports
│   ├── BENCHMARK.md                  # Regression testing with known-vulnerable contracts
│   └── CONSOLIDATE.md                # Anti-bloat sweep
├── benchmarks/                       # Known-vulnerable contracts for regression testing
│   ├── manifest.json                 # Registry of all benchmarks
│   ├── evm/                          # EVM benchmarks (reentrancy, share-inflation, etc.)
│   ├── solana/                       # Solana benchmarks (missing-signer, pda-substitution)
│   └── sui/                          # Sui benchmarks (shared-object-race)
├── agents/
│   ├── hacking-agents/               # Phase 3: 8 breadth agents
│   │   ├── vector-scan-agent.md
│   │   ├── math-precision-agent.md
│   │   ├── access-control-agent.md
│   │   ├── economic-security-agent.md
│   │   ├── execution-trace-agent.md
│   │   ├── invariant-agent.md
│   │   ├── periphery-agent.md
│   │   ├── first-principles-agent.md
│   │   └── shared-rules.md
│   ├── nemesis/                      # Phase 4b.1: Nemesis
│   │   ├── feynman.md
│   │   └── state-inconsistency.md
│   ├── depth-token-flow.md           # Phase 4b: Depth agents
│   ├── depth-state-trace.md
│   ├── depth-edge-case.md
│   ├── depth-external.md
│   ├── depth-lowlevel.md             # NEW: Language-specific
│   └── depth-runtime.md              # NEW: Runtime-specific
├── prompts/
│   ├── evm/
│   │   ├── phase1-recon-prompt.md
│   │   ├── phase4b-lowlevel-templates.md
│   │   ├── phase4b-runtime-templates.md
│   │   └── generic-security-rules.md
│   ├── solana/
│   │   ├── phase1-recon-prompt.md
│   │   ├── phase4b-lowlevel-templates.md
│   │   ├── phase4b-runtime-templates.md
│   │   └── generic-security-rules.md
│   ├── aptos/
│   │   ├── phase1-recon-prompt.md
│   │   ├── phase4b-lowlevel-templates.md
│   │   ├── phase4b-runtime-templates.md
│   │   └── generic-security-rules.md
│   └── sui/
│       ├── phase1-recon-prompt.md
│       ├── phase4b-lowlevel-templates.md
│       ├── phase4b-runtime-templates.md
│       └── generic-security-rules.md
├── rules/
│   ├── finding-output-format.md
│   ├── chain-analysis-prompt.md
│   ├── report-template.md
│   ├── fork-poc-execution.md         # NEW: Fork PoC rules
│   ├── severity-matrix.md
│   ├── docs-intent-map.md            # NEW (1.7.0): false-positive killer for documented intent
│   ├── severity-decision-tree.md     # NEW (1.7.0): hard a/b/c severity tree applied at Phase 5d
│   ├── auth-critical-files.md        # NEW (1.7.0): allowlist for files that must keep full bodies
│   └── agent-tool-budgets.md         # NEW (1.7.0): per-agent Read/Grep caps
└── references/
    ├── attack-vectors/
    │   └── attack-vectors.md
    ├── criteria/                      # Bug validator criteria
    │   ├── c4-competitive.md
    │   ├── c4-bounty.md
    │   ├── sherlock-competitive.md
    │   ├── sherlock-bounty.md
    │   ├── cantina.md
    │   └── immunefi.md
    ├── report-formatting.md
    └── judging.md
```
