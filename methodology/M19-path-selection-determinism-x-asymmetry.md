# M-19: Path-Selection Determinism × Economic-Asymmetry Matrix

> **Cross-language audit methodology** for path-finding / route-selection / DEX-aggregator code in any blockchain.
> **Validated origin**: XRPL April 2026 audit, Pathfinder × MPT full 8-agent breadth (0 Medium+ surfaced; the methodology's high-yield call was correct: most asymmetries refute via the consensus-bound-vs-RPC-only distinction).

---

## When to apply

Apply M-19 to any codebase that:

1. Composes a **path-finding / route-selection / aggregator** layer — e.g., XRPL Pathfinder, Uniswap V3 SmartOrderRouter, 1inch Pathfinder, Cowswap solver, Jupiter aggregator (Solana), Orca route-handler, DeepBook router (Sui), PancakeSwap-style aggregator (Aptos).
2. Routes payments / swaps across **multiple asset types** that have different arithmetic representations (integer vs decimal, native vs wrapped, Coin<T> vs FungibleAsset, ERC-20 vs ERC-4626 vs ERC-721) OR different fee mechanics (transfer fee, swap fee, withdrawal fee, fee-on-transfer carve-outs).
3. Uses **iterative refinement / multi-pass convergence** to balance offers against requested amounts.
4. Has any non-trivial **comparator or sort** that orders candidate paths/offers.
5. Processes **off-consensus** path suggestions that are then submitted as **consensus-bound** transactions (the architectural seam where most false-positive Critical findings live).

---

## The matrix (two axes, ~35 cells per audit)

### Axis 1 — Determinism dimensions

| Cell | Detection workflow | Common bugs |
|---|---|---|
| **D1: Hash-map / hash-set iteration order** | Grep for `unordered_map`, `unordered_set`, `HashMap`, `BTreeMap`-replaced-with-`HashMap`, `Map<K, V>` where `K` is a value type. For each: trace whether iteration order influences output. If output is consensus-relevant, flag. | std::unordered_map iteration order is implementation-defined; cross-validator divergence; cross-process divergence within same machine (process-salt). |
| **D2: Pointer-comparison in candidate sort** | Grep for `std::sort` / `std::stable_sort` / `Vec<T>.sort_by` / `.sort()`. Inspect comparator. Look for `&a < &b` / `reinterpret_cast<>` / `std::less<T*>` / pointer arithmetic in the predicate. | Memory-address-dependent ordering; non-deterministic across allocator implementations. |
| **D3: Floating-point math in ranking heuristic** | Grep for `double`, `float`, `f64`, `f32` in the path/order-quality computation. Check whether IEEE-754 cross-platform behaviour differs (different rounding modes, different `pow()` implementations, transcendentals). | Cross-validator divergence on math operations that are not bit-exact across compilers/architectures. |
| **D4: Unspecified order of evaluation** | Grep for sequential side-effects in expression-statements (e.g. `f(g(), h())` in C++ where g and h have observable side effects). | Compiler-dependent ordering; rare but surfaces in C/C++ DEX router code. |
| **D5: `std::sort` vs `std::stable_sort` distinction** | For every sort site, verify whether the comparator produces a strict total order (use `stable_sort` is unnecessary) OR a strict weak order (must use `stable_sort` to preserve input order on ties). Misuse of `sort` with weak-order comparator → non-deterministic output. | Halborn 7.1 (XRPL) — exact pattern. |
| **D6: Comparator strict-weak-order violation** | For every sort comparator: irreflexivity check (`cmp(x,x) == false`), asymmetry check (`cmp(a,b) → !cmp(b,a)`), transitivity check (across 3 elements). Any violation = UB in std::sort. | Generalizable to any router with custom sort key. |
| **D7: Memory-address-dependent ordering** | Look for any data structure whose iteration order depends on allocation order (e.g., free-list allocators, intrusive lists). | Subtle; surfaces in custom-allocator DEX engines. |

### Axis 2 — Economic-asymmetry dimensions

| Cell | Detection workflow | Common bugs |
|---|---|---|
| **E1: Token A→B vs B→A direction asymmetry** | For every fee/quality computation, trace the formula in BOTH directions. Check rounding direction. If `quality(A→B) ≠ quality(B→A)` for the same exchange rate, flag. | Asymmetric rounding (BookStep mulRatio); fee-on-one-side bugs. |
| **E2: Self-issued offer / self-quoted price advantage** | Construct a scenario where the attacker IS the issuer of one asset on the path. Check whether quality computation factors issuer identity. If yes, flag — issuer has unfair ranking advantage. | EVM: Uniswap V3 fee tier abuse. |
| **E3: Transfer-fee carve-outs** | Enumerate every transfer-fee-skipping condition (e.g. issuer-as-sender, issuer-as-receiver, AMM pool, fee-on-transfer exemption list). For each: who can trigger it? Is it asymmetric across asset types? | EVM: ERC-20 fee-on-transfer carve-outs vs ERC-4626. |
| **E4: Pseudo-account / smart-account immunity** | Identify all account types that bypass standard auth (XRPL pseudo-accounts; EVM smart contracts with custom IERC1271; Solana PDAs with no signer). Check whether the path-finder/router treats them correctly as intermediaries. | Pre-existing carve-outs may not be caught by the discovery layer. |
| **E5: Multi-hop fee composition direction** | For paths IOU→MPT vs MPT→IOU vs MPT→MPT vs IOU→IOU, trace fee composition formula. Verify commutativity (`compose(A, B) == compose(B, A)` for the multiplicative portion). | Non-commutative composition in custom fee engines. |
| **E6: First-depositor / last-withdrawer / zero-state edge** | What happens at the boundary state (empty pool, single user, max liquidity)? | ZERO_STATE_RETURN skill class (ERC-4626, vault-share). |
| **E7: Cross-validator quality divergence** | Same inputs across two validators → same path quality? Same liquidity computation? | EVM: Vyper vs Solidity rounding. |
| **E8: Frozen / paused / locked state mid-route** | Can attacker freeze a competitor's offer mid-route? Does path-finder ignore frozen offers? Does execution re-check at consumption? | Lock-state re-validation at consumption is the safe pattern. |
| **E9: Stale parameter retroactive effect** | Mutable economic parameter (transfer fee, swap fee, oracle price) consumed by cross-ledger-persistent SLEs (escrow, check, offer). Lock-in at create OR live-read at consume? Asymmetric handling → audit smell. | Escrow locks; OFFER/CHECK live-read = asymmetric. |
| **E10: Convergence iteration count differs by asset type** | Multi-hop iterative refinement: does an exact-arithmetic asset converge in same iterations as a decimal-arithmetic asset? Does any asset type cause unbounded loop? | Hardcoded asset-agnostic iteration cap is the safe pattern. |
| **E11: Fee / burn / transfer-rate rounds to zero at small amounts (value escape)** | For every fee / burn / transfer-rate computation, substitute small-but-nonzero amounts and the round-to-zero boundary. If the fee or burn rounds to 0 while value still moves (offer crosses, payment delivers, supply transfers), the issuer/protocol silently loses fee revenue or supply accounting drifts. Round fees UP (or gate the round-to-zero boundary) is the safe pattern. | **Sherlock 1260 F16** (High): MPT CLOB offer crossing rounds transfer-fee burn down to zero. EVM: fee-on-transfer rounding to 0 for dust; ERC-4626 share rounding. |

---

## Detection workflow (per cell)

1. **Locate the cell's surface in the codebase** (use grep / static analyzer / IDE for the patterns above).
2. **Trace the data flow** from input to output for that cell. Is the value cached? Mutable? Read fresh? Influenced by external state?
3. **Construct a two-validator (or two-process) scenario** for determinism cells, and a two-actor (attacker vs victim) scenario for asymmetry cells.
4. **For consensus-relevance check** (THE CRITICAL ANTI-FP GATE):
   - Is this code invoked during `doApply` / consensus-bound execution? OR is it invoked only off-chain (signing, RPC, mempool simulation, frontend)?
   - If **off-consensus only**: the cell's worst case is UX inconsistency. Cap severity at Low. Most "consensus-split" findings reduce to this.
   - If **consensus-bound**: any non-determinism = consensus split = Critical. Verify with two-validator PoC.
5. **For asymmetry cells**: identify a concrete attacker-victim pair where the asymmetry produces value extraction. If only "could be unfair" without a $-loss target, classify as Informational.
6. **Dedup against existing manifest entries** before promoting to a finding (M-10 mandatory pre-submission step).

---

## Anti-FP gates (mandatory)

### Gate 1: Consensus-bound vs RPC-only distinction

> **The single most important architectural fact when auditing a path-finder / router.**

For each suspect bug:
1. Identify the call sites of the function. Is ANY call site inside `doApply` / consensus execution?
2. If NO (only signing-time or RPC-only): worst case is per-server UX inconsistency. Cap severity at Low. Cannot be a consensus-split.
3. If YES: continue investigation. Construct two-validator PoC.

Validated origin: the audited Pathfinder layer is invoked only from signing / RPC paths, NEVER from any transactor's `doApply`. This single architectural fact refutes ALL Pathfinder-internal consensus-split hypotheses by architecture, not by bug analysis.

### Gate 2: Pre-existing legacy code (Sherlock T-06)

> **Sherlock contests classify pre-existing-impact bugs as known issues.**

For each suspect bug, diff the current code vs the previous commit. If the buggy mechanism is byte-identical to the prior version (only consumers changed), classify as OOS.

### Gate 3: Trust-model exclusion

> **Per-contest trust model dictates which actors are trusted.**

For each suspect bug, identify the actor(s) required to trigger it. If the actor is on the trusted list (validators, public server admins, protocol issuers), the finding is OOS.

### Gate 4: Defense-in-depth gap

> **Discovery-layer leaks are not exploits if the execution layer catches them.**

For each suspect bug in the path-finder layer, trace the SAME code path through the consensus-execution layer. If the execution layer re-validates and fail-closes, the discovery-layer bug is Informational only.

---

## Cross-language generalisation

| Pattern | EVM example | Solana example | Sui example | Aptos example |
|---|---|---|---|---|
| **D5/D6 comparator UB** | Uniswap V3 SmartOrderRouter sort comparator; 1inch Pathfinder | Jupiter aggregator route ordering with non-strict-weak comparator | DeepBook order-matcher with `vector::sort_by` | PancakeSwap-style router with custom `cmp` |
| **D1 hash-map iteration order** | Solidity `mapping` is keyed but cannot be iterated; LP token holders enumerated via events (off-chain) | `HashMap<K, V>` in Anchor / `BTreeMap` preferred | `Table<K, V>` is deterministic by key | `Table<K, V>` deterministic by key |
| **D3 floating-point in ranking** | Cowswap solver uses fixed-point internally; off-chain solvers use float (off-chain → not consensus) | Jupiter aggregator off-chain | DeepBook on-chain (no float) | PancakeSwap on-chain (no float) |
| **E1 token-direction asymmetry** | Curve-style stablepool with imbalanced fees | Raydium concentrated liquidity asymmetric tick fees | Cetus AMM tick spacing asymmetry | Tsunami Finance pool fee asymmetry |
| **E2 self-issued offer advantage** | Self-balancing AMM hop where attacker is one of the LPs | Self-issued SPL Token + Token-2022 with custom transfer hook | Self-issued Coin<T> with custom witness | Self-issued FungibleAsset with custom transfer ref |
| **E3 transfer-fee carve-outs** | ERC-20 fee-on-transfer + ERC-4626 vault-share asymmetry | Token-2022 transfer-fee extension carve-outs | Coin<T> vs FungibleAsset fee asymmetry | Coin vs FA dual ecosystem |
| **E4 pseudo-account immunity** | Account abstraction smart accounts (ERC-4337); IERC1271 contract signers | PDAs with no signer; CPI signer seeds | Sui object capabilities (witness pattern) | Aptos resource accounts |
| **E7 cross-validator divergence** | Vyper vs Solidity rounding; cross-EVM-fork divergence (e.g., zkSync Era arithmetic) | Cross-Solana-RPC simulation divergence | Cross-Sui-validator object-version divergence | Cross-Aptos-validator block-STM divergence |
| **E9 stale parameter retroactive effect** | Curve admin fee changes affecting in-flight orders; AMM swap fee changes affecting pending swaps | Token-2022 TransferFeeConfig affecting Jupiter pending orders | Sui Kiosk with mutable Cap fees affecting listings | Aptos AMM pool fees affecting pending swaps |
| **CONSENSUS-RELEVANCE GATE** | All EVM aggregators are off-chain (paths computed off-chain, submitted as `swap()` call) → no consensus-split surface | Jupiter is off-chain | DeepBook is on-chain (matching at consensus) — gate applies! | PancakeSwap on-chain |

**Methodology yield observation**: M-19 is highest-yield for **on-chain DEX matching engines** (DeepBook, on-chain CLOB) where the determinism cells are consensus-bound. For **off-chain aggregators** (Uniswap V3 Router, 1inch, Jupiter), the methodology produces mostly Informational findings because the consensus-bound execution is downstream of the suggestion layer.

---

## Audit checklist (apply per audit)

For every path-finder / router / aggregator codebase under audit:

- [ ] **Step 0**: Determine consensus-bound vs RPC-only call sites for the entire pathfinder/router file. Document in framework-facts.
- [ ] **Step 1**: Enumerate every `std::sort` / `std::stable_sort` / equivalent call. Verify comparator strict-weak-order. Apply Gate 4 (fail-closed at execution).
- [ ] **Step 2**: Enumerate every `unordered_map` / `unordered_set` / `HashMap` iteration. Trace consumer. If consensus-bound, flag.
- [ ] **Step 3**: Enumerate every floating-point operation in path-quality / cost / fee computation. If consensus-bound, flag.
- [ ] **Step 4**: For each pair (asset_in, asset_out) supported, verify quality formula symmetry under direction reversal.
- [ ] **Step 5**: For each fee-skipping condition (issuer-as-sender, AMM pool, exemption list), verify symmetry across asset types.
- [ ] **Step 6**: For each pseudo-account / smart-account / abstract-account type, verify path-finder treats correctly as intermediary (NOT as principal).
- [ ] **Step 7**: For each mutable economic parameter (transfer fee, swap fee, lock duration), verify all cross-ledger-persistent consumers either lock-in OR document retroactive semantics.
- [ ] **Step 8**: Convergence loop iteration count must NOT depend on asset type's representable precision. Hard-bounded constants only.
- [ ] **Step 9**: Subscribe-stream / event-broadcast surfaces must not leak per-subscriber path information cross-subscriber.
- [ ] **Step 10**: Apply M-10 dedup before promoting any finding.

---

## Validated finding

**XRPL April 2026 (Pathfinder × MPT domain)** — 8-agent breadth populated ~13 cells × 8 dimensions with the above matrix. Outcome:
- **0 Medium+ submittables** — every candidate refuted via Gate 1 (RPC-only / not consensus-bound), Gate 2 (pre-existing legacy code), or Gate 4 (execution-layer fail-closed).
- **1 Low submittable** (RPC-layer UX issue connecting MPT source-currency + send_max combination to a misleading error code).
- **2 architectural facts** extracted: Pathfinder is RPC-only / never invoked at consensus; the comparator strict-weak-order fix from a prior audit was correctly incorporated.

---

## Related methodology

- **M-04** (feature-pool coverage) — every router finding must connect to a reward-pool feature.
- **M-09** (SYNC_GAP) — many path-stale-parameter bugs are SYNC_GAP instances.
- **M-10** (prior-audit dedup) — comparator-fix re-validation often reveals the bug is already fixed in delta.
- **M-15** (expiry-race matrix) — both methodologies share the consensus-bound vs RPC-only distinction.
- **M-17** (mutable-config-flag audit) — E9 stale parameter cell is the M-17 Pattern 6 (asymmetric on-chain-state-lockin).
- **M-20** (wire-format mature-layer audit) — both methodologies inherit Gate 1 (consensus-bound vs RPC-only).

---

## ROI

XRPL Pathfinder × MPT domain yielded 1 Low from this methodology (4 cells RPC-only-capped). The methodology's main yield is the structural map of the router's attack surface — most cells refute via Gate 1, leaving the genuinely consensus-bound surfaces highlighted for depth probing. Highest yield expected on **on-chain DEX matching engines** (DeepBook on Sui; on-chain CLOBs); lower yield on off-chain aggregators (Jupiter, 1inch, Uniswap Router) where most determinism is off-consensus.
