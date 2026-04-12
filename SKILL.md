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
> **Languages**: Solidity, Rust/Solana, Move/Aptos, Move/Sui
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
Phase 5d:   Bug Validator (platform-specific scoring)
Phase 6:    Report (submission-ready)
```

---

## PHASE 1: RECONNAISSANCE

Detect language automatically:

| Indicator | Language |
|-----------|----------|
| `*.sol` + `foundry.toml` or `hardhat.config.*` | `evm` |
| `*.rs` + `Anchor.toml` or `solana-program` | `solana` |
| `*.move` + `aptos_framework` | `aptos` |
| `*.move` + `sui::object` | `sui` |

Spawn 4 recon agents in parallel:
- **1A (RAG)**: Background, fire-and-forget — vulnerability database queries
- **1B (Docs + External)**: Documentation, fork ancestry, external program verification
- **2 (Build + Static)**: Compile, static analysis, grep vulnerability patterns
- **3 (Patterns + Surface)**: Attack surface mapping, pattern detection, template recommendations

Output: 16+ scratchpad artifacts.

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
2. **Gate 2 — Reachability**: Prove the vulnerable state exists in production
3. **Gate 3 — Trigger**: Prove an unprivileged actor can execute
4. **Gate 4 — Impact**: Prove material harm to identifiable victim

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
│   └── severity-matrix.md
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
