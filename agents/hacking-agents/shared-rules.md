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

## Mental tools (senior-auditor mindset)

> Ported light-touch from solidity-auditor v3. Full reference: `references/senior-auditor-sop.md`. These are reasoning aids that raise finding quality — they are NOT enforced by an orchestrator marker grep, so use them because they work, not because they're checked.

Pattern-matching catches obvious bugs; the high-value ones come from HOW you reason. Reach for the right tool the moment its trigger fires:

| Trigger (the condition) | Tool | What you do |
|---|---|---|
| You open a new function/contract/module | **Feynman** (always first) | Explain what it does in plain English, no language jargon. Wherever the explanation gets fuzzy or you reach for a technical term to stay accurate — that spot is where a hidden assumption (and a bug) lives. |
| You stop on a line whose purpose isn't immediately clear | **Socratic** | Ask "why is this here? what does it assume?" Drill past restatements (2-3 "whys") until you reach the implicit belief the code rests on. |
| A path reads clean / a check looks sufficient / a guard looks correct | **Inversion** | Re-read it backward as an attacker: three concrete moves (specific addresses/values/states) that try to defeat it. |
| You reached a "bug" conclusion | Amplify | Chain it, find more victims, lower the precondition cost — do NOT argue yourself out of it. |

You MAY emit inline markers in your **working text** to show the reasoning — `[Feynman: <name>]`, `[Socratic: <file:line> — why?]`, `[Inversion: <function>]`. Keep these markers OUT of the `FINDING |` / `LEAD |` blocks (those are parsed mechanically by `scripts/parse_findings.py`). The markers are for reasoning depth, never for output volume.

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

# Optional schema-aligned fields (parsed by scripts/parse_findings.py into the
# v1.0 findings_table contract; omit when unknown — downstream phases fill in)
severity: Critical|High|Medium|Low|Informational   # only if you can reasonably classify; otherwise leave for inventory
impact: High|Medium|Low|Informational              # axis input for severity matrix
likelihood: High|Medium|Low                        # axis input for severity matrix
realism_filter: permissionless|semi-trusted-role|admin-trust|design-choice|unreachable-precondition
location: <relative/path/File.ext>:L<start>-L<end> # explicit machine-readable location
evidence: [CODE, BOUNDARY, TRACE, POC-PASS, ...]   # comma-separated tag list

LEAD | contract: Name | function: func | bug_class: kebab-tag | group_key: Contract | function | bug-class
code_smells: what you found
description: one sentence explaining trail and what remains unverified
tool_budget_exhausted: true | false   # set true if you ran out of Read/Grep budget

budget: reads=N/MAX greps=N/MAX — <one-sentence note on remaining capacity>
```

The `group_key` enables deduplication: `ContractName | functionName | bug_class`. Agents may add custom fields.

**Mechanical dedup**: `scripts/dedup.py` (v1.12+) parses every `FINDING | ... | group_key: ...` block from agent output into the v1.0 findings_table schema, then merges duplicates via three stages: (A) exact `group_key`, (A2) same `contract`+`function` with bug_class/title overlap, (B) same file + line proximity, (C) cross-file bug_class token overlap. Ambiguous pairs (score 0.70–0.85) are surfaced for LLM tie-break only — most clusters resolve mechanically. Schema-aligned optional fields above improve dedup precision and feed `scripts/severity_router.py` directly.

## Severity self-calibration (set `severity:` HOW, not by reflex)

> **Why this is here**: blind benchmark v1.21.0 showed the breadth layer over-escalates by +1 tier on 4 of 6 findings (reentrancy/unchecked-return/missing-signer each tagged one tier too high). Auto-Critical on any drainable function inflates the whole pipeline's noise floor. You set `severity:` by DERIVING it, not by pattern-matching "fund loss → Critical".

When you write a `severity:` field, derive it in two mechanical steps — do NOT skip to a tier by reflex:

1. **Pick the two axes first** (`impact:` + `likelihood:`), then read the tier off the matrix:

   | | Likelihood: High (no prereq, anyone) | Likelihood: Medium (specific state/role/order) | Likelihood: Low (complex setup) |
   |---|---|---|---|
   | **Impact: High** (direct theft / permanent lock) | Critical | High | Medium |
   | **Impact: Medium** (conditional loss, protocol break) | High | Medium | Medium |
   | **Impact: Low** (broken view, non-fund) | Medium | Low | Low |

   `Critical` requires BOTH High impact AND High likelihood. A drainable function whose trigger needs a specific pre-state, a second actor, a particular ordering, or a non-trivial setup is **High at most**, not Critical — its likelihood is not "anyone, anytime".

2. **Do not pre-apply downgrade modifiers** (trusted-actor −1, view-only cap, on-chain-only −1). Tag the raw axes + `realism_filter:` and let Phase 5d (`rules/severity-decision-tree.md` + `rules/realism-filter.md`) apply them once. Pre-applying them here double-counts.

When unsure between two tiers, **pick the lower one and say so** in the finding (`severity: High  # not Critical: trigger needs first-depositor empty-vault state`). Sandbagging is corrected upward by depth/validator far more cheaply than inflation is corrected downward. A LEAD you under-rate still gets re-scored; a Critical you over-rate burns a verification slot.

## Inconsistency check (MANDATORY for every FINDING)

For each FINDING, grep the full codebase for the CORRECT version of the pattern:
- **EVM**: Missing SafeERC20 → grep for `forceApprove|safeApprove|safeTransfer` in other files; missing access control → grep for the same modifier used on similar functions; missing validation → grep for the same validation in paired/sibling functions
- **C++ ledger (rippled, Bitcoin Core)**: Missing field presence check → grep `isFieldPresent(sfX)` in other transactors handling the same field; missing invariant → grep `MPTInvariant::visit` or similar for what other tx types check; missing amendment gate → grep `rules().enabled(feature)` for the correct guard; missing owner-count adjustment → grep `adjustOwnerCount` in paired create/destroy sites; missing SLE null check → grep `if (!sleX)` in parallel reads
- **Solana/Move**: missing signer check, missing constraint, missing capability pass — grep for the same pattern in sibling instructions

If the correct pattern exists elsewhere, add to proof: `precedent: {File}:{Line} uses {correct pattern}`
This transforms "missing feature" into "inconsistency bug" — much harder to invalidate.
