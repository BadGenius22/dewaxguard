# Solidity / EVM — Platform Quirks & Protocol-Family Defenses

> Read before any `LANGUAGE=evm` audit. This is **negative knowledge**: structural defenses that recur across EVM protocol families and pre-empt whole hypothesis classes. It complements `refuted/INDEX.md` (RF-13..RF-15) — the RF entries are the class-level refutations; this file is the family/context that tells you *which* refutation to reach for. Verify the structural condition still holds on the current target before dismissing anything (per the refuted-index amendment rule).

---

## 1. Angle Transmuter fork family (diamond-proxy over-collateralized stablecoin)

Detect: EIP-2535 diamond, facets `Swapper`/`Redeemer`/`Getters`/`SettersGovernor`, `LibOracle`, storage `normalizedStables`/`normalizer`, agToken-style `TokenP`. `Swapper.sol` often keeps an `AngleProtocol`/`angle-transmuter` attribution comment. Forks seen: Parallel Protocol.

Built-in defenses (do NOT re-derive as bugs — verify present, then move on):
- **Internal-counter accounting** — mint/redeem/collateral-ratio price off `normalizedStables` (a storage counter), NOT `totalSupply()`/`balanceOf`. → flash-mint / donation cannot move pricing (see **RF-13**).
- **`restricted` per-selector gating** — every fund-critical setter/facet fn uses one `restricted` modifier → OZ `AccessManager.canCall`. Governor-vs-guardian separation is now **off-chain AccessManager config**, not in-code (a defense-in-depth regression vs upstream — flag Info, but a guardian reaching a governor selector needs a *misconfig*, below bar).
- **Hard caps are risk limits, not solvency invariants** — exceeding `stablecoinCap`/hard-cap is not theft/insolvency; don't escalate a cap bypass to Critical on its own.
- **agToken `burnFrom`** — minter-role holders can burn any holder's balance (allowance skipped when `burner==sender`). Inherited Angle design = trusted-actor, out of bounty scope.
- **Fee curves** piecewise `xFee`/`yFee`, bounded by `MAX_MINT_FEE`/`MAX_BURN_FEE`; negative-fee gated by `checkFees` revert.

Where the fork bugs actually live (audit-delta focus): the **Parallel-added** modules on top of the Angle base — `Surplus`/`LibSurplus`, `RewardHandler`, `Savings`, `LibManager` (managed collateral, often *dormant* = single-variant enum, no manager deployed), harvesters, and the **cross-chain OFT token** (see §4).

## 2. Compound V2 fork family (lending: cToken / Comptroller / IRM)

Detect: `CToken`/`CErc20`/`CErc20Delegate`, `Comptroller`, `InterestRateModel`, `mintInternal`/`redeemInternal`/`borrowInternal`/`seizeInternal`. Forks seen: CapyFi.

- **Diff vs the audited upstream release FIRST** (`git`-clone `compound-finance/compound-protocol` at the fork's base commit, e.g. G7). Core files are usually **byte-identical to the audited base** — only the diff is live surface. Typical deltas: a whitelist gating one entry point, `compAddress=0`, `blocksPerYear` value, a custom oracle.
- **`blocksPerYear`** must match the chain's real block cadence; a wrong value is latent over/under-accrual — but if the fork *fixes* it (e.g. 2628000 for ~12s blocks) that's correct, not a bug.
- **Whitelist asymmetry** (mint-gated / transfer-open) is usually by-design + over-collateralized — trace the single `mintInternal` chokepoint, confirm seize/liquidation can't mint cTokens around it.
- **Oracle staleness**: major feeds are usually immutable Chainlink; exotic feeds are admin-fed + their markets whitelist-gated or `CF=0`. Missing-staleness is external-feed-freeze-gated → see §5 triage.

## 3. ERC4626 vault mitigations — verify these FIRST before any inflation/rounding hypothesis

- **First-depositor / donation inflation** → check for a locked share floor baked at `initialize` and/or OZ virtual-shares `_decimalsOffset` (**RF-14**). If present, the classic attack is dead — but a subtler donation-**accounting** variant can survive (run a targeted trace; two firms re-audited Parallel Savings donation).
- **Rounding** should always favor the vault: deposit→shares `Floor`, mint→assets `Ceil`, withdraw→shares `Ceil`, redeem→assets `Floor`. User eats the dust → no extractable asymmetry.
- **Yield mechanism**: continuous per-second (Taylor-compound) accrual with `_accrue()` called *before* any rate change → not retroactive, no drip to sandwich. A discrete `notifyReward` lump IS sandwichable — check which one.
- **Liveness coupling**: if `_accrue` mints reward tokens via an external `mint` right, revoking that right / pausing the token freezes the vault (incl. its own rate-to-0 escape). Governor-triggered = below bar unless a *permissionless* way to block the mint exists (e.g. a reachable global supply cap).

## 4. Cross-chain / LayerZero OFT tokens (the prime theft/insolvency surface)

- **Supply conservation**: for value `V`, source must burn exactly `V` and dest mint exactly `V` (possibly split principal-token + OFT). The **fee should be a redistribution of an already-minted slice, not new supply**. Trace `_debit`/`_credit` and confirm `mint_total == source_burn`.
- **Auth**: standard LZ v2 OApp — `_lzReceive` runs only after `OAppReceiver` enforces `msg.sender==endpoint` && `_getPeerOrRevert(srcEid)==origin.sender`; endpoint enforces nonce/payload-hash non-replay; `setPeer` is `onlyOwner`. Confirm no custom weakening before hypothesizing replay/forge.
- **Rate limits**: distinguish a **time-windowed daily** limit (fixed calendar window → ~2× burst across the UTC-midnight boundary, usually Low if bounded) from a **non-windowed global** cap (the real hard ceiling on net mint/burn). A daily-burst finding is only Low if the global cap still bounds net supply.
- **Pause coverage**: `_lzReceive` (inbound mint) is often deliberately *not* `whenNotPaused` (blocking inbound would strand already-burned source messages) — Info, not a bug.

## 5. Triage / severity notes (EVM, private-solo-bounty bar)

- **Missing oracle staleness/round-completeness check** = external-feed-freeze-gated. On Immunefi this is an **excluded best-practice class** (Info / private-disclosure) unless a *permissionless* actor can force the stale/bad value. Don't spend a PoC proving a frozen-feed scenario an attacker can't induce.
- **`restricted` / `onlyRole` / `onlyGovernor` / trusted-updater** reachability caps a finding **below the submission bar** (trusted-actor / compromised-key auto-invalidator). Only a *permissionless* or *weakly-gated-reachable-by-anyone* path qualifies for Critical.
- **Diamond (EIP-2535)** storage is keccak-anchored per struct → appended fields don't collide; a stale `Layout.sol` mirror is a *test-tooling* gap, not a production collision. `diamondCut` is the crown jewel — confirm it's strictly `restricted`.

## 6. Fork-ancestry discipline (always, for any fork)

Before breadth, identify the upstream base and `git diff` the fork against the **audited upstream commit**. The audited base is hardened; **only the fork's own additions/modifications are live surface**. Point depth budget there, give the base light coverage. (Skipping this is how you waste a whole pass cold-auditing Angle/Compound core that's already been through Code4rena.)

## 7. Scope hygiene (learned the hard way)

- Extract & verify the **full** official in-scope asset list before spawning agents (whole-repo vs specific-file vs directory assets; when N parallel impls of one interface exist, only the *listed* one is in scope).
- **Check the scoped default branch isn't frozen behind unmerged `audit/*` branches** (`git branch -r` + `git log --all --since=<scope-date>`). A frozen `main` with fixes staged on unmerged audit branches = a **known-issue minefield**: the strongest on-branch bugs are already whitehat/audit-firm-reported (duplicates, excluded). Strong deprioritize signal.

## 8. Layer-2 execution quirks (verify the harness models the target chain)

- **`block.number` on Arbitrum returns the L1 block, not the L2 block.** For L2-block semantics use `ArbSys(0x64).arbBlockNumber()`. Any logic — or PoC harness — that treats `block.number` as the L2 height (rate windows, TWAP intervals, deadline checks) is reading the wrong clock. In a fork PoC, `vm.roll` moves `block.number`; if the target reads `ArbSys`, `vm.roll` has no effect and you must mock the precompile at `0x64` instead. Confirm which the contract reads before trusting any timing-dependent PoC result. (`block.timestamp` is L2 wall-clock on Arbitrum and behaves normally — the trap is specifically the block *number*.)
