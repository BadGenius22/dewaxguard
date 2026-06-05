# DewaxGuard Changelog

## [1.19.0] - 2026-06-05

**Origin**: Upstream sync with solidity-auditor v3 (pashov/skills `c9ce8cf`, "attacker-framing 12-agent rewrite", 2026-06-04). dewaxguard's `agents/hacking-agents/` is derived from solidity-auditor's hacking agents; v3's improvements were ported in, adapted for dewaxguard's multi-language + pipe-format-parser pipeline. Two integration decisions taken by the maintainer: (1) **roster = add-5-gated-by-mode** — keep vector-scan (dewaxguard's recon `blackhat-maps`, `parse_findings.py`, self-calibration, and M-18/M-21 depend on it; v3 dropped it) and spawn the 5 new attacker-framing agents in **thorough mode only**, so thorough = 8 + 5 = 13 (not v3's 12). (2) **mental tools = ship-content-light-touch** — port senior-auditor-sop + a shared-rules "Mental tools" reference WITHOUT orchestrator marker-grep enforcement (dewaxguard already has a Nemesis-Feynman phase) and WITHOUT disturbing the `FINDING |` pipe format consumed by `scripts/parse_findings.py`.

### Added
- **5 attacker-framing hacking agents** (`agents/hacking-agents/`, thorough-mode only) — cross-lens "gap" hunters that the single-specialty core 8 miss, each adapted with a `## Language routing` section (EVM/Solana/Move/C++) and the house FINDING/LEAD pipe output:
  - `asymmetry-agent.md` — paired-function / branch / writer-reader storage-write mismatches.
  - `boundary-agent.md` — disciplined corner-case enumeration at every external boundary (no-code receiver, non-standard token, sentinel-address, bytes-decode truncation).
  - `flow-gap-agent.md` — execution × periphery × first-principles seams (bugs needing ≥2 lenses).
  - `numerical-gap-agent.md` — precision × invariant × boundary seams.
  - `trust-gap-agent.md` — access × economics × asymmetry seams (notes realism-filter downgrade for fully-trusted-actor exploits).
- **`references/senior-auditor-sop.md`** — Feynman / Socratic / Inversion mental tools (language-generalized from v3). Referenced light-touch from shared-rules; not orchestrator-enforced.

### Changed
- **`agents/hacking-agents/invariant-agent.md`** — appended v3's 8 coupled-mutation attack moves to "Step 2 — Break each invariant" (stale-cache-after-mutation, timer reset via secondary path, in-flight global-param mutation, view/write divergence, partial-mint peg break, emergency value-strand, cap bypass on secondary path, cross-read state-price coupling).
- **`agents/hacking-agents/math-precision-agent.md`** — appended v3's 8 cast/shift/edge-divisor attack moves (narrow-int sign loss, intermediate-shift overflow, sole-occupant boundary, cast-wrap at saturation, tiny-principal accrual truncation, unsigned-bonus underflow, wrong-bitmask, unconstrained-edge divisor).
- **`agents/hacking-agents/periphery-agent.md`** — appended v3's 7 encoder/storage-context/oracle attack moves (cross-encoded recipient truncation, wrong storage-context library read, ERC165 dispatch fallback, magic-ID helper lookups, same-block oracle read, single-block oracle manipulation, divergence-check dead code).
- **`agents/hacking-agents/shared-rules.md`** — added a "Mental tools (senior-auditor mindset)" section between Reading and Cross-contract patterns. Trigger→tool table (Feynman/Socratic/Inversion) + explicit instruction that inline `[Tool: ...]` markers live in working text, NOT in `FINDING |`/`LEAD |` blocks (parser-safe). Output-format section untouched.
- **`SKILL.md`** — frontmatter description, banner, modes table (thorough Breadth 8→13), pipeline overview, Phase 3 roster (new "Attacker-framing agents — thorough only" subtable #9-13), and FILE STRUCTURE listing.
- **`prompts/phases/30_breadth.md`** — agent-set-per-mode table (thorough = 13) and agent dispatch table rows 9-13 (output files, reused preprocessor maps, budgets), both marked thorough-only.

### Not changed (deliberate divergence from v3)
- **vector-scan-agent retained.** v3 retired it; dewaxguard keeps it because `build_recon_maps.sh` (blackhat-maps), `parse_findings.py`, `improve/SELF-CALIBRATE.md`, `improve/CONSOLIDATE.md`, M-18 and M-21 all reference it. Removing it is pipeline surgery, not a content port.
- **No orchestrator marker-grep verification** of the mental-tool protocol (light-touch only) and **no driver/content-gate changes** — the new agents reuse the existing breadth dispatcher, output files, and gates.
- **light / core modes unchanged** — the 5 new agents do not spawn there.

## [1.18.1] - 2026-06-04

**Origin**: Wiring the M-30 recon trigger so the signature-binding/replay lens auto-fires — v1.18.0 added the methodology but left its trigger as "proposed". Raised while reviewing EVM applicability: M-30 is the most EVM-relevant of the v1.18.0 additions (EVM is signature-auth-heavy — EIP-712 / permit / Permit2 / EIP-3009 / EIP-1271 / ERC-4337).

### Added
- **`scripts/build_recon_maps.sh` section (m) signature-binding-map** — emits `signature-binding-map.md` with machine-readable `SIGNATURE_BOUND_AUTH` + `CROSS_CHAIN_REPLAY_SMELL` flags. Detects (A) signature-verification call sites, (B) signed-payload/typehash definitions, (C) domain-separation & replay-guard evidence, (D) the recipient-unbound-by-signature red flag. EVM gets rich coverage (`ecrecover` / `ECDSA` / `SignatureChecker` / EIP-712 / permit / Permit2 / `UserOperation`); Solana/Stellar/Aptos/Sui/C++ get a generic verify-primitive grep (ed25519 / secp256k1 / BatchSigner / multisign) — **cross-language, unlike the EVM-only M-29 detector**. `CROSS_CHAIN_REPLAY_SMELL=true` fires when verify sites exist but no chainId/nonce/domain-tag evidence is found.

### Changed
- **`methodology/M30-signature-binding-replay.md`** — trigger line updated from "proposed" to the live `build_recon_maps.sh` flag.

## [1.18.0] - 2026-06-04

**Origin**: Post-audit improvement protocol run on Sherlock 1260 (XRPL April 2026) against the final preliminary-reward gist. The audit shipped 5 valid findings (~$3,047, 3/5 reward pools) but **0 of the contest's 9 High/Critical families**. The RC-AGENT exclusion test classified the 9 H/C misses as 3× RC-METHOD, 2× RC-DEPTH, 4× RC-AGENT. The 4 RC-AGENT misses (F60 $24k-solo BookStep fee-account, F15 AMMClawback auth, F39 book_offers, F82 sponsored cross-currency) were analyzed-but-mis-reasoned and produce **no** rule change per the anti-bloat / RC-AGENT-presumption gate. The 5 fixable misses produce 1 new template + 3 targeted extensions.

### Added
- **`methodology/M30-signature-binding-replay.md`** (~90 lines) — Signature-Binding / Replay / Domain-Separation audit. New attack class, zero prior coverage. Binding-table method (signer / signing-for account / envelope / chain / tx-type / nonce / expiry / value-params) + bearer-token test (F4 shape) + signing-for test (F3 shape). Cross-language (EVM EIP-712/permit/Safe, Solana ed25519 sysvar, XRPL BatchSigner/multisign, Move/Cosmos BCS/SignDoc). General complement to the EVM-specific M-29. Closes the gap that missed **F4** (Critical, 13 finders) and **F3** (High, 9 finders).

### Changed
- **`methodology/M16-zk-proof-bundle-composition.md`** — added **Phase 2.7 Adversarial Forgery Construction**. M-16 previously audited composition + reachability and could conclude "sound modulo completeness" without ever attempting a soundness break; the Domain-15 run did exactly that and missed **F30** (Critical, 15 finders — forged proof drains shared confidential backing). New mandatory step: assume a malicious prover, state the conservation relation, and specifically test the shared/pooled-backing drain before declaring soundness. Composition-correct ≠ forgery-resistant.
- **`methodology/M18-account-lifecycle-cleanup-switch.md`** — broadened scope from account-level `AccountDelete` to **ALL object-teardown ops** (AMM/Vault/LoanBroker delete, IssuanceDestroy, market/position close) and added the **shared-object grief variant** (attacker plants a permanent obligation on a pooled object the owner must tear down). Was AccountDelete-centric and missed **F13** (High, 19 finders).
- **`methodology/M19-path-selection-determinism-x-asymmetry.md`** — added economic-asymmetry dimension **E11 fee/burn/transfer-rate rounds to zero at small amounts (value escape)**. Missed **F16** (High — MPT CLOB offer crossing rounds transfer-fee burn to zero).
- **`methodology/INDEX.md`** — registered M-30; added post-mortem-extensions note for M-16/M-18/M-19.
- **`LEARNED_INDEX.md`** — appended the Sherlock 1260 post-mortem entry (5 valid / 0 H-C recall; RC distribution; meta-root-cause RC-CONTEXT domain mismatch: smart-contract-oriented vector libraries vs C++ consensus node + ZK crypto).

### Not changed (anti-bloat / RC-AGENT presumption)
- F60 (BookStep wrong-account fee — $24k solo find, deep-read across 76 files), F15 (AMMClawback authorization — 43 files), F39 (book_offers — 10 files), F82 (sponsored cross-currency). All in heavily-analyzed code → RC-AGENT reasoning-depth misses, not methodology gaps. No rule added — adding rules for reasoning misses is bloat without recall gain.

## [1.17.0] - 2026-05-28

**Origin**: M-29 detector false negative during the Alchemist Aludel v1 audit (TVL-scanner batch, 2026-05-28). v1.16.0's Section B grep targeted SquidRouter naming (`executeOnBehalf`, `executeBundle`, `executeBatch`, `swapOnBehalf`, `executeOnSafe`, `delegateBundler`, ...) and missed the Geyser/Aludel family which uses inherited staking-pool naming. The Alchemist Aludel `unstakeAndClaim(address vault, address recipient, uint256 amount, bytes permission)` function was a textbook M-29 action-binding failure (signature binds `delegate+token+amount+nonce` but not `recipient`, enabling MEV signature front-running with attacker-controlled recipient), and the detector grep would NOT have flagged the contract for M-29 lens application. v1.17 closes this gap.

### Changed

- **`scripts/build_recon_maps.sh` Section B grep** — extended with Geyser/Aludel/staking-pool naming patterns: `getPermissionHash`, `calculateLockID`, `onlyValidSignature`, `UNLOCK_TYPEHASH`, `LOCK_TYPEHASH`, `IUniversalVault`, `IRageQuit.rageQuit`, `unstakeAndClaim`, `lockAndStake`, `rageQuit`. Captures the Ampleforth Geyser / Alchemist Aludel / Crucible NFT-vault delegate-executor family in addition to the Squid/1inch/0x router-on-behalf family. The new grep also doubles as a generic "permission-signature pattern" detector: any contract that constructs a typehash with `UNLOCK_*` / `LOCK_*` / `getPermissionHash` naming should be audited under M-29 STEP 2 (auth-gate inversion → hash binding check).

- **`methodology/M29-safe-module-delegate-executor.md`** — new "Case study 2: Alchemist Aludel v1" section documenting the specific recipient-unbound-by-unlock-signature pattern. Includes (a) the vulnerable code shape with `_validateAddress(recipient)` being sanity-only, (b) the MEV signature front-running attack sequence (mempool extraction → relay with attacker recipient → vault accepts because typehash check passes), (c) the explicit detection rule: "if a public function takes a recipient/to/beneficiary/dest parameter AND validates a signature whose typehash does NOT include that parameter, flag as Critical under Step 2 hash-binding check", (d) severity calibration note explaining why the specific Alchemist instance is Low (sub-$100K per vault, victim sees front-run) but the bug class is High-to-Critical when per-vault TVL > $100K or relayer/bundler hides the front-run from the victim.

### Filter alignment

The extended grep does NOT loosen the user's severity filter — per-finding severity still goes through the realism-filter and matrix rules (sub-$100K extractable caps at Low). What v1.17 fixes is **detector coverage**: the M-29 lens now triggers on the Geyser/Aludel family so the methodology runs, the auth-gate inversion is applied, and the hash-binding check is mechanical. Whether a specific finding lands Critical or Low is then a separate severity-tier judgment based on per-target TVL and exploit prerequisites.

## [1.16.0] - 2026-05-28

**Origin**: SquidRouter hack (2026-05, ~$3.07M DAI extracted via `SquidRouterModule.executeSameChainActions()` impersonating authorized delegates on victim Safes). The bug class is a privileged execution wrapper where (a) the auth gate on the outer bundler path did not match the inner per-Safe authorization assumption, and (b) the inner swap path validation accepted caller-supplied router + attacker-deployed pool + `amountOutMinimum=1`. Permissionless attack — no keys compromised. The existing access-control + periphery + signature-verification agents would have caught individual sub-failures, but there was no dedicated detector or methodology surfacing the combined "Safe Module / delegate-executor / arbitrary-path" attack surface as a single Critical-ceiling category.

### Added

- **`methodology/M29-safe-module-delegate-executor.md`** (~250 lines) — full audit methodology for Safe Module + delegate-executor + arbitrary-path patterns. Six STEPs: (1) mechanical enumeration of every `external/public` function that can result in `safe.call/delegatecall` or `swapRouter(target).exactInput(...)` with caller-supplied target; (2) auth-gate inversion test (hash binding, nonce scope, EIP-1271 callee, outer-wrapper auth, cross-tier replay); (3) path-validation test (target allowlist, selector allowlist, pool key validation, slippage bound, decimal verification); (4) cross-class compose (auth × path → severity tier); (5) bundler-specific outer-auth + order-to-order sequencing; (6) on-chain `eth_simulateCallV1` confirmation with state overrides. Origin case study: SquidRouter post-mortem with the specific three-check failure pattern. Historical comparables: Wintermute V1 (2022), Multichain (2023).

- **`scripts/build_recon_maps.sh` extension** — new `(l) delegate-executor-map` block for EVM language. Emits `delegate-executor-map.md` under `$OUT` with sections A (Safe Module hits via `execTransactionFromModule` + selector `0x468721a7`), B (delegate-executor hits — `executeOnBehalf` / `executeMetaTransaction` / `executeBundle` / `swapOnBehalf` / `executeOnSafe` / `executeSameChain` / `delegateBundler` family), C (arbitrary-path call sites — `target.call/delegatecall`, `ISwapRouter(addr).exactInput`, `IPoolManager(addr).swap`, `IUniversalRouter(addr).execute`, `address target, bytes data` signature patterns), D (red-flag combos: `amountOutMinimum/minAmountOut/minOut = 0|1`, `sqrtPriceLimitX96 = 0`). Machine-readable flag summary: `SAFE_MODULE_OR_DELEGATE_EXECUTOR=true/false` and `ARBITRARY_PATH_EXECUTION=true/false`. EVM-only — Solana/Stellar/Move/CPP emit a `_M-29 detector is EVM-specific_` placeholder.

### Changed

- **`agents/hacking-agents/access-control-agent.md`** — new "Safe Module / Delegate-Executor / Arbitrary-Path" attack-plan section. When `SAFE_MODULE_OR_DELEGATE_EXECUTOR=true` or `ARBITRARY_PATH_EXECUTION=true` flags fire from `delegate-executor-map.md`, the agent MUST read M-29 and apply STEPS 1-5 in full. Findings in the map's sections A or B with auth-gate AND path-validation both broken are **Critical-ceiling** under the strict "no admin compromise / direct theft" filter. Use `eth_simulateCallV1` with state overrides to confirm on-chain (analog to the Solana `simulateTransaction` workflow from Vault Unstake Pool audit).

- **`agents/hacking-agents/periphery-agent.md`** — new M-29 section covering path-validation tests (target allowlist, selector/path allowlist, slippage bound, decimal verification) for every external-call site in section C of the recon map. Cross-class compose: when both auth and path fail, severity is Critical-ceiling.

- **`SKILL.md`** — `delegate-executor-map.md` added to the recon artifact list with consumer rules.

- **`methodology/INDEX.md`** — M-29 entry added with full purpose + trigger + STEPs summary. The "Safe Module / Delegate-Executor" category becomes the second EVM-specific methodology (after M-23 stays general). M-28 slot reserved for the deferred EA Finance "Solvency-Failure Severity Framework" proposal (`improve/proposals/2026-05-27-ea-finance-solvency-postmortem.md`).

### Verified

- Synthetic Squid-shape contract (66-byte test file with `executeSameChainActions(bytes data, address target)`, `swapOnBehalf(address router)`, and an inline `ISafe(safe).execTransactionFromModule(...)` call) triggers all three detector categories (A, B, C) and both machine-readable flags. Recon script smoke-test passed end-to-end.

### Filter alignment

M-29 maps directly to the user's strict filter ("Critical / direct theft / no admin compromise / high likelihood"). SquidRouter, Wintermute V1, and Multichain all match this profile — permissionless attacks on protocol code, no key compromise, single-tx extraction. The new detector ensures these patterns are surfaced at recon time with Critical-ceiling treatment, not buried implicitly in the general access-control sweep.

## [1.14.0] - 2026-05-19

**Origin**: Plamen v2.0.0 introduced an L1 infrastructure audit mode (`/plamen l1`) for Go/Rust blockchain node-client auditing — consensus engines, p2p networking, mempool, RPC, validator lifecycle. dewaxguard v1.14.0 ports the L1 mode as an additive layer on top of the v1.13.x driver: opt in via `--l1` and the driver swaps in L1-specific phases and agents.

### Added

- **`platform-quirks/go.md`** (~700 lines) — Go-language quirks file modeled on `platform-quirks/cpp.md`. Covers 12 critical Go semantics: map iteration order non-determinism (consensus-critical), slice aliasing (silent data corruption), `time.Now()` and wall-clock reads in consensus (forks), goroutine leaks and context cancellation, `defer` ordering and error path cleanup, silent integer overflow (Go does NOT panic), `nil` interface vs typed `nil` equality trap, concurrent map access panics, JSON/RLP/Borsh unmarshaling type confusion, IBC/bridge/cross-chain message handling, p2p / networking surface (12 attack vectors with mitigations), consensus state machine determinism. Includes baseline known-issue catalog (Geth, Reth, Cosmos SDK, CometBFT advisories) and quick-grep patterns for recon.

- **`agents/l1/depth-consensus-invariant.md`** — new L1 depth agent. Targets cross-validator divergence, slashing condition errors (SOUND/COMPLETE/PRIVATE/EFFICIENT 4-question matrix), fork-choice errors, finality bugs, validator set transition errors, IBC/bridge message handling, resource accounting drift, state pruning races. Six-step methodology: cross-validator divergence trace, differential against reference implementation, spec conformance, fuzz exploration, slashing-condition matrix, validator lifecycle race. Emits findings with IDs [DCI-N] and L1 evidence tags. Replaces depth-state-trace in L1 mode.

- **`agents/l1/depth-network-surface.md`** — new L1 depth agent. Targets eclipse, sybil, mempool DoS, peer-scoring poisoning, gossip amplification, slow loris, per-method RPC DoS, bandwidth amplification, block/packet withholding, censorship via peer-score manipulation, authentication bypass, peer identity spoofing. Six-step methodology: resource budget audit, per-attack-vector enumeration, peer-scoring symmetry check, authentication ladder, differential against reference implementation, fuzz the wire format. Emits findings with IDs [DNS-N]. Replaces depth-external in L1 mode.

- **`rules/l1-severity-matrix.md`** — L1-specific severity matrix (Immunefi v2.3-aligned). Distinct from smart-contract matrix because L1 impacts have different primary axes (chain halt, validator slashing, consensus stall, network partition). Includes 12-row impact table x 3-column likelihood, realism downgrade modifiers, evidence-tag severity floors (`[DIFF-PASS]` / `[NON-DET-PASS]` → High minimum), per-platform interpretation rules (Immunefi mapping table, Code4rena L1 contests, Sherlock L1 thresholds).

- **`scripts/bake_l1.sh`** — Phase 0.5 Bake step. Detects best available tool (ast-grep → opengrep → ripgrep → POSIX grep) and runs language-specific patterns to extract 8 bake artifacts under `{SCRATCHPAD}/bake/`: non_deterministic_calls.md, consensus_state_machine.md, slashing_conditions.md, validator_lifecycle.md, p2p_message_handlers.md, rpc_methods.md, mempool_admission.md, peer_scoring_rules.md. Each artifact maps to a specific consumer (depth-consensus-invariant or depth-network-surface). PCRE auto-detection with POSIX fallback for portability.

- **`prompts/phases/05_bake.md`** — phase template for the L1 Bake subprocess. Invokes `scripts/bake_l1.sh`, supplements with targeted greps when the POSIX fallback was used, optionally fetches baseline known-issue catalogs via WebFetch, writes `bake_summary.md` for handoff to depth agents.

- **`prompts/phases/45_depth_l1.md`** — L1 variant of the depth phase. Routes findings to L1 agents via bug_class root tokens specific to consensus/network domains. Spawns depth-consensus-invariant, depth-network-surface, depth-lowlevel (Go-aware), depth-runtime; plus depth-token-flow / depth-edge-case when the chain has CosmWasm/EVM modules. Each agent receives a per-domain bake artifact subset.

### Changed

- **`scripts/dewaxguard_driver.py`** — `Phase` dataclass extended with `l1_only`, `sc_only`, `l1_template` fields. `select_phases` filters by `l1` flag. `invoke_phase` swaps to `l1_template` when `--l1` is set. New `--l1` CLI flag. Bake phase entry added (positioned between recon and breadth, `l1_only=True`). Depth phase entry now declares `l1_template="45_depth_l1.md"`. `L1_MODE` placeholder added to template-instantiation context. Driver header logs `[L1]` tag when L1 mode is active.

- **`scripts/severity_router.py`** — new `--l1` flag adds L1 evidence-floor logic per `rules/l1-severity-matrix.md`. Tags `[DIFF-PASS]` / `[NON-DET-PASS]` raise severity floor to High; `[FUZZ-PASS]` raises to Medium. Floor is applied AFTER downgrades (per the matrix rule "If the matrix says Low but the evidence is [DIFF-PASS], the FINAL severity is High"). Pre-existing smart-contract matrix unchanged when `--l1` is absent.

- **`SKILL.md`** — added L1 mode callout near the Usage line; documents target chains (Geth / Reth / Erigon / Lighthouse / Prysm / Cosmos SDK / CometBFT / Bitcoin Core / rippled), the swapped agents, the severity-floor behavior. Added `Go` to the supported-languages line.

### Validation

- **Phase selection per mode + L1**:
  - Light + SC (8 phases): preflight → recon → breadth → inventory → niche → depth → chain → report
  - Core + SC (10): + verify + validator
  - Thorough + SC (11): + nemesis
  - Light + L1 (9): + bake
  - Core + L1 (11): + bake + verify + validator
  - Thorough + L1 (12): + bake + nemesis + verify + validator
- **Template swap**: L1 mode loads `45_depth_l1.md` for depth phase; SC mode loads `45_depth.md`. Verified by transcript inspection.
- **L1 evidence floor**: synthetic finding with `impact_level=Low likelihood=Medium` + evidence `[NON-DET-PASS]` routes to **High** under `--l1` (matrix says Low; floor wins). Same finding under SC mode routes to **Low**.
- **Bake script**: 8 artifacts emitted; POSIX-grep fallback verified working after PCRE-translation fix (map-range regex previously missed because POSIX ERE doesn't support `\s`/`\w`/`\b`).
- **Full pipeline traversal** (thorough + L1): all 12 phases run cleanly in dry-run, manifest written, prompt_bytes per phase recorded.

### Not in this release (deferred)

- L1 evidence-floor wiring in the inventory phase template (`40_inventory.md`) — currently the inventory invokes severity_router without `--l1`, so the floor only applies when severity_router is invoked manually. Add `L1_MODE` placeholder check to 40_inventory.md in v1.14.1.
- platform-quirks/rust.md for L1 Rust node clients (Reth, Lighthouse Rust, Solana validator). v1.14.x.
- Phase 0.5 Bake patterns for Rust — currently only Go is fully supported. v1.14.x.
- ast-grep / opengrep integration validated against real codebases (only POSIX grep fallback tested in this release).
- WebFetch-based known-issue catalog freshness check (currently relies on agent judgment).

### Rollout

`--l1` is a NEW flag on the driver, independent of `--driver` flag. Both opt-in. Smart-contract auditing remains unchanged in default invocation. The v1.14 milestone closes out the Plamen v2.0.0 port — every headline feature from that release now has a dewaxguard equivalent.

---

## [1.13.2] - 2026-05-19

**Origin**: v1.13.0 and v1.13.1 left 5 phase templates (preflight, recon, breadth, verify, report) as thin MVP delegations to SKILL.md — each ~2-3KB and dependent on the fresh `claude -p` subprocess chasing cross-references. v1.13.2 expands all 5 to self-contained ~10-18KB templates with full inline methodology. Total prompt budget across all 11 phases is now ~106KB.

### Changed

- **`prompts/phases/00_preflight.md`** — expanded from 87 to 175 lines. Inlines the project-local context table (CLAUDE.md, DEEP_DIVE_PLAN, MANIFEST, CONTEST_FAQ, KNOWN_ISSUES_INDEX). Inlines the V12-style AI-auditor probe (M-25) with the exact `grep_v12.sh --count` and `--invalid-only` invocations. Inlines the cross-audit context (LEARNED_INDEX, methodology/INDEX). Adds language detection probe commands with the file-count breakdown. Inlines the per-language platform-quirks routing table with mandatory-vs-optional markers. Self-check requires preflight.md ≥ 1500 bytes with all sections present.

- **`prompts/phases/10_recon.md`** — expanded from 52 to 250+ lines. Full Phase 1.0 preprocessor invocation inlined (build_recon_maps.sh + squeezer_rust.py) with expected artifacts table mapping each output to its downstream consumer. Phase 1.1 fully spelled-out: 4 sub-agents (1A RAG probe, 1B Docs+Fork+External, 2 Build+Static, 3 Attack-Surface+Templates) each with complete Task() invocation block including model selection, inputs to read, methodology, and per-agent SCOPE clause. Includes niche-agent flag detection at step 6 of Agent 3 (MISSING_EVENT, HAS_SIGNATURES, HAS_DOCS, HAS_MULTI_CONTRACT, HAS_UPGRADEABLE_PROXY). Self-check verifies all required artifacts exist with content-shape checks.

- **`prompts/phases/30_breadth.md`** — expanded from 60 to 200+ lines. Removes the table-only agent list; replaces with a full per-agent dispatcher template that fills in agent_name, agent_file, output_file, preprocessor_map, read_budget, grep_budget per mode. Documents the 8 agents (or 4 in light) with mode-specific model selection (opus for math/access/invariant in core; all opus in thorough; all sonnet in light). Inlines injectable-skill routing table (VAULT_ACCOUNTING → invariant or economic-security; LENDING_PROTOCOL_SECURITY → economic + math + invariant; etc.). Adds a breadth_dispatch.md log requirement so coverage gaps are debuggable.

- **`prompts/phases/50_verify.md`** — expanded from 76 to 290+ lines. Inlines verification queue construction with mode-dependent scope (light=skip, core=Medium+ only, thorough=ALL severities + fuzz variants). Inlines per-language PoC strategy: EVM Foundry with exact foundry.toml + fork RPC table, Solana with LiteSVM and solana-test-validator commands, Stellar/Aptos/Sui Move test commands, C/C++ rippled unit test invocation. Inlines Foundry cheatcode plain-English comment dictionary. Inlines test structure templates for EVM and Solana. Variant exploration table (timing/amount/ordering/initial-state/wrapper) with the rule that 2+ variant failures justify [FORK-FAIL]. Per-finding markdown output format with status header convention ([VERIFIED]/[UNVERIFIED]/[CONTESTED]/[FALSE_POSITIVE]).

- **`prompts/phases/60_report.md`** — expanded from 60 to 320+ lines. Strategy selection table (light=single-pass, core=single-pass OR 4-agent pipeline based on count, thorough=4-agent always). Inlines all 4 agent prompts (Index haiku, Critical+High writer opus, Medium writer sonnet, Low+Info writer sonnet, Assembler haiku/sonnet by count). Completeness assertion inline after Index agent (`hypothesis_count == report_ids + excluded_count + consolidated_absorbed`). Inlines the canonical report structure with all sections. Inlines per-finding markdown format. Inlines platform impact quantification rules per platform (Sherlock dollar threshold, Code4rena conditions/likelihood, Cantina matrix cells, Immunefi categories). 6 quality gates (finding count consistency, no internal IDs in body, valid cross-references, no duplicates, plain-English self-check, sentence length).

### Validation

- Full 11-phase traversal (thorough mode) completes cleanly in dry-run.
- Per-phase prompt sizes after expansion: preflight 8.8KB, recon 18.0KB, breadth 10.7KB, inventory 4.6KB, niche 6.2KB, depth 6.7KB, nemesis 5.8KB, chain 7.8KB, verify 13.8KB, validator 7.3KB, report 15.9KB. Total ~106KB.
- Mode filtering still correct: light skips verify+validator+nemesis (8 phases), core skips nemesis (10), thorough runs all 11.
- Checkpoint resume still works.

### Not in this release (still deferred)

- Coverage gate end-to-end validation against a live `claude -p` stream-json transcript.
- Codex backend validation (the dispatcher is wired but no real run yet).
- Adaptive depth loop iterations 2-3 with 4-axis confidence scoring (the depth phase runs iteration 1 only; iterations 2+ require the scoring pipeline from phase4-confidence-scoring.md).
- Dedicated RAG validation sweep as its own phase (currently embedded inline in chain phase).
- M-21 cross-agent contradiction protocol as a structural enforcement (currently it's prose-only methodology).

### Rollout

v1.13.2 completes the v1.13 phase-driver hardening work. The driver now has 11 self-contained phases covering preflight through report. `--driver` remains opt-in; legacy SKILL.md prompt-only flow is still the default. The next milestone is v1.14 L1 mode (Go/Rust node-client audits) which adds new surface on top of the now-stable driver.

---

## [1.13.1] - 2026-05-19

**Origin**: Continuation of v1.13.0. The MVP driver covered 6 phases (preflight, recon, breadth, inventory, verify, report) — enough to validate the architecture but missing the depth, chain, Nemesis, validator, and niche-agent phases that make dewaxguard's pipeline actually useful. v1.13.1 ports those 5 phases into the driver with self-contained per-phase templates (100-300 lines each).

### Added

- **`prompts/phases/42_niche.md`** — flag-triggered niche agents phase. Reads `template_recommendations.md` (from recon) to discover which niche agents to spawn: EVENT_COMPLETENESS, SIGNATURE_VERIFICATION_AUDIT, SPEC_COMPLIANCE_AUDIT, SEMANTIC_CONSISTENCY_AUDIT. Each niche agent runs in parallel via Task tool with a self-contained inline prompt covering inputs / method / output ID prefix. When no flags fire, the phase exits cleanly with an empty `niche_summary.md` (still meets content gate).

- **`prompts/phases/45_depth.md`** — 6 depth agents (Plamen-style 4 + dewaxguard's 2 NEW: depth-lowlevel + depth-runtime). Routes canonical findings to agents by bug_class root tokens (token/balance → depth-token-flow, auth/role → depth-state-trace, etc.). Each agent reads its definition (`agents/depth-*.md` or `methodology/depth-*.md`), processes ≤ 5 findings (Rule AD-3 from confidence scoring), and emits `depth_<short>_findings.md` with the agent-specific depth evidence tags ([DTF-N], [DST-N], [DEC-N], [DEX-N], [DLL-N], [DRT-N]) plus a Chain Summary table for Phase 4c. Iteration 1 only; iterations 2-3 (adaptive depth loop) are v1.13.2+ work.

- **`prompts/phases/46_nemesis.md`** — iterative Feynman ↔ State-Inconsistency cross-feed (mode_min=thorough). Pass 1 Feynman → Pass 2 State → Pass 3 Feynman → ... up to 6 passes with convergence-based exit (0 new findings → exit). Each pass spawned as separate Task agent with the pass-N number injected; the prior pass's output is the next pass's enrichment input. Final `nemesis_summary.md` aggregates novel findings for chain analysis.

- **`prompts/phases/47_chain.md`** — split 2-agent chain analysis from `rules/chain-analysis-prompt.md`. Pre-step: extract compact Chain Summary digests from depth output to avoid 5000+ line input. Agent 1: enabler enumeration (5-actor table per dangerous state, Rule R12) + grouping (max 5 findings per hypothesis, anti-absorption test). Agent 2: chain matching (PARTIAL/REFUTED → CONFIRMED postcondition lookup) + composition coverage map (cross-class pairs HIGH PRIORITY) + optional RAG validation. Iterative pass (max 1 additional iteration) when unexplored Medium+ cross-class pairs remain.

- **`prompts/phases/55_validator.md`** — Phase 5d bug validator. 7 gates per finding: refutation, docs-intent (HARD), reachability, trigger, severity decision tree a/b/c, realism filter, auth-critical-files when applicable. Emits per-platform `predicted_verdict` + 0-100 score for Code4rena / Sherlock / Cantina / Immunefi / HackenProof. Score deductions: -30 for failed gates 1/1a/2/3, -20 for realism filter rejection, -15 for severity inflation > 1 tier vs decision tree, -5 per plain-English violation, -10 for SKELETON_ONLY auth_check, +10 for RAG match. Writes `validation_results.json` consumed by the report phase.

### Changed

- **`scripts/dewaxguard_driver.py`** — phase registry expanded from 6 to 11 phases. New entries: `niche` (after inventory, always runs but can no-op), `depth` (after niche, 90min timeout for 6 parallel agents), `nemesis` (between depth and chain, mode_min=thorough, 2hr timeout), `chain` (after nemesis when present, else after depth, 40min for 2 sequential agents), `validator` (between verify and report, mode_min=core, 30min). Mode filtering verified across light/core/thorough.

### Validation

- **Phase registry per mode**:
  - Light (8 phases): preflight → recon → breadth → inventory → niche → depth → chain → report
  - Core (10): + verify + validator
  - Thorough (11): + nemesis
- All transitions still pass dry-run + skip-gates traversal. Checkpoints still resume correctly. Phase filter still honored.

### Deferred to v1.13.2+

- Coverage gate end-to-end validation against a real claude -p stream-json transcript.
- Codex backend validation.
- Expand early/late phase templates (00_preflight.md, 10_recon.md, 30_breadth.md, 50_verify.md, 60_report.md) from MVP delegations to full inline methodology — currently they reference SKILL.md sections, which means the fresh subprocess has to chase cross-references. v1.13.2 will inline them like the new 5 phases.
- Adaptive depth loop (iterations 2-3) per phase4-confidence-scoring.md.
- 4-axis confidence scoring after iteration 1.
- RAG validation sweep as a dedicated phase (currently embedded inline in chain phase).

---

## [1.13.0] - 2026-05-19

**Origin**: Continuation of the Plamen v2.0.0 port started in v1.12. Plamen v2 deprecated its LLM orchestrator with a deterministic Python driver that spawns `claude -p` subprocesses per phase — each phase runs in a fresh context window, gates check the output before advancing, and per-phase checkpoints make the pipeline crash-resumable. v1.13 ports this driver architecture to dewaxguard as an opt-in `--driver` invocation. The legacy prompt-only flow (`/dewaxguard`) remains the default until at least v1.15, so existing workflows are unaffected.

### Added

- **`scripts/dewaxguard_driver.py`** — deterministic phase orchestrator. Each phase is an isolated `claude -p` (or `codex exec` via `--backend codex`) subprocess invoked from Python. Per-phase timeout, retry budget with targeted retry hints, checkpoint sentinels under `scratchpad/checkpoints/`, manifest under `scratchpad/driver/manifest.json`, transcripts saved per retry. Phase registry: preflight → recon → breadth → inventory → verify → report. Mode filter (`mode_min` field on each Phase) excludes `verify` in `light` mode. CLI flags: `--mode {light|core|thorough}`, `--src`, `--audit-id`, `--backend {claude|codex}`, `--phase` (run only named phase, repeatable), `--resume` (skip phases with existing checkpoints), `--retry-budget`, `--dry-run`, `--skip-gates`.

- **`prompts/phases/00_preflight.md`** — phase template for the MANDATORY Session-Start Preflight, instantiated by the driver with project-state placeholders ({{AUDIT_ID}}, {{SRC_PATH}}, {{SCRATCHPAD}}, {{SKILL_ROOT}}, etc.). Self-contained — the fresh `claude -p` subprocess has no prior context, treats the prompt as its entire task.

- **`prompts/phases/10_recon.md`** — recon phase template. Delegates to SKILL.md PHASE 1.0 + 1.1 methodology. Lists required outputs the content gate checks for.

- **`prompts/phases/30_breadth.md`** — breadth phase template. Spawns 4 (light) or 8 (core/thorough) hacking agents in parallel. Mandates the pipe-delimited FINDING/LEAD output format with optional schema-aligned fields per v1.12.

- **`prompts/phases/40_inventory.md`** — inventory phase template. Invokes the three v1.12 mechanical scripts (`parse_findings.py` → `dedup.py` → `severity_router.py`) and handles the optional LLM tie-break for ambiguous dedup pairs. Phase 4a is now mostly mechanical.

- **`prompts/phases/50_verify.md`** — verification phase template. Per-finding PoC generation + execution per `rules/fork-poc-execution.md`. Records evidence tags (POC-PASS / POC-FAIL / CODE-TRACE). Mandates plain-English PoC comments per v1.11.

- **`prompts/phases/60_report.md`** — report assembly template. Either spawns the 4-agent tier writer pipeline (thorough mode) or produces the report in a single pass (light/core). Strict on no-internal-IDs-in-body, plain-English style, complete severity sections.

- **`scripts/gates/content_check.py`** — content gate. Verifies each phase's required outputs (a) exist, (b) are non-empty above MIN_BYTES, (c) are not stub placeholders ("I will analyse", "TBD", etc.), (d) match the content shape expected for their type — `findings_*.json` parsed as valid JSON with `findings` array; `analysis_*.md` / `verify_*.md` contain ≥ 1 `FINDING |` or `## Finding [` header; `AUDIT_REPORT.md` contains ≥ 3 of the expected sections (executive summary, summary, critical, high, medium, low). Generates structured FAIL messages the driver injects into retry prompts.

- **`scripts/gates/coverage_check.py`** — coverage gate. Parses the `claude -p` stream-json transcripts saved under `scratchpad/driver/` to extract every `Read` (and `Grep`/`Glob`) tool invocation. Compares against the enumerated in-scope source files (auto-discovered under `--src` filtered by `.sol`/`.rs`/`.move`/`.cpp`/`.cc`/`.hpp`/`.h`/`.go` extensions, excluding common non-audit paths). Targets the structural enforcement of "every in-scope file must be read by some agent" — failures emit specific file paths the next retry must read. Falls open safely when transcripts are not yet available.

### Changed

- **`SKILL.md`** — added a "Driver mode (v1.13+, opt-in)" callout near the Usage line documenting the `python3 scripts/dewaxguard_driver.py --mode core ...` invocation. The legacy `/dewaxguard` prompt-only flow remains the default; users opt in to the driver explicitly. Behavior of the legacy flow is unchanged.

### Validation Summary

- **Full pipeline traversal**: dry-run + skip-gates → all 6 phases (preflight, recon, breadth, inventory, verify, report) invoked in registry order, manifest written with prompt_bytes per phase, checkpoints written.
- **Crash resume**: second invocation with `--resume` → all 6 phases SKIPped because checkpoints exist.
- **Phase filter**: `--phase inventory` → only inventory ran, others not invoked.
- **Mode filter**: `--mode light` correctly excludes `verify` (mode_min=core); 5 phases ran instead of 6.
- **Retry behavior**: dry-run WITHOUT skip-gates → content gate correctly detects missing required outputs, retries with injected hint message, aborts after retry_budget exhausted.
- **Manifest content**: prompt body NOT embedded in manifest (only `prompt_bytes` + transcript path), keeping the manifest readable for crash diagnostics.

### Not in this release (deferred)

- Coverage gate parsing has not been validated against a real `claude -p` stream-json transcript (only against synthetic non-existent transcripts that correctly FAIL). The regex assumes `{"type":"tool_use","name":"Read","input":{"file_path":"..."}}` shape per Anthropic's documented stream-json format. v1.13.1 will validate end-to-end against a live run.
- The `codex` backend is wired in but not validated. Codex CLI users should expect rough edges until v1.13.2.
- The per-phase templates (recon, breadth, verify, report) are intentionally concise — they delegate to existing SKILL.md sections for detailed methodology. Full per-phase prompt expansion is v1.13.1+ work.
- Phase 4b (depth), Phase 4b.1 (Nemesis), Phase 4c (chain analysis), niche agents, and Phase 5d (bug validator) are NOT yet driver phases. The current driver MVP runs preflight → recon → breadth → inventory → verify → report. Depth + chain + validator integration is v1.13.2 work.

### Rollout

`--driver` is opt-in for v1.13. The legacy SKILL.md prompt-only flow remains the default invocation when users type `/dewaxguard`. After v1.13.x stabilizes and the deferred items ship, v1.14 will introduce L1 mode (`/dewaxguard l1`) and v1.15 may flip the driver to the default with `--legacy` as the escape hatch.

---

## [1.12.0] - 2026-05-19

**Origin**: Plamen v2.0.0 (2026-05-13) deprecated its LLM orchestrator after observing context-saturation drift on multi-agent audits — late-pipeline phases silently skipped mandatory dedup work, and the same finding shipped 3-5x in the report under different titles. dewaxguard v1.12 ports the mechanical-Python pattern at the inventory layer: three deterministic scripts replace the LLM-led inventory phase. The phase driver, content/coverage gates, and L1 mode follow in v1.13/v1.14.

### Added

- **`scripts/findings_table.schema.json`** — v1.0 JSON Schema for findings tables passed between phases. Superset of the existing `FINDING | ... | group_key:` pipe-delimited prose. Adds optional fields for `severity`, `impact_level`, `likelihood`, `realism_filter`, `location` (file+line range), `evidence_tags`, `verdict`, `preconditions`, `postconditions`, `chain_id`, `platform_status`, and per-finding agent-source paths. Includes L1-mode evidence tags (`DIFF-PASS`, `CONFORMANCE-PASS`, `NON-DET-PASS`, `FUZZ-PASS`) ahead of v1.14.

- **`scripts/parse_findings.py`** — parses agent scratchpad files into the v1.0 schema. Handles two formats: (a) the `FINDING | contract: X | function: Y | bug_class: Z | group_key: X | Y | Z` pipe blocks from `agents/hacking-agents/`, (b) the `## Finding [H-01]: Title [VERIFIED]` + `**Severity**:`/`**Location**:` markdown blocks from `rules/finding-output-format.md`. Both formats can coexist in the same file. Optional fields (`severity:`, `impact:`, `likelihood:`, `realism_filter:`, `location:`, `evidence:`) are parsed when present.

- **`scripts/dedup.py`** — mechanical three-stage clustering with Jaro-Winkler character similarity and Jaccard token overlap, all implemented in pure Python (no external deps). Stage A: exact `group_key` match (score 1.0, always merge). Stage A2: same `contract`+`function` with bug_class jaccard ≥ 0.3 OR title similarity ≥ 0.55 (merge), or partial signals (ambiguous). Stage B: same file + line proximity (±5) + bug_class overlap. Stage C: cross-file bug_class token-bucket pre-filter + full pair scoring. Each pair evaluated at most once. Ambiguous pairs (score 0.70-0.85) surface in `dedup_ambiguous.json` for optional LLM tie-break — the vast majority of clusters resolve mechanically. Canonical picker prefers highest severity → FINDING over LEAD → most evidence tags. Cluster absorbs `extra_locations`, agent paths, evidence tags, and the most-restrictive realism filter from all members. End-to-end run < 100ms on 50-finding input.

- **`scripts/severity_router.py`** — mechanical Impact×Likelihood matrix application from `rules/report-template.md`. Implements: (a) base matrix lookup when `severity` is unset but `impact_level`/`likelihood` are; (b) realism-filter downgrades (`admin-trust` -1 tier, `design-choice`/`unreachable-precondition` cap at Informational); (c) scope modifiers (`VIEW_ONLY` cap at Medium, `ON_CHAIN_ONLY` without off-chain impact -1 tier); (d) `--proven-only` flag that caps any finding without a proof tag (`POC-PASS`, `MEDUSA-PASS`, `PROD-*`, `FUZZ-PASS`) at Low. Preserves `severity_pre_modifier` for the report to show original tier + adjustment reason. Propagates canonical severity to duplicate rows automatically.

- **`methodology/M26-mechanical-inventory-dedup.md`** — new methodology entry documenting the v1.12 pipeline. When to apply (between Phase 3 and Phase 4b), the three-stage clustering rules, output artifacts (`findings_routed.json`, `dedup_clusters.json`, `dedup_ambiguous.json`, `severity_changes.json`), fallback to LLM dedup when scripts are unavailable, integration with M-10 (3-layer dedup) / M-13 (Kuprum) / M-25 (V12 external). Distinct from M-25: M-25 dedupes against external published indices via `scripts/grep_v12.sh`; M-26 dedupes internal cross-agent findings via `scripts/dedup.py`.

### Changed

- **`SKILL.md`** — added new "PHASE 4a: INVENTORY + MECHANICAL DEDUP (v1.12+)" section between Phase 3 (Breadth) and Phase 4b (Depth). Documents the three-script invocation sequence (`parse_findings.py` → `dedup.py` → `severity_router.py`), the optional LLM tie-break for ambiguous pairs, and the rationale (replaces non-deterministic LLM dedup with reproducible Python clustering that's ~100× cheaper). Lists downstream artifacts consumed by Phase 4b.

- **`agents/hacking-agents/shared-rules.md`** — extended the FINDING/LEAD output format block to declare the optional schema-aligned fields agents MAY emit when known (`severity:`, `impact:`, `likelihood:`, `realism_filter:`, `location:`, `evidence:`). Existing pipe-delimited format is unchanged — agents that don't emit these fields still work. Added a paragraph explaining the mechanical dedup pipeline and how schema-aligned fields improve precision.

- **`methodology/INDEX.md`** — registered M-26 with the validation note and trigger criteria.

### Validation Summary

- **Schema validation**: parser output validates against `findings_table.schema.json v1.0` (jsonschema library).
- **Dedup correctness**: tested on synthetic 3-agent overlap of the same bug with different bug_class spellings (`missing-auth` / `missing-access-check` / `auth-missing`) → all 3 merged into 1 canonical (chose EXECUT-1 over ACCESS-1 because it had more evidence tags `[CODE, TRACE]` vs `[CODE]`). False-positive guard: same function with two legitimately different bugs (`missing-auth` + `rounding-loss` on `liquidate`) → correctly kept separate, flagged only as ambiguous for human glance.
- **Severity matrix correctness**: 5-case test covers Critical-from-High/High, admin-trust downgrade preserving `pre_modifier`, VIEW_ONLY cap, design-choice cap to Informational, `--proven-only` cap to Low for findings with only `[CODE]` evidence.
- **End-to-end smoke**: 4 breadth agents emitting 5 findings (1 cross-agent duplicate, 4 distinct) → 4 canonicals routed to Critical / High / Low / Medium with correct realism-filter adjustments.
- **Format coexistence**: pipe-format and markdown-format findings in the same file parse together without conflict.
- **Performance**: end-to-end pipeline (parse + dedup + severity) runs in < 100ms on 50-finding input. LLM inventory agent in prior versions took ~30s for the same volume.

### Rollout

The v1.12 scripts are opt-in for v1.12. v1.13 introduces a `--driver` flag that makes the deterministic phase orchestrator the default invocation path. The legacy LLM inventory flow stays available behind `--legacy` indefinitely; users without Python on their machine fall back to it automatically.

---

## [1.11.0] - 2026-05-09

**Origin**: User feedback that DewaxGuard reports and PoCs were hard to read for non-auditor stakeholders (project leads, junior devs, bounty triagers). Findings used auditor jargon (`reentrancy`, `TOCTOU`, `monotonicity`, `composability`) that forced the reader to translate before deciding whether to merge a fix. PoC files used opaque comments (`// Impersonate caller`, `// Set storage slot`) that did not explain the attack story. The fix is a single style rule, referenced from every place a finding or PoC is written.

### Added

- **`rules/plain-english-style.md`** — new style rule defining the target reader (smart-contract-savvy, not auditor-fluent), the five sentence rules (one idea per sentence ≤ 25 words, subject-before-verb, name the actor, show harm in user terms, no Latin/no nested parentheticals), a banned-jargon table with plain-language replacements (≈ 30 entries — reentrancy, invariant, monotonic, fungible, atomicity, TOCTOU, MEV, slippage, etc.), the four-sentence Description shape (what is wrong → why it matters → who triggers it → what the user sees), the three-part Recommendation shape (fix sentence → diff → result sentence), the cheatcode-comment dictionary for Foundry/Anchor/Move, and a side-by-side bad-vs-good example. Hard rule: validator deducts 5 points per violation; failed findings get one rewrite pass before submission.

### Changed

- **`rules/report-template.md`** — added a top-of-file plain-English requirement, replaced the bare finding-format block with a worked H-01 example using the four-sentence shape and a real diff, rewrote the Platform Impact bullets in plain English (Sherlock/C4/Cantina/Immunefi), added a 5-item self-check the writer runs before saving the report.
- **`rules/finding-output-format.md`** — added the plain-English requirement as the 5th validator hard rule, rewrote the example finding (Solana `set_admin` missing-auth) using the four-sentence Description shape and a plain-English Recommendation diff.
- **`rules/fork-poc-execution.md`** — replaced jargon comments on the Foundry cheatcode block (`Impersonate caller` → `next call comes from the attacker`, `Set storage slot` → `force the contract's storage to a state we want to test`, etc.), added a "Use real names, round numbers, plain comments" section between Concrete Assertions and Variant Testing, rewrote the Output Format example to include an "Attack story" paragraph in plain English, added a 5-item self-check before saving the PoC.
- **`references/report-formatting.md`** — added the plain-English requirement at the top, rewrote the per-finding Description template ("vulnerable code pattern and why it is exploitable" → "name the function, say what is missing or wrong, say who can abuse it, and say what the user loses"), added a 4-item self-check for each Description.
- **`SKILL.md`** Phase 5c — added a one-paragraph plain-English requirement directing every PoC-writer agent to load `rules/plain-english-style.md`.
- **`SKILL.md`** Phase 6 — added the plain-English requirement to the report writers' mandatory input list (alongside `report-template.md` and `report-formatting.md`); each finding line in "For each finding" now states its plain-English shape (four-sentence Description, dollar/percent Impact, fix-sentence + diff + result-sentence Recommendation).

### Validation Summary

- **Banned-jargon coverage**: ≈ 30 most common auditor terms have plain replacements; covers reentrancy, invariants, MEV, slippage, oracle staleness, TOCTOU, griefing, monotonicity, fungibility, race conditions, signature replay, idempotency.
- **Description shape coverage**: every report and finding format file now states the four-sentence shape explicitly. Validator deducts 5 points per missing sentence.
- **PoC comment coverage**: Foundry cheatcode dictionary covers `vm.prank`, `vm.startPrank`, `vm.deal`, `vm.store`, `vm.warp`, `vm.roll`, `vm.expectRevert`, `assertEq`, `assertGt`. Solana/Anchor/Move comment dictionary covers `Context<T>` setup, `signer`, `program.methods.*.rpc()`, `assert_eq!`, expected-error patterns, `tx_context::sender`, Move `transfer::public_transfer`.
- **Cross-reference**: 5 files now reference `rules/plain-english-style.md` (report-template, finding-output-format, fork-poc-execution, references/report-formatting, SKILL.md Phase 5c+6). Single source of truth, no duplication.

---

## [1.10.0] - 2026-05-06

**Origin**: K2 Lending Protocol audit continuation (Code4rena Stellar Soroban). During an exploratory deep-dive round, two false-positive findings were investigated, PoC'd, and only THEN discovered to be V12 duplicates (DD-5 "broken `update_atoken` caller forwarding" → V12 #44797; L-09 "TTL-expiry default-on-read" → V12 #44792 with explicit `### Invalid Reason` documenting Soroban v23 archive-restore semantics). Combined wasted time: ~1.5 hours. Triggered the codification of a programmatic dedup workflow specifically for V12-style structured AI-auditor outputs (which differ in shape from M-13's Kuprum-style human-curated catalogs).

### Added

- **`methodology/M25-v12-style-ai-auditor-dedup.md`** — V12-style AI-auditor finding-index pre-grep methodology. When the contest sponsor publishes a V12-style structured AI-auditor output (Zellic V12, similar tools) as the official "known issues" index: at audit start, ingest the platform-knowledge corpus (Invalid-marked entries explain why something LOOKS like a bug but isn't); before every Medium+ PoC, dedup against V12 keywords. Distinct from M-13 (M-13 = unstructured Kuprum-style human-curated catalogs; M-25 = structured AI-auditor outputs with consistent Targets / Severity / Validity / Description / Root Cause / Impact / PoC / Invalid Reason fields). The companion script `scripts/grep_v12.sh` automates Phase 1 step 2.

- **`scripts/grep_v12.sh`** — companion helper for M-25. Four modes: `--count` (per-file finding count, code-fence-aware), keyword OR-mode (default), `--strict` AND-mode (all keywords must match in same finding), `--invalid-only` (surface every entry with explicit Invalid Reason — the platform-knowledge corpus). Validates keyword matches against finding title + body, skips fenced code blocks to avoid false-positive matches on PoC test code. Tested on K2 V12 corpus (3 files, 109 findings, 125k lines) — runs in <1s for typical queries. Exit code 0 on match, 1 on no-match, 2 on bad args.

### Changed

- **`platform-quirks/stellar.md`** — Added top-of-file callout reminding to re-read storage-archival semantics (#1 quirk) before any TTL/expiry hypothesis. Cites the 5 V12 Invalid-marked entries that document the same misconception (#44792, #44793, #44432, #44849, #44858) and provides the one-line grep recipe to surface them. The callout exists because dewaxguard already had this lesson documented but the orchestrator missed reading it before investigating L-09.

- **`methodology/INDEX.md`** — Registered M-25. Added "before submission" workflow step (run M-25 V12 dedup grep if contest cited V12/Zellic) and "audit start when V12 present" step (run `scripts/grep_v12.sh --invalid-only` to ingest platform-knowledge corpus before any breadth/depth work).

- **`SKILL.md`** — Preflight Step 1 now includes `5a. *V12*-output.md / *zellic*.md detection` with mandatory action when present. Self-check before declaring preflight complete now includes V12-output check.

### Validation Summary

- **DD-5 dedup test**: `grep_v12.sh "Wrong actor forwarding"` → returns V12 #44797 in <1s. Would have killed DD-5 candidate before any PoC effort.
- **L-09 dedup test**: `grep_v12.sh --invalid-only | grep -iE "expir|archiv"` → returns 5 entries (#44792, #44793, #44432, #44849, #44858) all citing Soroban v23 archive-restore semantics. Would have killed L-09 candidate before any QA-Bundle write-up.
- **Per-K2-audit savings**: ~1.5h wasted investigation + ~0.5h documentation revert = ~2h saved per audit when V12-style index ships.
- **Permanent platform-knowledge corpus**: 66 Invalid-marked entries available as pre-audit reading material on Soroban quirks (storage archival, public-entry-point reachability, admin-trust patterns, oracle dependency boundaries).

---

## [1.9.0] - 2026-05-05

**Origin**: K2 Lending Protocol audit (Code4rena Stellar Soroban, 2026-04-17 → 2026-05-27, 8 passes / 108 hypotheses). 14 of 14 QA-Bundle entries followed the same consistency-class pattern → highest-yield methodology for Aave V3 forks. Manual-orchestrator fallback in Pass 7 produced 3 false negatives → codified mandatory agent-failure-recovery protocol. Project-local realism filter reclassified ~40% of candidate findings → promoted to first-class rule.

### Added

- **`methodology/M23-consistency-class-sweep.md`** — Defensive-pattern sweep methodology. For Aave V3 forks and similar protocols with ≥3 instances of the same defensive macro, build a convention catalog (canonical helper + intent source + all call sites), grep for outliers, file each as Low/Info. Validated on K2: 14/14 QA-Bundle entries follow this pattern (~89% of all findings); the 1 submitted Medium also fits the shape. Cross-language mappings for EVM/Solana/Soroban/Move/C++. **Highest-yield methodology for fork-style protocols** — supersedes M-08 yield-per-effort on Aave-style codebases.

- **`methodology/M24-fresh-eyes-surfaces.md`** — Late-stage surface enumeration methodology. After ≥1 prior breadth pass, enumerate 5-8 surfaces NOT covered by current hypothesis set (tertiary contracts, recently-modified files, lightly-used helpers, magic numbers, cross-contract invariants, dead code, test-leaking-into-prod, TODO/FIXME comments). Spawn ONE general-purpose agent with the surface list and 5-finding cap. Validated on K2: 2/2 novel findings (FE-1 → QA-L06 in Pass 5, Observation A → QA-04 in Pass 6) — surfaces no themed pass covered. **Highest-yield late-stage methodology**.

- **`rules/realism-filter.md`** — First-class permissionless/admin-trust/design-choice/unreachable-precondition/semi-trusted-role tagging. Every finding MUST carry a `Realism Filter` tag. Phase 5d (bug validator) applies the filter BEFORE severity-decision-tree. Per-platform defaults table (Code4rena Competitive blocks admin-trust; Sherlock Bug Bounty allows them with -1 tier; etc.). Project-local override via CLAUDE.md "Realism filter" section. Validated on K2: without this filter the audit would have shipped 4-5 contested admin-trust Mediums.

- **`rules/agent-failure-recovery.md`** — Mandatory protocol when agents fail mid-pass (rate-limit cap, runtime error, zero output, timeout). **Forbidden patterns**: orchestrator manual fallback, prompt simplification, quick-grep confirmation, ship-without-verification. **Allowed patterns**: wait for cap reset, retry with identical prompt once, document unverified hypotheses with severity cap, surface failure to user. Codified after K2 Pass 7 manual fallback produced 3 false negatives (HF44 reclassification, HF50 nuance miss, HF51 missed QA-05) that agent retry corrected.

### Changed

- **`platform-quirks/stellar.md`** — Added quirks #9 (Aave V3 fork patch ancestry — V3.0.1/V3.0.2/V3.1/V3.2/V3.3 sweep table for K2-like ports), #10 (Soroban auth args binding is automatic via XDR; `require_auth_for_args` only needed for deferred auth), #11 (`try_invoke_contract<T,E>` type projection is not verified host-side; `invoke_contract` panic-on-error is fail-closed and SAFE — corrects K2 Pass 6 HF44 misclassification), #12 (cross-contract error code u32 collision is diagnostic-only when callers use `Ok(Err(_)) | Err(_) => return Err(SpecificError)` pattern).

- **`methodology/INDEX.md`** — Registered M-23 and M-24. Added per-audit high-yield template guidance: M-23 for Aave V3 forks (replaces M-08 as highest-yield for fork-style protocols); M-24 for late-stage audits (after ≥1 prior pass).

- **`LEARNED_INDEX.md`** — Added K2 Code4rena audit entry (1 Medium + 9 Lows + 5 Info across 8 passes / 108 hypotheses). Updated methodology maturity tracking with M-23 and M-24 validations.

- **`MEMORY.md`** — Added 1.9.0 row with K2 metrics: RC-AGENT = 3 (manual-orchestrator errors corrected by agent retry), Reclassified = 1 (HF44 SAFE not unsafe).

- **`SKILL.md`** — File-structure listing updated to include `realism-filter.md` and `agent-failure-recovery.md` under `rules/`.

### Validation Summary

K2 Code4rena audit (2026-05-05):
- **8 passes / 108 hypotheses** — yield knee at Pass 6, Pass 7-8 sub-source-level all REFUTED
- **1 Medium + 9 Lows + 5 Info** = 15 findings; all 14 QA-Bundle entries follow M-23 consistency-class pattern
- **Pass 7+8 retry via /dewaxguard core** — 7 agents successfully verified after initial usage-cap failure; corrected 3 manual-orchestrator errors
- **Realism filter** — reclassified ~40% of candidate findings (HF38-b auto-promoted by agent then correctly downgraded; HF41 + HF44 routed to ADDITIONAL_LEADS via V12 dedup)

## [1.8.0] - 2026-05-04

**Origin**: Cross-pollination from cosminmarian53/skills `soroban-auditor` (commit 2 of 2). Deterministic recon-artifact builder + Rust source squeezer. Builds on the v1.7.0 prompt-only guards by giving them concrete artifacts to consume.

### Added

- **`scripts/build_recon_maps.sh`** — multi-language deterministic recon preprocessor. Runs in Phase 1.0 (BEFORE recon agents spawn) and emits 11 stable greppable artifacts under `$SCRATCHPAD`:
  - `guard-map.md`, `state-flags.md`, `integration-map.md`, `math-map.md`, `unsafe-map.md`, `logic-anomaly-map.md`, `blackhat-maps.md`, `divergence-map.md` (curated near-twin pairs diffed via `difflib.unified_diff`), `invariant-extract.md` (harvested from `fuzz/invariants.*`).
  - `docs-intent-map.md` (consumed by Phase 5d Gate 1a — see `rules/docs-intent-map.md`).
  - `auth-critical-files.txt` (consumed by the squeezer and by every agent claiming missing-auth — see `rules/auth-critical-files.md`).

  Per-language pattern banks for `evm` / `solana` / `stellar` / `aptos` / `sui` / `cpp`. Curated divergence pairs per language (e.g. lending: `supply` vs `supply_on_behalf`, `liquidation_call` vs `internal_liquidation_call`, `flash_loan` vs `flash_loan_simple`). Repo-augmentable via `$OUT/divergence-pairs.txt`.

  **Validation**: smoke-tested against the K2 audit codebase (Stellar Soroban, ~15K SLoC). Produced 252 guard-map entries, 488 state-flags, 1005 integration sites, 351 math sites, 808 pub-fn signatures, 23 auth-critical files, and 921 invariant lines — empty unsafe-map (correctly, Soroban has no unsafe surface). Total recon-stage tokens emitted to disk in <1s.

- **`scripts/squeezers/squeezer_rust.py`** — Rust source minifier ported (with attribution) from cosminmarian53/skills `soroban_token_squeezer.py` (MIT). Generalizes from Soroban-only to Anchor and native Solana — the brace-counter/string-escape logic is language-feature-agnostic Rust. Modes: `--collapse-bodies` (replace each `fn ... { body }` with `{ ... }`, brace-counted, respects strings/chars/raw strings/comments), `--numbered` (line numbers post-minification), `--keep-full F,G` (substring allowlist that bypasses collapse for auth-critical files). Emits `[full-bodies]` / `[collapsed]` tags per file consumed by `rules/auth-critical-files.md`.

  **Validation**: smoke-tested on K2's `kinetic-router/src/admin.rs` (6,844 bytes uncollapsed → 2,167 bytes collapsed = ~68% reduction). Allowlist correctly preserves bodies of `admin.rs`, `access_control.rs`, `token/src/contract.rs`, etc.

### Changed

- **`SKILL.md` Phase 1** — split into Phase 1.0 (deterministic preprocessors, run BEFORE agents) + Phase 1.1 (4 recon agents, run AFTER preprocessors). Recon Agent 1B and Agent 3 now augment the pre-built artifacts rather than emitting them from scratch — same end state, much faster, deterministic.
- **`SKILL.md` file-structure listing** — adds the `scripts/` tree.
- **`README.md`** — adds a "Recon scripts (v1.7.0)" section showing the standard invocation; adds upstream attribution under "Methodology Sources".

### Why this release matters

The v1.7.0 prompt-only rules created mandatory validator fields (`docs_intent_check`, `auth_check`, `severity_check`) but agents had to re-grep the docs/auth surface every time. v1.8.0 ships the deterministic preprocessor that emits the source-of-truth artifacts ONCE, and every downstream agent reads from them.

Token budget impact (measured on K2 stellar smoke test):
- Without preprocessor: each of 8 breadth agents would re-grep `require_auth` across 95 `.rs` files = 8× the same work.
- With preprocessor: one bash pass produces `guard-map.md` (252 lines) consumed by all 8 agents.

False-positive impact: the squeezer's `[full-bodies]` / `[collapsed]` tags categorically prevent the body-collapse hallucination class. Findings alleging missing-auth on a `[collapsed]` file MUST Read the body or DOWNGRADE to LEAD per `rules/auth-critical-files.md`.

### Compatibility

The preprocessor is OPTIONAL — the skill works without it (agents fall back to direct grep). When run, it merely accelerates and stabilizes the recon stage. To skip, omit Phase 1.0; the validator falls back to grep-time docs-intent checks. To keep the FP guards but skip the squeezer, run only `build_recon_maps.sh` and let agents Read source files directly.

---

## [1.7.0] - 2026-05-04

**Origin**: Cross-pollination from cosminmarian53/skills `soroban-auditor` (commit 1 of 2). Prompt-only false-positive guards. Zero new agents, zero new scripts — pure rule additions and prompt edits.

### Added

- **`rules/docs-intent-map.md`** — pre-extracted "by design / intentional / accepted trade-off / out of scope / known limitation / expected behavior" signals from project docs, emitted by Recon Agent 1B. Phase 5d Gate 1a (Refutation) hard-fails any finding without a populated `docs_intent_check:` field. Prevents the entire FP class where agents file findings on documented behavior and the validator manually re-rejects them at submission time. Source artifact: `{SCRATCHPAD}/docs-intent-map.md`.
- **`rules/severity-decision-tree.md`** — 3-question ordered tree applied at Phase 5d Gate 4a. The first YES determines severity: (a) directly stolen/lost/locked → HIGH; (b) core function broken / liveness / compounding accounting drift → MEDIUM; (c) else → LOW/QA. Findings whose claimed severity exceeds the tree result get a 10-30 point deduction in the bug-validator score. Replaces ad-hoc severity reasoning with a defensible mechanical procedure.
- **`rules/auth-critical-files.md`** — allowlist of files (admin/access-control/auth/emergency/upgrade/governance/multisig substrings + per-language entry-point lists) whose bodies MUST be emitted in full by any future squeezed/skeleton bundle. Pairs with the new `auth_check:` field requirement: findings alleging missing auth must record whether they read the actual body (`SAW_FULL_BODY` / `SAW_GUARD` / `SKELETON_ONLY`). Prevents the high-volume "missing require_auth" hallucination produced when a body-collapsing preprocessor hides the guard. Recon Agent 3 emits `{SCRATCHPAD}/auth-critical-files.txt` per audit.
- **`rules/agent-tool-budgets.md`** — per-agent Read/Grep caps (e.g. vector-scan 4/6, access-control 5/6, depth-token-flow 8/6, bug-validator 12/8). Halved in `light` mode, +50% on depth/validator in `thorough` mode. Mandatory greps (e.g. access-control → `guard-map.md`, validator → `docs-intent-map.md`) count against budget but cannot be skipped. Agents end every output with a `budget:` receipt; over-budget hypotheses convert to LEADs flagged `tool_budget_exhausted: true` for follow-up by depth or validator phases.

### Changed

- **`rules/finding-output-format.md`** — `verified:` field is now MANDATORY for every FINDING (not LEADs). Must paste the actual ±2 lines from the source around the cited bug location. No paste = auto-reject by the validator harness. Three additional fields added that Phase 5d populates: `docs_intent_check:`, `severity_check:`, `auth_check:`.
- **`agents/hacking-agents/shared-rules.md`** — added the `verified:` requirement, the tool-budget rule, the auth-critical-file rule, and an extended FINDING/LEAD output template that includes `verified:`, `tool_budget_exhausted:`, and the `budget:` receipt line.
- **`SKILL.md`** Phase 1 Recon — Agent 1B now MUST emit `docs-intent-map.md`; Agent 3 now MUST emit `auth-critical-files.txt`. Phase 5d Validation Pipeline — Gate 1 split into 1a (docs-intent) + 1b (auth-check); Gate 4 gains 4a (severity decision tree). File-structure listing updated to reflect the four new rules files.

### Why this release matters

`soroban-auditor` (Pashov-fork by cosminmarian53) ships four mechanical FP guards that dewaxguard previously handled in prompt-space (variable, agent-by-agent). Codifying them as rules + mandatory validator fields means:

- Documented "by design" behavior is rejected at validation time, not at submission time — saves judging cycles.
- Severity reasoning produces an audit trail (`severity_check: a=NO, b=YES → MEDIUM`) instead of an opinion.
- Body-collapse hallucinations are categorically prevented for auth-critical files instead of relying on per-agent vigilance.
- Tool-budget receipts let the orchestrator detect both under-spending (cautious agents) and over-spending (loose prompts) systematically.

These are all prompt/rule changes. Commit 2 (next) ports the deterministic recon-map builder script and the Rust source squeezer that consume the artifacts.

---

## [1.6.0] - 2026-04-30

**Validated in**: Monetrix audit (Code4rena, April 24 – May 4, 2026)

### Added

- **M-22: Hypothesis Pre-Declaration with Falsifiable Verdict Tracking** (`methodology/M22-hypothesis-pre-declaration.md`). Per-domain pre-declared `H{domain}.{n}` hypotheses BEFORE breadth agents spawn. Agents verdict CONFIRMED/PARTIAL/REFUTED against a closed set instead of open-ended discovery. Validated across Domains 11/12/13/14 of the Monetrix audit: 2 breadth agents per domain achieved same coverage as 8-agent open-ended breadth (~75% budget reduction, no recall loss). Refutations flow systematically into R-N manifest deltas. Cross-language: EVM/Solana/Move/C++.
- **C4 Submission Format Rules** in `references/criteria/c4-competitive.md`. Codifies Code4rena's "one QA report per audit" + "all low-severity AND governance/centralization findings → QA-Bundle" rule as a mechanical routing matrix. Misrouting governance/centralization findings to separate Medium slots risks AI-4 invalidation; routing to QA-Bundle preserves QA points. Includes trigger heuristic for "governance/centralization-class" findings and pre-submission consolidation gate.
- **SKILL.md Phase 5d Gate 4.5 — Submission-Slot Routing**. New sub-step after the 4-gate validation pipeline. Applies platform-specific submission format rules before writing findings to their severity slots. For Code4rena: routes governance/centralization-class findings to QA-Bundle as L-N entries instead of separate Medium files.

### Validated outcomes (Monetrix April 2026)

- M-22 ran on Domains 11-14 → 0 false positives, all hypotheses verdicted, ~30-40% total audit-time savings vs open-ended discovery on prior domains
- C4 Submission Format Rules caught the `setRedeemEscrow` rotation routing risk before submission → finding folded into QA-Bundle as L-03 instead of submitted as borderline-AI-4 Medium
- Phase 5d Gate 4.5 + bug-validator integration produced final submission state aligned with Code4rena one-bundle rule

### Why this release matters

The M-22 + C4-format-rule pair fixes a class of audit bloat where multiple borderline-Medium governance findings get submitted as separate files, then collapse to QA at judging — losing per-finding judging cycles and risking sponsor-side dismissal as severity-inflation. The fix is mechanical (routing matrix) not judgmental.

---

## [1.5.0] - 2026-04-26
- **M-21 Cross-Agent Contradiction Protocol** (NEW, methodology/M21-...md): always-on merge-step protocol for multi-reviewer pipelines. When 2+ reviewers disagree on the same code surface, OR a lone-flagger surfaces a finding the others missed, mandatory source-code arbitration at the merge step (4-step protocol). Generalizes the M-18 Phase-3 sub-rule into a stand-alone always-on protocol independent of any matrix domain.
- **Validated origin**: XRPL Sherlock April 2026 audit. M-21 alone produced L-35 — the **3rd reward-pool hit (XLS-0075 Permission Delegation)** that all 7 other breadth agents missed. Without M-21 the audit would have shipped 2 of 5 reward pools instead of 3. Independently re-validated against majority-refute in Domain 18 ECS18-1.
- **M-19 Path-Selection Determinism × Economic-Asymmetry Matrix** (NEW): 35-cell breadth scaffold for path-finder / route-selection / DEX-aggregator audits. 7 determinism dimensions (D1-D7) × 10 economic-asymmetry dimensions (E1-E10). Cross-language: Uniswap V3 SmartOrderRouter, 1inch Pathfinder, Jupiter, Orca, DeepBook, PancakeSwap. Validated origin: XRPL Domain 21 (Pathfinder × MPT) — surfaced L-34.
- **M-20 Wire-Format Mature-Layer Audit Matrix** (NEW): 4-dimension verdict per type-codec cell (parse-time validation / template completeness / cross-codec consistency / fuzz-coverage). Includes orphan-public-API filter and convergence-on-informational handling. Cross-language: Bitcoin CTransaction consensus rules, Ethereum RLP, Solana borsh, Cosmos protobuf PROTO3 LAST-WINS, Sui/Aptos BCS. Validated origin: XRPL Domain 20 (Binary Serialization / Canonical-Form Attacks) — 35/35 NEW SFields PASS unanimously across 7 of 8 agents.
- **rules/cross-class-preflight-firewall.md** (NEW): defensive-pattern rule. When a system has multiple authority classes (delegate / sponsor / pseudo-account / admin / governance), each must be validated at preflight before reaching transactor-specific logic. Sibling-transactor cross-comparison test for finding-class detection.
- **platform-quirks/cpp.md** (UPDATED): new section "🚨 #12 — Delta-Scope Contest Validity Rules" capturing T-06 (pre-existing-with-unchanged-impact = OOS), T-13 (grief-floor cap at Low), and amendment-gating reachability. Cross-platform mapping for Cosmos SDK upgrades, EVM proxy upgrades, Solana program upgrades.
- **methodology/INDEX.md** (UPDATED): M-19/M-20/M-21 entries added; "How to use" extended with merge-step rule (apply M-21); "Per-audit high-yield template" extended with M-21/M-19/M-20 specific guidance.
- **Audit metrics from validation source**: XRPL April 2026 ran 12 of 21 domains via /dewaxguard thorough; surfaced 4 Medium + 5 Low submittables; covered 3 of 5 Sherlock reward pools (Sponsored Fees, MPT DEX, Confidential MPT + Permission Delegation via L-35).

## [1.4.0] - 2026-04-12
- Added Phase 4b.5 RAG Validation Sweep: every finding validated against Solodit database via unified-vuln-db MCP tools
- Primary tools: validate_hypothesis, search_solodit_live (historical precedent lookup)
- Fallback chain: get_similar_findings → get_common_vulnerabilities → WebSearch (site:solodit.xyz)
- RAG score feeds into bug validator (Phase 5d) confidence axis and Phase 5d.1 submission hardening
- Recon Agent 1A now probes MCP tool availability and sets RAG_TOOLS_AVAILABLE flag
- Floor score 0.3 if all tools fail — preserves pipeline progress on tool errors
- New file: rules/rag-validation-sweep.md (full spec)

## [1.3.0] - 2026-04-12
- Added Inconsistency Scanner: depth/breadth agents grep codebase for correct pattern used elsewhere (shared-rules.md)
- Added Platform Threshold Enforcement: mandatory quantification rules per platform in report-template.md
- Added Trust Boundary Mapping: meta-tx/relay role analysis in access-control-agent.md
- Added Caller-Controlled Callback Tracing: attacker-supplied target trace in execution-trace-agent.md
- Added Submission Hardening Pass (Phase 5d.1): feedback loop from bug validator to fix deductions before report
- First audit metrics: Superfluid ClearMacro (EVM), 2M found, both scored >90 after hardening

## [1.2.0] - 2026-04-12
- Added self-calibration: Phase 5e auto-analyzes agent FP rates, confidence accuracy after every audit
- Added batch import: `/dewaxguard batch-import` processes multiple public contest results in one session
- Added benchmark suite: `/dewaxguard benchmark` runs pipeline against known-vulnerable contracts for regression testing
- Added 6 starter benchmarks: EVM (reentrancy, share-inflation, unchecked-return), Solana (missing-signer, pda-substitution), Sui (shared-object-race)
- Each benchmark includes false-positive traps to test precision alongside recall

## [1.1.0] - 2026-04-12
- Added self-improvement system: `/dewaxguard improve` and `/dewaxguard consolidate`
- Added MEMORY.md metrics ledger
- Added CHANGELOG.md version history
- Added YAML frontmatter for Claude Code skill compatibility

## [1.0.0] - 2026-04-12
- Initial release: 8 hacking agents, Nemesis cross-feed, depth analysis, fork PoC, bug validator
- Multi-language support: EVM, Solana, Aptos, Sui
- Platform-specific validation: Code4rena, Sherlock, Cantina, Immunefi
