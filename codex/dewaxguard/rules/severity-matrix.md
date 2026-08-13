# Severity Matrix (Impact x Likelihood)

| | **Likelihood: High** | **Likelihood: Medium** | **Likelihood: Low** |
|---|---|---|---|
| **Impact: High** (direct fund loss/permanent lock) | **Critical** | **High** | **Medium** |
| **Impact: Medium** (conditional fund loss, protocol breakage) | **High** | **Medium** | **Medium** |
| **Impact: Low** (broken views, non-fund impact) | **Medium** | **Low** | **Low** |
| **Impact: Info** (quality, style) | **Informational** | **Informational** | **Informational** |

## Grief economics (MANDATORY for every DoS / griefing finding)

> **Origin**: DRE Sherlock audit (2026-07). A **real** defect — a wrong-list compliance check (dreUSD freeze list checked, USDC blacklist paid) with no `try/catch`, permanently bricking the keeper queue — shipped as Medium with a passing end-to-end fork PoC and was rejected. Judge: *"attacker will lose way more than the party being affected... I don't see how this should be Medium/High at all."* The attacker's dust was unrecoverable; the victims only suffered delay the TREASURY could clear manually.
>
> dewaxguard already had this dimension in three places and had **never generalized it to the smart-contract path**: `rules/l1-severity-matrix.md` ("Single-node DoS with high attacker cost → Low"), `references/criteria/immunefi.md` ("Medium 'Griefing' requires DEMONSTRATED damage"), and `M16` ("unless easy-to-trigger with zero attacker cost"). These gates close that gap for every language and platform.

A DoS / griefing finding may exceed **Low** only if it clears all three gates. Each is mechanical — implemented in `scripts/severity_router.py::apply_grief_economics` and applied at Phase 5d.

| Gate | Question | Fails → |
|---|---|---|
| **G1 — Economic rationality** | Is the attacker's **unrecoverable** cost less than the quantified victim harm? | tag `uneconomic-grief` → **cap Low** |
| **G2 — Operator recovery** | Can a privileged-but-routine operation (treasury fill, admin skip, re-queue) restore service with no funds lost? | **cap Low** |
| **G3 — Quantification** | Are BOTH `attacker_cost:` and `victim_harm:` declared with concrete figures? | **cap Low** (unquantified grief) |

**Required fields.** Every DoS/grief finding MUST carry:

```
attacker_cost: ~$12 in dust + gas, UNRECOVERABLE (NFT sits at a blacklisted address forever)
victim_harm:   withdrawals delayed until TREASURY manually fills; no funds lost
operator_recoverable: true            # true | false — if false, say why in one clause
```

**Self-admission rule (G2, automatic).** If the finding's own Description/Impact text concedes a recovery path — *"the TREASURY can still recover"*, *"requires manual fills"*, *"the admin can skip"* — it is treated as `operator_recoverable: true` and capped at Low **unless** the author explicitly sets `operator_recoverable: false` and justifies it. A writeup that argues High→Medium using the existence of a recovery path has already conceded G2; that same fact argues Medium→Low.

**A passing PoC does not clear these gates.** The DRE finding had `[FORK-PASS]`. An executable oracle proves the *mechanism*, never the *economics* — so these gates run **before** the proven-only cap and cannot be rescued by evidence tags.

**Scope.** These gates apply to availability/griefing impact only. Direct theft, permanent fund loss, and accounting drift are unaffected — an attacker who spends $10k to steal $1M is not "uneconomic."

---

## Downgrade Modifiers

- **Grief economics** (G1/G2/G3 above) → cap at Low for any DoS/griefing finding that fails a gate
- Attack requires FULLY_TRUSTED actor to be malicious → -1 tier (floor: Info)
- View-function-only impact → cap at Medium
- On-chain-only exploit (no UI path) → -1 tier (only if impact confined to on-chain)
- Attack requires control of block production on an external chain (Bitcoin mining, ETH proposer slot, Cosmos validator-set position) → **cap at Low for contest mode, cap at Medium for bounty mode**. Applies when the on-chain step is trivial but the precondition is "produce or steer a specific block on another chain whose state this protocol consumes" (SPV light clients, optimistic bridges, ZK bridges with miner-controlled witness). Contest judging treats this prerequisite as Low-likelihood regardless of marginal-cost arguments (e.g. "a top-5 mining pool can craft the block for $0 marginal cost"): the pool of capable entities is small (~10 mining pools, ~rotating beacon committee), the action requires hours-to-days of opportunistic waiting, and reputational/legal exposure deters realistic use. Origin: Atomiq H-01 CVE-2012-2459 audit (2026-05-27); see [[M27-realistic-attacker-severity]] for the sibling capital-dependent attack framework.
