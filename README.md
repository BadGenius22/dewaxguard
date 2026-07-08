# DewaxGuard — Ultimate Smart Contract Security Auditor

A Claude Code skill that combines three audit methodologies into one unified pipeline for maximum bug coverage.

## What Makes DewaxGuard Different

| Feature | Traditional Audit | DewaxGuard |
|---------|------------------|------------|
| **Breadth** | 2-3 generic agents | 8 specialized hacking agents (vector scan, math, access control, economic, execution trace, invariant, periphery, first principles) |
| **Depth** | Business logic only | 6 agents including **language low-level** (casts, unsafe, serialization) and **runtime-specific** (VM exploits, tx composition) |
| **Cross-feed** | Single pass | Nemesis iterative loop — Feynman ↔ State Inconsistency until convergence |
| **Verification** | Code trace / unit test | **Mainnet fork PoC** — real contract calls on forked chain |
| **Quality** | Submit and hope | **Pre-submission bug validator** — 4-gate scoring against platform criteria |
| **Languages** | Single chain | Solidity, Rust/Solana, Rust/Soroban (Stellar), Move/Aptos, Move/Sui, C/C++ (rippled, Bitcoin Core), Go (L1 node clients) |

## Installation

```bash
# Clone to your Claude commands directory
git clone https://github.com/BadGenius22/Claude-Skills.git
cp -r Claude-Skills/dewaxguard ~/.claude/commands/

# Or symlink
ln -s /path/to/Claude-Skills/dewaxguard ~/.claude/commands/dewaxguard
```

## Usage

```bash
# In Claude Code, navigate to the project directory
cd /path/to/smart-contract-project

# Run audit
/dewaxguard                          # Auto-detect language, Core mode
/dewaxguard thorough                 # Maximum depth (Nemesis + fork PoC)
/dewaxguard core platform:sherlock   # Score findings for Sherlock criteria
/dewaxguard light                    # Quick scan, Sonnet-only
```

## Options

| Flag | Effect |
|------|--------|
| `light` / `core` / `thorough` | Audit depth (default: core) |
| `platform:{name}` | Judging criteria: `c4`, `sherlock`, `cantina`, `immunefi` |
| `network:{name}` | Fork chain: `ethereum`, `arbitrum`, `base`, `solana`, etc. |
| `docs:{url}` | Documentation URL for trust model calibration |
| `nodocs` | Skip documentation analysis |
| `scope:{file}` | Limit to specific files/contracts |
| `proven-only:true` | Cap unproven findings at Low severity |

## Pipeline

```
Phase 1:    Recon (4 agents — build, docs, patterns, attack surface)
Phase 2:    Instantiation (template binding per language)
Phase 3:    Breadth (8 specialized hacking agents in parallel)
Phase 4a:   Inventory + Deduplication
Phase 4a.5: Semantic Invariants (Core/Thorough)
Phase 4b:   Depth (6 agents: standard 4 + lowlevel + runtime)
Phase 4b.1: Nemesis Cross-Feed (Thorough only)
Phase 4c:   Chain Analysis (compound attack paths)
Phase 5a:   Code Trace
Phase 5b:   Unit PoC
Phase 5c:   Mainnet Fork PoC (Critical/High/Medium)
Phase 5d:   Bug Validator (platform scoring)
Phase 6:    Report (submission-ready)
```

## Driver mode (advanced, opt-in)

Instead of the prompt-only LLM orchestrator, a deterministic Python driver can run the pipeline as one `claude -p` subprocess per phase, with content/coverage gates and crash-resumable checkpoints between phases:

```bash
python3 scripts/dewaxguard_driver.py --mode core --src ./contracts [--resume]
python3 scripts/dewaxguard_driver.py --mode thorough --src ./node --l1   # Go/Rust L1 node clients
```

**Model tiering** — each phase's subprocess runs at a tier chosen by role: high-token workers (PoC/trace) and fan-out dispatchers run cheap, the finding sub-agents stay premium, and the bug-validator decision gate runs at the commander tier. Pass `--commander-model fable` to run that gate on Fable 5 (a "premium advisor at decision points" pattern). See [`rules/model-tiering.md`](rules/model-tiering.md).

## Supported Languages

| Language | Low-Level Checks | Runtime Checks |
|----------|-----------------|----------------|
| **Solidity** | Assembly safety, abi.encode collisions, unchecked blocks, delegatecall storage, type truncation | Reentrancy, gas griefing, CREATE2, selfdestruct injection, EIP-712 replay |
| **Rust/Solana** | `as` cast bypass, zero_copy padding, unsafe blocks, borsh serialization | CU exhaustion, account aliasing, PDA collision, instruction composition, CPI trust |
| **Rust/Soroban (Stellar)** | `as` cast bypass, unsafe blocks, serialization | Archive/restore state, `require_auth` gaps, storage TTL, cross-contract trust |
| **Move/Aptos** | Ability constraints, generic type exploits, reference lifecycle, object model | Module upgrades, resource publishing, tx composition, gas metering |
| **Move/Sui** | Object ownership, dynamic fields, witness pattern, coin safety | PTB composition, package upgrades, shared object contention, clock manipulation |
| **C/C++ (native nodes)** | Integer overflow, unsafe casts, memory safety, serialization | rippled / Bitcoin Core tx composition, consensus edge cases (unit-test PoC; fork not feasible) |
| **Go (L1 node clients)** | Unsafe casts, serialization, non-determinism (map iteration, floats, RNG) | Consensus invariants, slashing, fork choice, p2p/RPC surface, mempool admission (via `--l1` mode) |

## Methodology Sources

- **Breadth agents**: Adapted from [Pashov's Solidity Auditor](https://github.com/pashov/skills)
- **Nemesis cross-feed**: Feynman technique + State Inconsistency mapping
- **Plamen pipeline**: Full audit orchestration framework
- **Bug Validator**: Platform-specific judging criteria (C4, Sherlock, Cantina, Immunefi)
- **Recon map builder & Rust squeezer (v1.7.0)**: Ported from [cosminmarian53/skills `soroban-auditor`](https://github.com/cosminmarian53/skills/tree/main/soroban-auditor) (MIT). Generalizes the deterministic preprocessor + body-collapse approach from Soroban-only to multi-language (evm/solana/stellar/aptos/sui/cpp).

## Recon scripts (v1.7.0)

Two deterministic preprocessors that emit greppable artifacts before agents spawn — replaces ad-hoc per-agent grep work, reduces token cost, and produces stable cross-agent context.

```bash
# Build all recon maps (guard, state-flags, integration, math, unsafe,
# logic-anomaly, blackhat, divergence, invariant-extract, docs-intent,
# auth-critical-files allowlist) into $SCRATCHPAD.
scripts/build_recon_maps.sh \
    --lang stellar \
    --src ./contracts \
    --out ./scratchpad \
    --docs .                # default: ./ for docs/, README.md, etc.

# Squeeze Rust sources for context-light agent bundles. Auth-critical
# allowlist files keep full bodies; others collapse fn bodies to `{ ... }`.
python3 scripts/squeezers/squeezer_rust.py \
    --collapse-bodies --numbered \
    --keep-full "admin.rs,access_control,token/src/contract.rs" \
    contracts/**/*.rs > ./scratchpad/core-minified.rs
```

The artifacts are consumed by:
- `rules/docs-intent-map.md` — Phase 5d Gate 1a (validator) hard-fails findings without `docs_intent_check:` populated against the docs-intent map.
- `rules/auth-critical-files.md` — agents must record `auth_check: SAW_FULL_BODY / SAW_GUARD / SKELETON_ONLY` for any missing-auth claim, derived from the squeezer's `[full-bodies]` / `[collapsed]` tag.
- `rules/agent-tool-budgets.md` — mandatory greps against `guard-map.md`, `integration-map.md`, etc. count against per-agent Read/Grep budgets but cannot be skipped.

## Requirements

- Claude Code (claude.ai/code)
- **EVM**: Foundry (forge, anvil)
- **Solana**: solana-cli, anchor-cli
- **Aptos**: aptos-cli
- **Sui**: sui-cli
- Git, Python 3, Node.js (for some tooling)

## License

MIT
