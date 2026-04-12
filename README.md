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
| **Languages** | Single chain | Solidity, Rust/Solana, Move/Aptos, Move/Sui |

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

## Supported Languages

| Language | Low-Level Checks | Runtime Checks |
|----------|-----------------|----------------|
| **Solidity** | Assembly safety, abi.encode collisions, unchecked blocks, delegatecall storage, type truncation | Reentrancy, gas griefing, CREATE2, selfdestruct injection, EIP-712 replay |
| **Rust/Solana** | `as` cast bypass, zero_copy padding, unsafe blocks, borsh serialization | CU exhaustion, account aliasing, PDA collision, instruction composition, CPI trust |
| **Move/Aptos** | Ability constraints, generic type exploits, reference lifecycle, object model | Module upgrades, resource publishing, tx composition, gas metering |
| **Move/Sui** | Object ownership, dynamic fields, witness pattern, coin safety | PTB composition, package upgrades, shared object contention, clock manipulation |

## Methodology Sources

- **Breadth agents**: Adapted from [Pashov's Solidity Auditor](https://github.com/pashov/skills)
- **Nemesis cross-feed**: Feynman technique + State Inconsistency mapping
- **Plamen pipeline**: Full audit orchestration framework
- **Bug Validator**: Platform-specific judging criteria (C4, Sherlock, Cantina, Immunefi)

## Requirements

- Claude Code (claude.ai/code)
- **EVM**: Foundry (forge, anvil)
- **Solana**: solana-cli, anchor-cli
- **Aptos**: aptos-cli
- **Sui**: sui-cli
- Git, Python 3, Node.js (for some tooling)

## License

MIT
