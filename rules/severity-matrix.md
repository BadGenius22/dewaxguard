# Severity Matrix (Impact x Likelihood)

| | **Likelihood: High** | **Likelihood: Medium** | **Likelihood: Low** |
|---|---|---|---|
| **Impact: High** (direct fund loss/permanent lock) | **Critical** | **High** | **Medium** |
| **Impact: Medium** (conditional fund loss, protocol breakage) | **High** | **Medium** | **Medium** |
| **Impact: Low** (broken views, non-fund impact) | **Medium** | **Low** | **Low** |
| **Impact: Info** (quality, style) | **Informational** | **Informational** | **Informational** |

## Downgrade Modifiers

- Attack requires FULLY_TRUSTED actor to be malicious → -1 tier (floor: Info)
- View-function-only impact → cap at Medium
- On-chain-only exploit (no UI path) → -1 tier (only if impact confined to on-chain)
- Attack requires control of block production on an external chain (Bitcoin mining, ETH proposer slot, Cosmos validator-set position) → **cap at Low for contest mode, cap at Medium for bounty mode**. Applies when the on-chain step is trivial but the precondition is "produce or steer a specific block on another chain whose state this protocol consumes" (SPV light clients, optimistic bridges, ZK bridges with miner-controlled witness). Contest judging treats this prerequisite as Low-likelihood regardless of marginal-cost arguments (e.g. "a top-5 mining pool can craft the block for $0 marginal cost"): the pool of capable entities is small (~10 mining pools, ~rotating beacon committee), the action requires hours-to-days of opportunistic waiting, and reputational/legal exposure deters realistic use. Origin: Atomiq H-01 CVE-2012-2459 audit (2026-05-27); see [[M27-realistic-attacker-severity]] for the sibling capital-dependent attack framework.
