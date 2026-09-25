# 🛡️ DewaxGuard

DewaxGuard is a [Claude Code skill](https://code.claude.com/docs/en/skills) for reviewing smart contracts and blockchain node code for security issues. It checks the code from several angles, tries to confirm possible bugs, and writes a report you can review.

It supports Solidity, Rust, Move, C/C++, and Go projects. The checks vary by language and chain.

## 🚀 Get started

Install the skill with Git:

```bash
mkdir -p "$HOME/.claude/skills"
git clone https://github.com/BadGenius22/dewaxguard.git "$HOME/.claude/skills/dewaxguard"
```

Then open Claude Code in the project you want to audit:

```bash
cd /path/to/your-project
claude
```

At the Claude Code prompt, enter:

```text
/dewaxguard
```

This runs the default **core** audit. DewaxGuard detects the project's language and starts its review.

If you already cloned this repository somewhere else, you can link that checkout instead. Run these commands from the repository's root directory:

```bash
mkdir -p "$HOME/.claude/skills"
ln -s "$PWD" "$HOME/.claude/skills/dewaxguard"
```

Use either the clone or the link. If `~/.claude/skills/dewaxguard` already exists, use that installation. To update a Git checkout installed at that path, run:

```bash
git -C "$HOME/.claude/skills/dewaxguard" pull --ff-only
```

## 🔎 Choose an audit mode

| Mode | When to use it | What it does |
| --- | --- | --- |
| `light` | You want a quicker first pass | Runs a smaller set of checks. |
| `core` | You want the standard audit | Runs the main checks and deeper follow-up analysis. This is the default. |
| `thorough` | You want the most detailed review | Adds more attack angles and repeated checks. It takes longer. |

Enter these commands at the Claude Code prompt:

```text
/dewaxguard light
/dewaxguard core
/dewaxguard thorough
/dewaxguard core platform:sherlock
```

The last example checks findings against Sherlock's judging criteria. You can also pass a project path: `/dewaxguard core /path/to/project`.

### Other options

| Option | Meaning |
| --- | --- |
| `platform:{name}` | Use the rules for `c4`, `sherlock`, `cantina`, or `immunefi`. |
| `network:{name}` | Select a network for fork testing, such as `ethereum`, `arbitrum`, or `base`. |
| `docs:{url}` | Give DewaxGuard a documentation page to use during the review. |
| `nodocs` | Skip documentation analysis. |
| `scope:{file}` | Limit the review to specific files or contracts. |
| `proven-only:true` | Keep findings without proof at Low severity or below. |

## 🧭 What happens during an audit?

1. **Understand the project.** DewaxGuard reads the code, build setup, and available documentation.
2. **Look for issues.** Specialized agents check areas such as permissions, math, state changes, and interactions with other contracts. Deeper modes add more checks.
3. **Check possible findings.** The workflow traces the relevant code and may run a unit test or proof of concept. Where supported, it can test contract calls on a fork of a live chain.
4. **Write the report.** It reviews findings against the selected platform's criteria and records what the audit did not cover.

A finding is a lead to investigate, not a guarantee that an exploit works. Review the evidence and reproduce important findings before relying on the report.

## 🌐 Supported codebases

| Codebase | Examples of issues checked |
| --- | --- |
| Solidity / EVM | Reentrancy, unsafe assembly, storage changes through `delegatecall`, and signature replay. |
| Rust / Solana | Account permissions, PDA handling, unsafe casts, and compute limits. |
| Rust / Soroban (Stellar) | Authorization, storage lifetime, serialization, and cross-contract calls. |
| Move / Aptos | Resource rules, module upgrades, and transaction behavior. |
| Move / Sui | Object ownership, shared objects, and package upgrades. |
| C/C++ node code | Memory safety, serialization, and consensus edge cases. |
| Go node code | Consensus rules, nondeterministic behavior, networking, and mempool handling. |

For native node code, verification may use unit tests because a chain fork is not always available.

## ⚙️ Advanced: run the Python driver

The normal `/dewaxguard` command runs the Claude Code workflow. An optional Python driver runs each audit phase as a separate `claude -p` process, checks the output between phases, and saves progress so you can resume an interrupted run.

Run it from the project you want to audit. Replace `./contracts` with the source directory in that project:

```bash
python3 "$HOME/.claude/skills/dewaxguard/scripts/dewaxguard_driver.py" --mode core --src ./contracts
```

Add `--resume` to continue from saved progress. For a Go or Rust node client, use `--l1`:

```bash
python3 "$HOME/.claude/skills/dewaxguard/scripts/dewaxguard_driver.py" --mode thorough --src ./node --l1
```

The driver can choose different models for different phases. See [model tiering](rules/model-tiering.md) for details.

### Recon tools

The repository also includes scripts that prepare code maps before an audit. Run these from the DewaxGuard checkout, replacing `./contracts` with the path to the code you want to review:

```bash
scripts/build_recon_maps.sh --lang stellar --src ./contracts --out ./scratchpad --docs .
python3 scripts/squeezers/squeezer_rust.py --collapse-bodies --numbered contracts/**/*.rs > ./scratchpad/core-minified.rs
```

The first command maps areas such as authorization, state changes, and integrations. The second makes a shorter copy of Rust source for agent context. See [documentation intent](rules/docs-intent-map.md), [authorization checks](rules/auth-critical-files.md), and [agent tool budgets](rules/agent-tool-budgets.md) for how the workflow uses these files.

## 📦 Requirements

- [Claude Code](https://code.claude.com/)
- Git and Python 3; some tools also use Node.js
- Chain tools for the project you audit: Foundry (`forge`, `anvil`) for EVM, Solana CLI and Anchor for Solana, Aptos CLI for Aptos, or Sui CLI for Sui

## 📚 Methodology and credits

The broad first pass draws on [Pashov's Solidity Auditor](https://github.com/pashov/skills). The deeper workflow combines business-logic review, state-consistency checks, and finding validation. The recon map builder and Rust source shortener adapt work from [cosminmarian53's Soroban auditor](https://github.com/cosminmarian53/skills/tree/main/soroban-auditor) (MIT).

## 📄 License

MIT
