# Shared Scan Rules

## Reading

Your bundle has two sections:

1. **Core source** (inline) — read in parallel chunks (offset + limit), compute offsets from the line count in your prompt.
2. **Peripheral file manifest** — file paths under `# Peripheral Files (read on demand)`. Read only those relevant to your specialty.

When matching function names, check language-specific naming conventions:
- **Solidity**: `functionName` and `_functionName` (underscore prefix = internal)
- **Rust**: `fn function_name` (snake_case) and `pub fn`
- **Move**: `public fun function_name` / `fun function_name` (native module functions)
- **C++**: `ClassName::method` and free `functionName`; virtual/override methods; template instantiations; `namespace::function`. For rippled-pattern: `Transactor::preflight`, `Transactor::preclaim`, `Transactor::doApply` are the entry points for tx logic.

## Cross-contract patterns

When you find a bug in one contract, **weaponize that pattern across every other contract in the bundle.** Search by function name AND by code pattern. Finding native/ERC20 confusion in `ContractA.onRevert` means you check every other contract's `onRevert` — missing a repeat instance is an audit failure.

After scanning: escalate every finding to its worst exploitable variant (DoS may hide fund theft). Then revisit every function where you found something and attack the other branches.

## Do not report

Admin-only functions doing admin things. Standard DeFi tradeoffs (MEV, rounding dust, first-depositor with MINIMUM_LIQUIDITY). Self-harm-only bugs. "Admin can rug" without a concrete mechanism.

## Output

Return structured blocks only — no preamble, no narration. Exception: vector scan agent outputs its classification block first.

FINDINGs have concrete, unguarded, exploitable attack paths. LEADs have real code smells with partial paths — default to LEAD over dropping.

**Every FINDING must have a `proof:` field** — concrete values, traces, or state sequences from the actual code. No proof = LEAD, no exceptions.

**Every FINDING must have a `verified:` field** — paste the actual ±2 lines from the source around the cited line. No paste = LEAD, no exceptions. See `rules/finding-output-format.md`.

**Tool-call budget**: every agent operates under a hard Read/Grep cap defined in `rules/agent-tool-budgets.md`. When the budget exhausts, convert remaining hypotheses to LEADs flagged `tool_budget_exhausted: true`. Do NOT continue calling tools past the cap. End every output with a one-line `budget:` receipt.

**Auth-critical files**: when a finding alleges missing auth / access-control / role check, follow the rules in `rules/auth-critical-files.md`. Do NOT claim a missing-auth bug from a `[collapsed]` skeleton view alone — Read the body first, or DOWNGRADE to LEAD.

**One vulnerability per item.** Same root cause = one item. Different fixes needed = separate items.

```
FINDING | contract: Name | function: func | bug_class: kebab-tag | group_key: Contract | function | bug-class
path: caller → function → state change → impact
proof: concrete values/trace demonstrating the bug
verified: |
  Lxx:   <line of source code>
  Lyy:   <±2 lines around the cited bug location>
description: one sentence
fix: one-sentence suggestion

LEAD | contract: Name | function: func | bug_class: kebab-tag | group_key: Contract | function | bug-class
code_smells: what you found
description: one sentence explaining trail and what remains unverified
tool_budget_exhausted: true | false   # set true if you ran out of Read/Grep budget

budget: reads=N/MAX greps=N/MAX — <one-sentence note on remaining capacity>
```

The `group_key` enables deduplication: `ContractName | functionName | bug_class`. Agents may add custom fields.

## Inconsistency check (MANDATORY for every FINDING)

For each FINDING, grep the full codebase for the CORRECT version of the pattern:
- **EVM**: Missing SafeERC20 → grep for `forceApprove|safeApprove|safeTransfer` in other files; missing access control → grep for the same modifier used on similar functions; missing validation → grep for the same validation in paired/sibling functions
- **C++ ledger (rippled, Bitcoin Core)**: Missing field presence check → grep `isFieldPresent(sfX)` in other transactors handling the same field; missing invariant → grep `MPTInvariant::visit` or similar for what other tx types check; missing amendment gate → grep `rules().enabled(feature)` for the correct guard; missing owner-count adjustment → grep `adjustOwnerCount` in paired create/destroy sites; missing SLE null check → grep `if (!sleX)` in parallel reads
- **Solana/Move**: missing signer check, missing constraint, missing capability pass — grep for the same pattern in sibling instructions

If the correct pattern exists elsewhere, add to proof: `precedent: {File}:{Line} uses {correct pattern}`
This transforms "missing feature" into "inconsistency bug" — much harder to invalidate.
