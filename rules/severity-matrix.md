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
