# L1 Severity Matrix (Immunefi v2.3-aligned)

> **Phase**: 5d (Bug Validator) and Phase 4a (Inventory) — for findings produced in L1 mode (`/dewaxguard l1`)
> **Purpose**: L1 node bugs have different impact categories than smart-contract bugs. "Theft of $X" is rarely the right impact axis; "validator-set partition", "chain halt", "honest validator slashed" usually are. This matrix is Immunefi v2.3-aligned and takes precedence over `rules/severity-matrix.md` when LANGUAGE ∈ {go, cpp-l1} OR when the protocol is classified as `l1` in `attack_surface.md`.

---

## Distinct from smart-contract matrix

The base matrix in `rules/severity-matrix.md` and `rules/report-template.md` uses Impact × Likelihood with impact axes (High fund loss / Medium fund loss / Low / Info). For L1, "fund loss" is a SECONDARY impact — the primary axes are consensus health, network integrity, and validator economics:

| L1 impact axis | Smart-contract analog | Why distinct |
|----------------|------------------------|--------------|
| Chain halt (no finality > 1hr) | Permanent fund lock for an entire protocol | Affects every user of every dApp on the chain |
| Validator slashing of honest validator | Theft of validator's stake | Slashing is irreversible and cascades to delegators |
| Consensus stall (re-org > 7 blocks) | Re-org reverting confirmed txs | Affects bridge withdrawals, exchange deposits |
| Network partition | Censorship | Subset of validators isolated; possible double-spend in the partition |
| Theft of staked funds | Theft of contract funds | Direct value loss |
| Block production censorship | Permanent action prevention | User cannot submit tx; protocol unusable |
| Resource exhaustion DoS | Function DoS | Whole node crashes; loss of liveness |
| Validator misbehavior unpunished | Admin rug | Trust assumption violated; economic security degrades |

---

## The Matrix

| Impact | Likelihood: High (no prereq, anyone) | Likelihood: Medium (specific cond) | Likelihood: Low (unlikely setup) |
|--------|--------------------------------------|------------------------------------|----------------------------------|
| **Chain halt / network-wide fork** | **Critical** | **High** | **Medium** |
| **Honest validator slashed (false positive)** | **Critical** | **High** | **Medium** |
| **Theft of staked funds (any validator's stake)** | **Critical** | **High** | **Medium** |
| **Consensus stall / no finality > 1 hour** | **High** | **Medium** | **Medium** |
| **Block production censorship (single validator)** | **High** | **Medium** | **Low** |
| **Network partition (subset of validators)** | **High** | **Medium** | **Low** |
| **Resource exhaustion DoS on majority of nodes** | **High** | **Medium** | **Low** |
| **Authentication bypass on admin / debug RPC** | **High** | **Medium** | **Low** |
| **Validator misbehavior unpunished (slashing false negative)** | **Medium** | **Medium** | **Low** |
| **Single-node DoS with high attacker cost** | **Medium** | **Low** | **Low** |
| **Information leak via RPC (e.g., debug_*) without auth** | **Medium** | **Low** | **Low** |
| **Code quality / spec drift / unused code** | **Informational** | **Informational** | **Informational** |

---

## Downgrade modifiers (applied after matrix lookup)

The same downgrade modifiers from `rules/severity-matrix.md` apply, with L1-specific examples:

| Modifier | Adjustment | L1 example |
|----------|-----------|------------|
| Attack requires `FULLY_TRUSTED` actor (governance, foundation key) | -1 tier (floor: Info) | "governance can vote to halt chain" — by design; not a finding |
| `WITHIN-BOUNDS` semi-trusted role | no severity change, flag only | "supermajority validators agreeing on a malicious block is by design within consensus assumptions" |
| Reproducible only on local testnet, not under real network load | -1 tier | "race condition in tx pool only triggers at 1Mtx/sec, well above mainnet throughput" |
| Affects single-validator infrastructure only (not protocol) | -1 tier (cap at Medium) | "Geth-specific RPC bug; Reth users unaffected" |
| Affects ALL clients (DIFF-PASS across implementations) | +1 tier or no change | spec ambiguity; cannot blame an implementation |
| Information-only impact, no state change | cap at Medium | "wallet address leaks via RPC method but no fund movement" |
| Affects testnet only (not mainnet config) | cap at Informational | "Holesky-specific deposit contract address has a typo" |

---

## Likelihood calibration

Likelihood for L1 differs from smart contracts because the attacker capability spectrum is wider:

| L1 likelihood | Means | Examples |
|---------------|-------|----------|
| **High** | Any peer or any RPC client can trigger; no special access | RLP decoder crash on a crafted packet; mempool DoS via low-fee floods |
| **Medium** | Requires running a validator OR being on a specific peer's allowlist OR ≥ 1% stake | False-positive slashing requires the attacker to be a validator; eclipse requires controlling 8 of 50 peer slots |
| **Low** | Requires being a specific validator (e.g., the proposer for a specific slot) OR ≥ 33% stake OR governance-controlled multi-step | Honest validator framed by 33%-stake attacker; consensus stall requires colluding minority |

---

## Per-platform interpretation (when L1 mode + a specific bounty platform is named)

### Immunefi (the canonical reference)

L1 chain protocols use Immunefi's "Layer 1 / Layer 2 Blockchain" severity table:

- **Critical**: Network not being able to confirm new transactions (Total network shutdown); Permanent freezing of funds (Fix requires hardfork); Direct theft of any user funds, whether at-rest or in-motion (other than unclaimed yield)
- **High**: Theft of unclaimed yield; Permanent freezing of unclaimed yield; Temporary freezing of funds for at least 1 hour; Cluster of nodes goes offline for a brief duration
- **Medium**: Smart contract unable to operate due to lack of token funds; Block stuffing; Griefing; Theft of gas; Unbounded gas consumption
- **Low**: Smart contract fails to deliver promised returns, but doesn't lose value; A node operator unable to operate solely due to actions by another node operator

When `Platform: immunefi` is set in CLAUDE.md, the validator translates dewaxguard L1 matrix entries to Immunefi categories. Mapping:

| dewaxguard L1 finding | Immunefi category |
|------------------------|-------------------|
| Chain halt | Critical: Network not being able to confirm new transactions |
| Honest validator slashed | Critical: Direct theft of any user funds (slashing IS fund loss to the slashed validator) |
| Theft of staked funds | Critical: Direct theft of any user funds |
| Consensus stall > 1hr | High: Temporary freezing of funds for at least 1 hour |
| Cluster offline | High: Cluster of nodes goes offline for a brief duration |
| Mempool DoS / Block stuffing | Medium: Block stuffing or unbounded gas consumption |
| RPC info leak | Low / Medium (depends on data sensitivity) |

### Code4rena L1 contests (when applicable)

C4 has run L1 contests (Stellar, Cosmos chains). The judging team uses dewaxguard L1 severity matrix as-is; the Realism Filter on `admin-trust` still applies (-1 tier for "governance can fix it").

### Sherlock L1 bounties

Sherlock uses dewaxguard L1 severity matrix; an additional threshold rule applies: at the Medium tier, the finding must affect > 0.01% of network value OR cause > 1 hour of node downtime.

---

## Evidence tag → severity floor

L1 evidence tags imply a severity floor independent of the matrix:

| Evidence tag | Severity floor | Reason |
|--------------|----------------|--------|
| `[DIFF-PASS]` | High | Two implementations disagree on the same input — at least one is wrong, and the network can fork |
| `[NON-DET-PASS]` | High | Same input on two same-version validators yields different state — direct consensus risk |
| `[CONFORMANCE-PASS]` | matches severity of violated spec invariant | A spec violation is as bad as the invariant it breaks |
| `[FUZZ-PASS]` | Medium | Fuzz found a counterexample; severity then determined by the resulting impact |
| `[CODE-TRACE]` | caps at CONTESTED in `core` mode, at LOW in `thorough` mode | No execution evidence |
| `[POC-PASS]` | matches matrix | Executed proof |

If the matrix says "Low" but the evidence is `[DIFF-PASS]`, the FINAL severity is High (evidence floor dominates).

---

## Self-check for the validator agent

Before emitting `severity_check:`:

- [ ] Did I use the L1 matrix, not the smart-contract matrix? (Confirm: LANGUAGE ∈ {go, cpp-l1} OR protocol_type=l1)
- [ ] Did I apply realism modifiers AFTER the matrix? (Trusted-actor -1 tier, etc.)
- [ ] Did I check the evidence floor? (DIFF-PASS / NON-DET-PASS = High minimum)
- [ ] Did I cite the Immunefi-equivalent category when Platform: immunefi is set?
- [ ] Did I record `severity_pre_modifier` if any downgrade applied?
