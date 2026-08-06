# DewaxGuard Changelog

## [1.33.0] - 2026-08-06

**Origin**: 0xSimao, "How I use AI in smart contract audits (2026)", 4 August 2026 (user-supplied article). Not a post-mortem — no ground truth was compared. This release encodes three claims from that article that the pipeline structurally violated, each confirmed absent by grep before the edit rather than assumed.

The article's claims, checked against this skill:

| Claim | Status here before v1.33.0 |
|-------|---------------------------|
| Severity is an economic judgment models get wrong in both directions | **Mostly covered.** `realism-filter.md` Gate R-0 and `severity-decision-tree.md` grief gates G1/G2/G3 already force articulated mechanisms. Gap: G3's quantification demand fired for *availability findings only*. |
| A clean pass is not coverage; the same tool run twice gives two different sets | **Violated.** Nothing measured run-to-run variance, and no report section stated what was not examined. |
| A PoC that exercises a mock proves the mock; check the assertion would fail if you reverted the bug | **Absent.** Zero matches for mutation / positive-control / revert-the-bug across the whole skill. |
| Do not ask a model how something works and accept the answer | **Partially covered.** `verified:` at finding level and M-32 at the final gate; nothing at the agent handoffs in between, where every hop launders a guess into a premise. |
| The gaps in a test suite are the gaps in their thinking | **Absent.** Zero matches for test-suite gap analysis. |

### Added
- **`rules/negative-space.md`** (new) — the complement the pipeline could not compute. Every stage after breadth is conditioned on the breadth finding list, so a region no breadth agent entered is invisible to inventory, depth, chain and verification alike, and silence there gets reported as a clean result. Three sources, each finding a different blind region and none substituting for the others:
  - **Phase 1.2 Test-Gap Map** — classifies every in-scope entry point and extracted invariant as `UNTESTED` / `HAPPY-ONLY` / `ADVERSARIAL` / `FUZZED`. The `UNTESTED` + `HAPPY-ONLY` sets become depth targets in their own right, outranking a finding-derived target of equal severity on contested budget. `FUZZED` is explicitly not a safety signal.
  - **Phase 2.5 Findings-Blind Protocol Model** — one agent, forbidden from reading any findings file, `analysis_*.md`, hypothesis list, prior-audit report, known-issue index, `refuted/INDEX.md` or `patterns/`. Emits protocol intent, an invariant ledger (each `file:line`-enforced or `NOT ENFORCED IN CODE`), and a value-outflow map organised by protocol mechanic with the actor gate per site. At Phase 4c, invariants and outflow rows no finding references are the unmodelled region; a `NOT ENFORCED` + permissionlessly-reachable row is promoted to depth regardless of budget.
  - **Phase 3.5 Blind Re-Run** — re-runs `invariant-agent`, `economic-security-agent`, `first-principles-agent` with no exclusion list and no pass-1 findings in context, and computes `stability = |P1 ∩ P2| / |P1 ∪ P2|` on group_keys via the existing `parse_findings.py` + `dedup.py`. `vector-scan-agent` is deliberately excluded — known patterns are the commoditizing half and the most stable across runs, so re-running it buys the least per token. Distinct from the exclusion-list rescan, which measures novelty and by construction cannot detect variance.
  - **Phase 6 mandatory report section** — "What this audit did not cover". Bans "full coverage", "all paths analyzed", "the contract is clean", and *coverage* used for a throughput count.
- **`rules/fork-poc-execution.md` §7 — PoC Integrity Gate (HARD)**: four receipts required for any `[FORK-PASS]` / `[POC-PASS]`. **7a mutation check** (revert the bug, the test MUST fail — if it still passes the assertion is not measuring the bug and the result is void). **7b positive control** (mandatory before any negative result stands; a broken harness and a hardened target both produce FAIL, and the surfpool BPFLoader2 token-program substitution is the worked example). **7c real-path audit** (no mock on the value flow being proven). **7d assertion audit** (a balance delta at a named address, not a revert or success flag). Failing or skipping any drops the tag to `[CODE-TRACE]`.
- **`rules/severity-decision-tree.md` — Quantification gate**: extends the demand for a measured number from the availability branch to **every** branch. a=YES needs `loss` measured as a delta from a zero-capital start (or capital stated and marked RECOVERABLE/UNRECOVERABLE); b=2 needs a drift *rate* and horizon ("it compounds" is the mechanism, not the impact); b=3 needs the invariant's source; b=4 needs magnitude and boundedness. Four mandatory fields: `victim` / `loss` / `attacker_cost` / `recoverable`. `loss: UNQUANTIFIED — {reason}` is an accepted value that caps at Low — never invent a figure. Escalation is symmetric: a measured loss materially above the claimed tier escalates.
- **`rules/finding-output-format.md` — Handoff citation discipline**: any claim about what the code does, written into a scratchpad artifact another agent will read, carries `file:line`. Consuming agents treat uncited upstream claims as unverified and must either cite them or carry `depends_on_unverified:` forward, which blocks any tier above Low until discharged by a citation (not by a second agent agreeing). Binds the orchestrator's own prior turns.
- **`~/.claude/audit-method.md`** (new, global, imported from `~/.claude/CLAUDE.md`) — rules **A-1** (a quiet pass is not coverage), **A-2** (no uncited mechanism claim), **A-3** (a test that cannot fail proves nothing). Tool-independent by design: they describe ways model output can look like work without being work, so they bind dewaxguard, dewaxoffense, dewaxdlt, plamen and ad-hoc reads alike. Added to preflight as Step 1.5.

### Changed
- **`SKILL.md`** — pipeline overview gains phases 1.2 / 2.5 / 3.5 and the negative-space spine note; modes table updated (+1 agent all modes, +3 core/thorough; light skips the re-run); Phase 4b depth agents now receive `test-gap-map.md` alongside `findings_routed.json`; Phase 5c leads with the integrity gate; Phase 6 gains the mandatory negative-space section and the quantification ledger per finding.
- **Evidence tag table** (`rules/fork-poc-execution.md`) — `[FORK-PASS]` and `[POC-PASS]` now require the §7 all-pass; `[FORK-FAIL]` requires a passing positive control before it supports FALSE_POSITIVE; `[CODE-TRACE]` is named as the ceiling for any PoC that fails or skips §7.

### Deliberately not changed
- **Coverage-claim language in `~/.plamen/rules/`** (`phase3b` "skip iteration 2 unconditionally", `phase5` "Verification coverage: N/N") is the same A-1 violation but lives in globally-loaded files outside this skill. Left alone by scope decision; rule A-1 in `audit-method.md` overrides it wherever both are in context.
- **No RC classification or recall metric** for this release — there is no ground truth behind it. It does not get a `MEMORY.md` metrics row.

## [1.32.0] - 2026-08-05

**Origin**: Post-mortem of Sherlock 1279 (oracle-priced bin AMM). One missed valid Medium — a floored cross-price quotient in a two-feed synthetic oracle path — traced to **four compounding layers**, seeded by a recon regex gap. RC-METHOD → `FM-10`. A second judged result (a submitted JIT fee-capture finding ruled invalid) classified RC-AGENT and shipped no rule, per the presumption gate.

The miss chain, in order of causation:
1. **`MATH_PAT` never matched `mulDiv` / `Math.*`.** `\.mul\s*\(` does not match `Math.mulDiv(`. The dominant precision-critical primitive in modern Solidity (OpenZeppelin `Math.mulDiv`, Uniswap `FullMath.mulDiv`) was therefore absent from every `math-map.md` this skill has generated — so the numeric specialist never reached the file, and the only agent that did was a trust-boundary agent with no numeric tooling. Verified against the real target: the exact bug line scored **0 matches** under the old pattern; the map grew **16 → 43 rows** on the affected subset after the fix.
2. **All truncation coverage was truncate-to-ZERO.** Every bullet across math-precision and numerical-gap ("zero-round to steal", "fees truncate to zero", "bonus rounds to zero") targets a vanishing result. This bug truncated to **1** — nonzero, passes every validity guard, looks like a legitimate price, carries ~49% error.
3. **Operand-extreme framing manufactured a false actor dependency.** The boundary agent's only numeric question is "empty / zero / max input", applied to operands. That yields a *divergence* story ("the two legs sat at opposite guard edges"), which imports whoever controls those edges as an actor. The bug's real form needs no actor and is present at ordinary mid-range inputs.
4. **The realism filter then terminally rejected the mis-framing**, and chain analysis subsumed the survivor into a larger admin-gated hypothesis that the same filter parks on most platforms — deleting the only submittable member of the pair.

### Fixed
- **`scripts/build_recon_maps.sh` — EVM `MATH_PAT`**: added `mulDiv|mulDivDown|mulDivUp|mulWad|divWad|FullMath|PRBMath|UD60x18|SD59x18|Math\.\w+\s*\(`; removed `\.add\s*\(|\.sub\s*\(` (SafeMath is dead on ≥0.8 — they only matched `EnumerableSet.add` noise). Soroban `MATH_PAT`: added `mul_div|\.fixed_div|\.fixed_mul`.

### Added
- **`scripts/build_recon_maps.sh` — math-map quotient-range mandate**: every row whose quotient is returned or stored must state the quotient's magnitude range over the realistic input domain and whether any regime puts it under ~1e3 in its own fixed-point units. An un-ranged row is not cleared.
- **`agents/hacking-agents/math-precision-agent.md` — "Quantize a live quotient"**: the truncate-to-small-**nonzero** class. Relative error of a floored quotient is `ULP / value`, so it explodes as the quotient approaches its own unit (100% at q=1, 50% at q=2, <0.1% only above q≈1e3). For every division whose result is consumed as a price / exchange ratio / rate / scale, compute the quotient's magnitude across the **realistic** input domain and flag regimes under ~1e3. Enumerate the boundary in the **output** domain and invert to the inputs that reach it — operand extremes do not reach this bug; ordinary mid-range operands do.
- **`agents/hacking-agents/numerical-gap-agent.md` — Seam 2 output-domain enumeration**: the same inversion at the boundary×precision seam.
- **`agents/hacking-agents/boundary-agent.md` — Step 6 (computed values hand off)**: when the thing crossing the boundary is a value the code *computes*, operand extremes are insufficient and actively mislead (divergence story → filtered as admin-trust; quantization story → permissionless and survives). A computed-value boundary cannot be closed as "guarded" on an operand-only sweep.
- **`rules/realism-filter.md` — Gate R-0 (re-derive with all actors honest)**: MANDATORY before tagging `design-choice` / `admin-trust` / `semi-trusted-role` / `unreachable-precondition`. Restate the bug with every actor honest and every config at ordinary in-envelope values; if a loss still occurs, the finding is `permissionless` and the actor dependency came from the framing, not the code. Necessary because every non-permissionless outcome in the tree is terminal. Names the two framings that most often manufacture a false dependency (guard-tightness, opposite-extremes).
- **`rules/chain-analysis-prompt.md` — Subsumption direction**: absorption runs toward the **more reachable** hypothesis, never the bigger number. A `permissionless` finding is never subsumed by an actor-gated one regardless of magnitude; the survivor inherits the **lowest** actor gate among its constituents; "weaker variant of" is a valid dismissal only within the same gate. Every `NEG/subsumed` coverage-map row must carry both sides' actor gates.
- **`failure-modes/INDEX.md` — FM-10**.
## [1.31.0] - 2026-07-26

**Origin**: DRE Sherlock post-mortem (2026-07). A **real** defect — the wrong-list compliance check in `fillWithdrawal` (dreUSD freeze list checked, USDC blacklist paid, no `try/catch`), permanently bricking the automated keeper queue — was submitted as Medium with a passing end-to-end fork PoC and rejected: *"attacker will lose way more than the party being affected(protocol here), I don't see how this should be Medium/High at all."* The attacker's dust was unrecoverable; the victims suffered only delay the TREASURY could clear manually.

Every gate behaved correctly by its own rules. The realism filter tagged it `permissionless` (true — the trigger is permissionless and the victims are involuntary) → *"No adjustment"*. The severity tree answered `b=YES` on liveness → Medium. `references/criteria/sherlock-bounty.md` lists *"Medium | Griefing; DoS"*. The pipeline read its rulebook and got Medium. **The rulebook was missing a dimension it already had elsewhere**: attacker-cost-vs-victim-harm lived in `rules/l1-severity-matrix.md` ("Single-node DoS with high attacker cost → Low"), `references/criteria/immunefi.md` ("Medium 'Griefing' requires DEMONSTRATED damage") and `M16` ("unless easy-to-trigger with zero attacker cost") — and had never been generalized to the smart-contract path. This release generalizes it. Methodology + mechanism only — no stored bug patterns.

### Added
- **`rules/severity-matrix.md` → Grief economics** — three mandatory gates for any DoS/griefing finding: **G1** economic rationality (attacker's *unrecoverable* cost < quantified victim harm), **G2** operator recovery (a routine privileged action restores service, no funds lost), **G3** quantification (both `attacker_cost:` and `victim_harm:` declared). Any FAIL caps at **Low**. Includes the **self-admission rule**: a finding whose own text concedes a recovery path ("the TREASURY can still recover", "requires manual fills") is treated as operator-recoverable unless it explicitly sets `operator_recoverable: false`. Explicitly scoped to availability impact — theft, fund loss and accounting drift are unaffected.
- **`rules/realism-filter.md` → `uneconomic-grief` tag** (7th tag) — permissionless trigger + involuntary victim, but the attacker's unrecoverable cost ≥ quantified victim harm. Action is **cap at Low**, not reject: the underlying defect is usually real and belongs in the QA/Low bundle. Wired into the filter's decision tree (new step 2a), output format, and mechanical-enforcement list.
- **`scripts/severity_router.py::apply_grief_economics`** — mechanical implementation of G1/G2/G3, applied in `derive_severity` **before** the proven-only cap so a `[FORK-PASS]` cannot rescue an uneconomic grief (the DRE finding had one). Text scan walks every string in the finding so the self-admission check works regardless of which phase/field the prose lands in.
- **`prompts/phases/55_validator.md` → Gate 4a** — the Phase 5d counterpart, including a literal grep list for the self-admission scan, run where the full writeup prose actually exists.
- **Required fields for DoS/grief findings** (`attacker_cost:`, `victim_harm:`, `operator_recoverable:`) documented in `agents/hacking-agents/shared-rules.md`, `rules/realism-filter.md` and `rules/severity-decision-tree.md`.

### Changed
- **`rules/severity-decision-tree.md`** — added the **b-qualifier**: a `b=YES` answer on *liveness/availability* is provisional until the grief-economics gates pass; compounding-accounting (b=2), invariant breaks (b=3) and accounting inconsistency (b=4) are exempt. The existing `✅ b=YES: liquidationCall() can be DoS'd by a tiny dust deposit` example was the DRE shape verbatim and is now marked provisional with the conditions under which it holds at Medium. `severity_check:` must show the gate verdicts for availability findings.
- **`scripts/parse_findings.py`** — `REALISM_NORMALIZE` accepts `uneconomic-grief` / `uneconomic_grief` (without this the new tag was silently dropped at parse time).
- **`scripts/dedup.py`** — `uneconomic-grief` ranks above bare `permissionless` in the canonical-selection priority: it is a *refinement* of permissionless, so the agent that actually did the cost/harm analysis wins the merge. Over-capping ships in the QA bundle; over-claiming gets rejected.

### Known issue (pre-existing, not changed here)
- `scripts/dedup.py` realism-priority comment says *"keep the most-restrictive non-permissionless tag"* but the `max()` over the priority map keeps the **least** restrictive (`permissionless: 5` wins). Left as-is — flipping it would change dedup semantics for every existing tag and could suppress real findings; flagged for a deliberate decision.

## [1.27.0] - 2026-07-15

## [1.30.0] - 2026-07-26

**Origin**: Request to let dewaxguard "learn from" a reproduced-exploit corpus (crypto.training / DeFiHackLabs — hundreds of real on-chain hacks with root-cause + Foundry PoC). The trap was to bolt on a stored bug-pattern database, which fights the skill's core principle ("methodology, not stored bug patterns" — the whole reason for the adversary gate + refuted index). Instead this routes the corpus through the learning loop that already exists (`/dewaxguard batch-import` → coverage check → `failure-modes/INDEX.md` class-level ledger → M-template proposal + `benchmarks/` seed), adding the deterministic backbone that the uniform PoC-corpus source makes possible. Learning stays at the class / evaluation level; the specific exploits never persist. Selfcheck is now 14 checks.

### Added
- **`scripts/import_exploits.py`** — deterministic backbone for the exploit-corpus source. Ingests a normalized corpus JSON and (a) runs a keyword co-occurrence coverage check per class (COVERED / PARTIAL / NOT_COVERED — is there a methodology file actually *about* this class, not just the words scattered), aggregates by `(class, language)`, applies the same `>= min-occurrences` recurrence filter as batch-import, and emits paste-ready `failure-modes/INDEX.md` candidate rows merged against existing FM rows; and (b) `--scaffold-benchmarks` creates `benchmarks/<lang>/<slug>/` ground-truth + manifest skeletons for a blind, scored regression case. **Anti-anchoring by construction**: persisted output carries only generic class + language + root cause — the corpus may include `name`/`loss_usd`/`date`/`chain`, but those are never written out. `--json` mode; validated on the real crypto.training slice (12 recent hacks → surfaced `amm-reserve-desync` skim/sync reserve manipulation as a recurring uncovered class).
- **`scripts/fixtures/exploit-corpus.sample.json`** — generic (synthetic, no real protocol names) sample corpus documenting the input schema and driving selfcheck's importer test.
- **`scripts/selfcheck.sh` check 14** — importer present + executable, runs on the sample corpus, and (anti-anchoring lint) leaks none of the sample's identifying fields into its output.

### Changed
- **`improve/BATCH-IMPORT.md`** — added "Option D: Reproduced-exploit corpus (DeFiHackLabs / crypto.training)" describing the normalize → `import_exploits.py --coverage` → aggregate → FM-rows / M-template / benchmark-scaffold flow, under the existing Anti-Anchoring Rules. The specific exploits are a learning input, not a pattern store.

## [1.29.0] - 2026-07-21

**Origin**: Full source evaluation of `Kritt-ai/open-kritt` @ `6f9abc4` (~18.6k lines) for portable mechanisms. Five parallel extraction tracks; **three yielded nothing adoptable** — kritt's dedup, severity scoring, refusal path, and retry logic are each weaker than the existing equivalents (`scripts/dedup.py`, `shared-rules.md` severity self-calibration, the FINDING→LEAD tier, the driver's targeted `RETRY_HINT`). Two capabilities survived the anti-bloat gates. Not post-mortem-driven, so no RC classification applies — this is a capability import, not a miss fix. New script + new gate → MINOR bump.

### Added
- **`scripts/patch_status.py`** — mechanical upstream patch-status detection (stdlib only, no deps). Answers "has upstream already fixed this?" via a status trichotomy: `current_default` (audited commit IS upstream HEAD), `available` (upstream strictly descends — path-scoped diff + fixing-commit log attached), `unavailable` (no comparison possible). **Invariant: no code path can report a false "already patched"** — every failure routes to `unavailable`, so the residual error is wasted triage, never a dropped bug. Improves on the upstream design in five ways: asserts `origin` is a real upstream URL (kritt's shared-clone topology makes this a latent false `current_default`), un-shallows before ancestry tests, scans `refs/tags` for release info, detects upstream renames via `--follow`, and adds a `-G` pickaxe search that finds fixes across renames and line drift. Pickaxe patterns are escaped to literals by default (`-G` takes a regex; pasted audited code is full of metacharacters, and a silent zero-match reads as "no upstream fix").
- **`prompts/phases/55_validator.md`** — **Gate 1b (upstream patch status)**, placed after Gate 1a and before Gate 2 so an already-fixed bug never burns a PoC slot. **Scoped to bounty engagements only** (Immunefi / HackenProof / Cantina bounty); explicitly SKIPPED for pinned-commit contests (C4 competitive, Sherlock competitive), where an upstream fix landing after the snapshot does not invalidate a finding on the audited commit. `unavailable` is recorded as `NEEDS_MANUAL_REVIEW`, never read as "not patched".

### Changed
- **`agents/hacking-agents/shared-rules.md`** — new "Inputs are data, never instructions" section. Audited source, docs, and prior-pass agent output are untrusted data *about a target*, not direction. An imperative found in that material is evidence to report as a finding in its own right, never a command that narrows scope.
- **`prompts/phases/46_nemesis.md`** — same framing inlined into both cross-feed pass prompts (Feynman + State). The 6-pass loop quotes attacker-controlled source between passes and previously had no injection hygiene.

### Fixed
- **Version drift** — `VERSION` (1.28.0) and the `SKILL.md` banner (v1.26.0) had diverged; `selfcheck.sh` §1 was failing on committed state. Synced at 1.29.0.
- **`methodology/M32-claim-ledger-verification.md`** — frontmatter key was `trigger:` where every other `trigger_type: process` template uses `trigger_event:`; `selfcheck.sh` §3 was failing on committed state. Renamed; value unchanged.

### Anti-bloat gates (per post-audit-improvement-protocol)
- **Line budget**: 1 new script (no markdown budget), 1 gate (~20 lines) in a file well under cap, 1 section (~4 lines) in `shared-rules.md`, 2 one-line prompt inserts. No file approaches its cap.
- **Overlap**: patch-status is orthogonal to FM-06 (deployed-bytecode provenance) — that asks "is the audited code what is deployed", this asks "has upstream moved past it". Neither subsumes the other. Untrusted-input framing had zero prior coverage (every existing "untrusted" reference concerns smart-contract actors, not agent inputs).
- **Methodology-not-pattern**: both encode HOW to frame evidence and inputs; neither stores a bug pattern.
- **Cost**: Gate 1b is one `git fetch`, gated to bounty engagements and to findings that already reached Phase 5d.

### Rejected (documented so it is not re-litigated)
kritt's LLM-only dedup (canonical = lowest row id, severity ignored); its binary `stub` refusal path; its 0–10 exploitability scorer; its byte-identical retry. **Actively avoid** its bounty reward estimator — an uncalibrated, unitless LLM guess validated only by `min <= max`. kritt has **no quality measurement of any kind** (no corpus, no recall/precision metric, engine tests disabled in CI); `benchmarks/` + the improvement protocol remain the strictly stronger position.

## [1.28.0] - 2026-07-16

**Origin**: Metric OMM re-audit (Sherlock #1279). One methodology gap passed the RC-AGENT Exclusion Test + anti-bloat gates: the existing Phase 5d Gate 2 verifies load-bearing *enablers* but not the *full* claim set (mechanism chain, dedup, severity basis) of a final candidate. An adversarial line-by-line pass on three final candidates verified every mechanical claim to `file:line` (zero verification debt), corrected one REFUTED mechanism assumption a one-directional score pass had accepted, and caught a leaked internal PoC ID. Methodology only — no stored bug patterns. `extend`-class (extends Gate 2, no fork; final-candidate-gated for cost) → MINOR bump.

### Added
- **`methodology/M32-claim-ledger-verification.md`** — final-candidate (score >= 70) adversarial per-claim source verification. Decompose finding → atomic claims (mechanism / enabler / dedup / severity) → verify EACH to `file:line` via a two-sided refute+defend read (code decides, no uncited assertions) → classify VERIFIED / REFUTED / JUDGMENT → emit a verification ledger + verification-debt verdict + quarantined JUDGMENT residual. HARD gate: verification debt must be `none` before the report; a REFUTED load-bearing claim blocks submission. Extends Phase 5d Gate 2 (`enabler_check`) from enablers to the full claim set; does NOT resolve severity (quarantines it as JUDGMENT — that stays with `severity-decision-tree` + M-27). Cross-language (language-agnostic ledger). Hooked as **Phase 5d Gate 5 / Phase 5d.2**; indexed in `methodology/INDEX.md`. (RC-METHOD)

### Anti-bloat gates (per post-audit-improvement-protocol)
- **Line budget**: 1 new methodology file (~155 lines) + 2 one-line hooks (phase list + Gate 5) + 1 index row. No file approaches its cap.
- **Overlap**: extends Gate 2 rather than forking a parallel judge (>60%-overlap rule) and reuses `enabler_check`; does not duplicate the severity tree or M-27.
- **Methodology-not-pattern**: encodes HOW to verify claims; stores no bug pattern.
- **Cost**: gated to final candidates (score >= 70) only — never breadth/depth/LEAD.

## [1.27.0] - 2026-07-15

**Origin**: Session-lesson import from recent live-bounty audit sessions (Parallel V3, Raydium CLMM, DeFi Saver v3, Metric OMM, Twyne). Four methodology gaps passed the RC-AGENT Exclusion Test + anti-bloat gates; two candidates were dropped as already-covered (Immunefi v2.3 impact classification, shipped v1.24.0) and one as RC-AGENT (admin-config severity calibration — already covered by severity-decision-tree + realism-filter + M-27). Methodology only — no stored bug patterns. `extend`-class changes → MINOR bump.

### Added
- **`rules/fork-poc-execution.md` "Deployed-code provenance"** (EVM section) — impl-slot (EIP-1967) → `cast implementation`/`cast storage`, then 4-byte selector membership-test against the DEPLOYED bytecode before trusting repo HEAD. A missing selector or wrong impl = "audited source differs from deployed" finding + re-scope. Closes the EVM equivalent of the existing Solana program-ID/IDL-drift check. (RC-METHOD; FM-06)
- **`rules/fork-poc-execution.md` §6 "Common false signals"** — (a) misplaced `vm.expectRevert` on a setup call read as a live guard-defeat → arm-then-observe (wrap only the exploit call in `try/catch`, trace `-vvvv`) before escalating (Twyne L-04 was this artifact); (b) both-regime `vm.store` sweep for clamp-neutralized share/price-manipulation attacks (a `[FORK-FAIL]` in one regime is not a `[FORK-FAIL]` overall). (RC-METHOD + RC-DEPTH; FM-07, FM-08)
- **`platform-quirks/solidity.md` §8 "Layer-2 execution quirks"** — Arbitrum `block.number` returns the L1 block; use `ArbSys(0x64).arbBlockNumber()` for L2 height. `vm.roll` no-ops when the target reads `ArbSys`; mock the precompile instead. Confirm which clock the contract reads before trusting any timing-dependent PoC. (RC-METHOD; FM-09)
- **`references/criteria/immunefi.md` scope model** — Primacy of Impact vs Primacy of Rules: under Rules an impact on an unlisted asset is unsubmittable; under Impact an in-scope impact pays even when the triggering asset is off the list. Determine the model before parking a finding as OOS. (RC-METHOD)

### Changed
- **`prompts/phases/00_preflight.md` §1a** — added HARD "Provenance & claim-verification": (1) audited code == deployed code before spending depth (pointer to fork-poc-execution provenance procedure); (2) propagated factual claims ("live?/in-scope?/guard exists?/already audited?") are hypotheses to check against the primary source before relaying as fact; (3) extract the FULL bounty in-scope asset list + determine the program's scope model. Generalizes the EVM-only scope-extraction discipline (solidity.md §7) to preflight without duplicating detail.
- **`failure-modes/INDEX.md`** — added FM-06..FM-09 (the four fix-eligible classes above).
- **`MEMORY.md`** — v1.27.0 metrics row (session-lesson import: 4 RC-METHOD, 1 RC-DEPTH, 1 reclassified to RC-AGENT).

## [1.26.0] - 2026-07-12

**Origin**: Post-incident knowledge ingestion from the Bonzo Lend / Supra oracle exploit (Hedera mainnet, ~$10M). Attacker submitted a price update carrying a **zeroed BLS signature `[0,0]`**; the oracle's BLS verifier fed the degenerate points to Hedera's pairing precompile and, because both signature and committee key were the identity/zero, the pairing equation `e(0,G2) == e(H(m),0)` collapsed to `1 == 1` and returned true. The verifier never checked its inputs were non-zero and in-subgroup first, so a meaningless-but-mathematically-valid equation was trusted as a valid committee signature — inflating an oracle price ~1e12x and enabling ~$9.05M borrowed against ~$2 of collateral. dewaxguard had M-30 (signature replay/binding) and M-16 (ZK-proof composition) but **zero coverage of verifier input-validation soundness**. Methodology only — no stored bug patterns.

### Added
- **`methodology/M31-signature-verifier-input-validation.md`** — On-Chain Signature-Verifier Soundness template. Auditable soundness table per verifier (non-zero/non-identity, subgroup membership, on-curve, `ecrecover`→`address(0)` sentinel, semantic-vs-mathematical result, key provenance) with a 7-STEP process including the zero/identity test (the Bonzo shape), subgroup/small-order test, sentinel test, and STEP 6 consumer-side defense-in-depth pairing. `trigger_grep` fires on pairing/BLS/precompile/`ecrecover` primitives; cross-language (EVM `ecPairing` 0x08 / EIP-2537 / `ecrecover`, Solana `alt_bn128_pairing` / `blst`, Sui `bls12381`, Aptos `crypto_algebra`, Cosmos consensus BLS). Distinct from M-30 (binding/replay) and M-16 (ZK composition).
- **`references/attack-vectors/attack-vectors.md` #267** — "Pairing / BLS Signature-Verifier Accepts Zero / Identity / Small-Order Inputs" detect/FP entry, with FP gates (library subgroup-checks on deserialization; `ecrecover` compared to non-zero expected signer; BN254 G1 cofactor-1 exemption; pinned pubkey).

### Changed
- **`references/attack-vectors/attack-vectors.md` #174** (Missing Oracle Price Bounds) — added a reverse cross-link to #267 framing #174 as the CONSUMER-side defense and #267 as the VERIFIER-side root cause (the two boundaries of the Bonzo incident).
- **`methodology/INDEX.md`** — registered M-31 in the Entries table.
- **`LEARNED_INDEX.md`** — one-line external-incident enrichment entry (v1.26.0).

## [1.25.0] - 2026-07-08

**Origin**: Repo-wide code review (three parallel reviewers over the Python scripts, shell scripts, and driver↔prompt↔gate consistency). This release fixes the high-confidence, low-risk correctness bugs the review surfaced; a set of architectural findings that need a live pipeline run or a design decision were reported separately, not auto-fixed. Selfcheck stays green (now 13 checks, with the blind-stripper gate hardened to honor exit codes). Mechanism/robustness only — no stored bug patterns.

### Changed
- **`scripts/dewaxguard_driver.py`** — dry-run no longer writes phase checkpoints (a `--dry-run` followed by `--resume` would otherwise skip every phase); deterministic setup errors (missing template, backend not on PATH) abort immediately instead of retrying with an empty hint; an unknown or mode-excluded `--phase` now errors (exit 2) instead of silently running nothing; the retry hint now includes the subprocess status. Gates are invoked with `--src` and `--project-root` so `coverage_check` scopes the real source tree instead of guessing `project_root/contracts`.
- **`scripts/gates/coverage_check.py`** — takes `--project-root` (relative Read/scope paths resolve against it, not CWD); uses `Path.is_relative_to` (no crash on sibling-prefixed dirs); scope-file entries resolve against the project root; the retry hint names the misses file it actually writes.
- **`scripts/gates/content_check.py`** — accepts a `NO-FINDINGS` / `NONE-TRIGGERED` sentinel so a legitimately-empty phase output (niche "none triggered", a verify pass that refuted everything) passes the gate instead of pressuring agents to fabricate content; resolves non-scratchpad and absolute output specs correctly (no `ValueError` on absolute globs).
- **`scripts/blind_benchmark.sh`** — the answer-blind stripper no longer deletes Rust/Move `#[attr]` / `#![attr]` lines (the `#`-comment rule is now applied only to hash-comment languages), strips multi-line `/* … */` block comments, and replaces block comments with equal blank lines so ground-truth line numbers stay aligned; exits nonzero when an answer leak survives so `selfcheck` check 10 can trust it.
- **`scripts/bake_l1.sh`** — renamed the `LANG` variable to `BAKE_LANG` (it was clobbering the POSIX locale for every child process); fixed `rg -E` (ripgrep's `--encoding`) to `-e`; dropped the broken opengrep rung (semgrep can't run the PCRE patterns).
- **`scripts/run_benchmarks.sh`** — `--score` now fails when nothing was scored, when any benchmark produced no agent output, or on score errors (it previously reported 100% and exit 0 on an empty/misnamed outputs dir); JSON is passed to Python via env, not textual interpolation (a quote in a finding title no longer breaks the parse).
- **`scripts/detect_language.sh`** — single-quotes the text-mode `LANGUAGE`/`QUIRKS`/`EVIDENCE` values so SKILL.md's `eval "$(detect_language.sh …)"` is safe (a free-text `EVIDENCE=*.sol (no build config)` was a shell syntax error under eval).
- **`scripts/parse_findings.py`** — `LOC_RE` recognizes `.go`/`.vy`/`.huff` locations (L1 Go findings were silently dropped).
- **`scripts/score_benchmark.py`** — the finding regex accepts a class field as the last column (no trailing pipe required), so valid findings aren't miscounted as misses.
- **`scripts/selfcheck.sh`** — check 10 now honors `blind_benchmark.sh`'s exit code and fails on an empty stripped tree (it previously passed vacuously if the stripper crashed).
- **`prompts/phases/42_niche.md`, `prompts/phases/46_nemesis.md`** — added explicit `model=opus` (core/thorough) directives to the niche and nemesis sub-agent spawns. These dispatchers now run cheap while their recall-sensitive finding sub-agents stay premium; without the directive they would have inherited the cheap dispatcher tier (a regression the v1.24.0 tiering change would have introduced). The niche "none triggered" summary now carries the `NO-FINDINGS` sentinel.
- **`scripts/dewaxguard_driver.py`, `rules/model-tiering.md`** — `nemesis` is now a `sonnet` dispatcher (its passes are pinned opus in-prompt); the tiering doc records that every dispatcher must state its sub-agent tier explicitly.
- **`README.md`** — Supported Languages now lists Rust/Soroban (Stellar), C/C++, and Go/L1; added a Driver mode + model-tiering section.

## [1.24.0] - 2026-07-08

**Origin**: ClaudeDevs multi-model cost patterns (advisor / orchestrator — premium model only at decision points; cheaper models for the token-heavy bulk). dewaxguard already tiered finding sub-agents by phase but ran every driver subprocess at one uniform default model, so the "cheap executor" idea was unrealized at the phase level. This release adds per-phase subprocess tiering in the deterministic driver, split by role, with the finding agents deliberately left untouched (security auditing is recall-sensitive — the coding/research benchmarks those patterns come from are not). Methodology/mechanism only — no stored bug patterns.

### Added
- **`rules/model-tiering.md`** — the per-phase cost/recall policy: three tiers (worker `sonnet`/`haiku`, finding `opus`, commander `--commander-model`), how the ClaudeDevs advisor/orchestrator patterns map onto the pipeline, the recall caveat that keeps finding agents premium, and the do-nots. Documents that a phase subprocess model is independent of the `Task` sub-agent `model=` it spawns — the mechanism that lets dispatchers run cheap without touching recall.
- **`scripts/dewaxguard_driver.py`** — `--commander-model {sonnet,opus,fable}` (default `opus`) resolving the decision-gate tier; pass `fable` to run the bug-validator gate on Fable 5 (the ClaudeDevs "premium advisor at decision points" pattern) with no other Fable spend.

### Changed
- **`scripts/dewaxguard_driver.py`** — `Phase.model` per-phase tier added to the registry and passed as `--model` to each `claude -p` subprocess (was: no `--model`, uniform default). Workers/dispatchers → `sonnet`/`haiku` (preflight/bake `haiku`; recon/breadth/inventory/niche/depth/chain/report/verify `sonnet`); finding-tier in-subprocess `nemesis` → `opus`; validator → commander tier. Resolved model is recorded in the manifest, transcript header, and driver log lines. The finding sub-agents' `model=` literals in the phase prompts are unchanged, so recall is unaffected.
- **`prompts/phases/50_verify.md`**, **`prompts/phases/55_validator.md`** — header notes documenting each phase's tier (worker vs decision gate) and that it does its work in-subprocess (no sub-agent spawning).
- **`SKILL.md`** — Modes section notes the driver's per-phase tiering and the `--commander-model fable` advisor toggle.

## [1.23.0] - 2026-06-25

**Origin**: Field calibration from a live Cantina submission (Morpho Midnight) where 9/9 findings were rejected despite a standalone validator predicting 0 rejections. Root cause: the validator (and dewaxguard's Phase 5d gate) scored writeup quality, not bug reality — it had no by-design/source-NatSpec kill, no enabler-fabrication check, and no opted-in-disclosed-risk kill. This release ports those three checks from the bug-validator Reality Gate INTO dewaxguard's own end-of-pipeline gate, so the pipeline is self-sufficient (no separate bug-validator skill needed). Methodology only — no stored bug patterns.

### Changed
- **`references/judging.md`** — hardened the 4 gates: Gate 1 adds a **by-design / source-NatSpec kill** (explicit `"Reverts if X"` and documented-parameter-effect are specified behavior, not bugs; "no guardrail on a documented-effect param" is a doc note); Gate 2 adds **enabler verification** (reject preconditions that are caller-supplied or unverified against code); Gate 4 adds **opted-in disclosed-risk** (harm only to a voluntary participant in an immutable, permissionless, on-chain-visible market = no involuntary victim → reject, even if the loss is real). Added a header note: a single REJECT/DEMOTE is final — legitimacy ≠ submittability.
- **`SKILL.md` Phase 5d** — wired the three checks as HARD sub-gates 1c (source-NatSpec by-design kill), 2a (enabler verification), 4b (opted-in disclosed-risk), mirroring the existing 1a/1b/4a pattern.

## [1.22.0] - 2026-06-12

**Origin**: Direct follow-up to v1.21.0 ("improve this skill to ultimate and absolute peak optimal"). v1.21.0 built the honest-accuracy machinery and ran the first blind benchmark; that run flagged a +1 severity over-escalation at the breadth layer and two unmeasured language trees. This release closes the four remaining NOT_STARTED / PARTIAL items in the self-improvement plan (Tiers 2.5, 2.6, 3.7, 3.8, 3.9), fixes the flagged calibration bias at its source, and widens benchmark coverage from 3 to 5 language trees. Every change is methodology or mechanism — no stored bug patterns. `selfcheck.sh` is green (13 checks, up from 11).

### Added
- **`agents/methodology-adversary.md`** (Tier 3.7) — session-start template skeptic. After `match_methodologies.sh` fires templates by `trigger_grep`, this agent argues each FIRED code/artifact template does NOT apply here, using a structural-precondition test (a grep keyword is not the precondition), a provenance-mismatch test, and an anchoring-cost test. Emits KEEP / DEMOTE / KILL verdicts; the orchestrator loads only KEEP templates into breadth prompts. Pure subtraction step — never adds templates, cannot create new FP surface. Has an explicit anti-over-correction self-check (must KEEP ≥1 highest-provenance template; a KILL without a named absent-precondition downgrades to DEMOTE).
- **`failure-modes/INDEX.md`** (Tier 3.9) — class-level miss ledger, populated by `/dewaxguard improve` Phase E for every fix-eligible (non-RC-AGENT) miss. Generic class + language + root cause + the fix that shipped — never titles/locations/protocol names (no anchoring). Aggregation rule drives "what template next": class count ≥3 same-language overrides the RC-NOVEL wait-gate; count ≥2 cross-language → generalize the owning M-template. Seeded with FM-01..FM-05 from the Sherlock 1260 and benchmark post-mortems. 40-row cap with a close-the-gap archival rule.
- **`scripts/detect_language.sh`** (Tier 3.8) — deterministic language + platform-quirks resolution. Maps build files → LANGUAGE → the exact `platform-quirks/{lang}.md` the orchestrator must pass to every agent, replacing "load if Claude remembers" (the silent-miss risk that ships Soroban archive-restore false positives when stellar.md isn't loaded). Evidence-ordered (soroban-sdk-no-anchor ≠ generic Solana; Anchor ≠ bare Rust), emits an `l1_candidate` signal. `--json` output. Verified on all benchmark trees.
- **`scripts/run_benchmarks.sh`** (Tier 2.5) — end-to-end blind regression harness wrapping `blind_benchmark.sh` + `score_benchmark.py` into one runner with three modes: `--prep` (blind copies + per-benchmark language + run plan), `--score DIR` (aggregate recall / trap-precision / per-finding severity-delta across all benchmarks into one results markdown, CI-gateable), `--check` (mechanical leak gate). Closes the loop the plan flagged: prep and scoring were two disconnected manual steps with no aggregation.
- **`benchmarks/aptos/auth-arg-confusion/`** — first Aptos benchmark. `withdraw()` authorizes against a caller-supplied `claimed_owner` argument instead of the transaction signer (any attacker drains any vault); FP trap = a `#[view] balance()` accessor. Seeded High, access-control.
- **`benchmarks/stellar/missing-require-auth/`** — first Stellar/Soroban benchmark. `transfer()` debits `from` without `from.require_auth()` (any caller moves any balance); FP trap + inconsistency precedent = sibling `burn()` that correctly calls `require_auth()`. Seeded High, access-control. Deliberately NOT an archive-restore shape (that's the known Soroban FP class, covered by `platform-quirks/stellar.md` #1).

### Changed
- **`agents/hacking-agents/shared-rules.md`** — added a compact **"Severity self-calibration"** section (the v1.21.0 benchmark fix, FM-05). Breadth agents now DERIVE `severity:` in two mechanical steps (pick impact×likelihood axes → read the matrix; Critical needs BOTH High impact AND High likelihood) instead of reflex-tagging any drainable function Critical, do NOT pre-apply downgrade modifiers (Phase 5d owns those — pre-applying double-counts), and sandbag on ties (under-rating is re-scored cheaply; over-rating burns a verification slot). Teaches HOW to set severity, not WHAT to find.
- **`scripts/selfcheck.sh`** — now 13 checks (was 11). Added #12 cross-language enforcement (Tier 2.6 — every multi-language code-triggered M-template must carry a cross-language section; single-language like M-29 [evm] exempt) and #13 v1.22.0 component presence + executability.
- **`benchmarks/manifest.json`** — 6 → 8 benchmarks (added aptos + stellar). 5 of 6 language trees now have ≥1 benchmark (C/C++ remains the only unmeasured tree).

### Self-improvement plan status (`improve/SELF-IMPROVEMENT-PLAN-2026-04.md`)
- 2.5 Wire up evals → **SHIPPED** (`run_benchmarks.sh`); 2.6 cross-language enforcement → **SHIPPED** (selfcheck #12); 3.7 adversarial methodology-skeptic → **SHIPPED**; 3.8 per-language quirks auto-detect → **SHIPPED** (`detect_language.sh`); 3.9 failure-mode database → **SHIPPED**. Tiers 1-3 of the plan are now fully shipped; remaining open work is corpus growth (C/C++ benchmark) and the Tier 4 "hard truths" (template pruning, which is ongoing not a one-shot).

## [1.21.0] - 2026-06-12

**Origin**: Follow-up to v1.20.0 in the same skill-improvement session — the user asked to "make sure or find a way for this skill to be thorough and 100% accurate." Rather than assert an unverifiable "100%", this release (a) states honestly that no LLM auditor can guarantee 100% recall or precision and why, (b) builds the machinery that maximizes accuracy and measures the residual, and (c) actually runs the measurement and acts on what it found. A blind breadth-pass benchmark run (6 contracts, answer-stripped) scored 6/6 recall, 5/6 trap precision — and surfaced three real problems, all fixed below.

### Added
- **`ACCURACY.md`** — the honest accuracy contract: why 100% is unachievable (open-ended reasoning, no enumerable bug oracle; the Sherlock 1260 0%-H/C-recall event as standing proof), what the skill's recall/precision/consistency maximizers actually are, how accuracy is *measured* not asserted, and the banned anti-patterns (auditing leaked benchmarks, editing oracles to match output).
- **`scripts/selfcheck.sh`** — mechanical skill-integrity gate. 11 checks: version sync (VERSION/SKILL.md/CHANGELOG), methodology registry bidirectional + links, trigger-frontmatter validity (ERE compiles, no brace-globs, no double-backslash), SKILL.md path references resolve, pattern-library links, criteria files present, script syntax, benchmark manifest + ground-truth parse, refuted index, blind-stripper leak guard, disputed-oracle review-note guard. This is the one place "100%" is the right word — internal consistency is enforced by a script, held green this release.
- **`scripts/blind_benchmark.sh`** — produces answer-blind benchmark copies (strips every comment, refuses to copy `ground-truth.json`). Fixes a latent measurement bug: the committed benchmark sources carry `// VULNERABLE:` answer comments, so every prior "benchmark" run was scored against a leaked answer key.
- **`scripts/score_benchmark.py`** — mechanical scorer: parses `FINDING |` lines, computes must_detect recall (range-overlap + class-token match), false-positive-trap precision (midpoint-in-window, so a real finding abutting a safe function doesn't phantom-trigger), and per-finding severity delta. Respects `must_detect:false`/`disputed` oracle entries. CI-gateable (exit 0 iff recall 100% and no trap triggered).
- **`platform-quirks/sui.md`** — first real Sui quirks file (was a stub reference). Lead quirk: shared-object access is consensus-serialized, so EVM-style lost-update races on shared objects are invalid findings; plus owned-object auth, `key` vs `key+store`, hot-potato, OTW, and Move abort-not-wrap arithmetic — each with an "invalid finding pattern → reframe as" row.
- **`refuted/INDEX.md` RF-12** — EVM-style lost-update race on a Sui/Move shared-object field (refuted: consensus serialization), with the re-check precondition (same-tx = atomic; cross-tx = staleness; non-serialized runtime = LIVE) and the equivocation/liveness caveat.
- **`benchmarks/results/v1.21.0_2026-06-12.md`** — the baseline run with full caveats (single breadth pass, sonnet, toy contracts; Aptos/Stellar/C++ trees unmeasured).

### Changed
- **`benchmarks/sui/shared-object-race/ground-truth.json`** — corrected oracle. The original sole finding asserted an EVM-style "concurrent read-then-write race"; that cannot occur on Sui (consensus serializes shared-object txns). The blind breadth agent correctly refused to report it and instead found a real bug the oracle missed (accumulated `Balance<SUI>` has no withdraw/claim path → permanent fund lock). The real fund-lock is now `must_detect:true`; the disputed race is retained `must_detect:false, disputed:true` with an `_oracle_review` provenance note. This is an oracle *correction* (independently verifiable by reading the file), explicitly NOT metric-coaching.
- **`improve/BENCHMARK.md`** — new MANDATORY "run BLIND" section wiring `blind_benchmark.sh` + `score_benchmark.py` into the benchmark flow, plus the two banned anti-patterns.
- **`VERSION`** → 1.21.0.

### Measured, not changed (flagged for monitoring)
- **Breadth agents over-escalate severity** (+1 tier on 4/6 benchmarks). On single-function toy contracts a full drain is arguably Critical, so part of the gap is benchmark conservatism — but the consistent upward bias is real and is what the downstream realism-filter + severity-decision-tree (Phase 5d) exist to correct. No change made; left as a calibration signal in the results file.
- **Coverage gap**: no Aptos/Stellar/C++ benchmark exists; those trees are unmeasured.

## [1.20.0] - 2026-06-12

**Origin**: Skill-improvement session ("improve this skill in terms of smartness and accuracy"). Ships the three highest-leverage NOT_STARTED items from `improve/SELF-IMPROVEMENT-PLAN-2026-04.md` — Tier 1 #2 (trigger-pattern matching), Tier 1 #3 (negative-results retrieval), and Tier 2 #4 (mandatory Phase A retrospective — the plan's own "single highest-leverage gap; without it the system is open-loop and everything else is theater") — plus registry/doc accuracy bugs found during a full consistency audit of the skill.

### Added
- **`trigger_*` YAML frontmatter on all 25 methodology templates** (M-03..M-30): `trigger_type: code|artifact|process`, `trigger_grep` (cross-language POSIX ERE) / `trigger_glob` / `trigger_event`, `trigger_languages`, `applies_to_protocol_types`, and `recon_flags` where `build_recon_maps.sh` detectors already exist (M-29, M-30). Every code pattern was validated to fire on the template's own validated-origin codebase tokens.
- **`scripts/match_methodologies.sh`** — preflight Step 3 matcher. Parses the frontmatter, greps the audit target (code-type), checks artifact globs, and emits `$SCRATCHPAD/applicable-methodologies.md` with FIRED / process-checklist / not-fired / language-skipped sections. Smoke-tested: the share-inflation benchmark fires M-09; a synthetic escrow+permit+setter contract fires M-03/M-08/M-17/M-30; `--lang solana` correctly skips the evm-only M-29.
- **`refuted/INDEX.md`** (Tier 1 #3) — cross-audit refuted vulnerability classes **RF-01..RF-11**, each with a mandatory structural-reason + re-check-precondition format (a refutation transfers ONLY if its structural reason holds in the new target), an anti-anchoring rule, and an amendment rule. RF-03 ("read-only RPC immune") is the canonical narrowed-after-counterexample entry, amended per Sherlock 1260 F39.
- **SKILL.md `POST-AUDIT: PHASE A RETROSPECTIVE GATE`** (Tier 2 #4) — an audit does not close until outcomes are compared against ground truth via `/dewaxguard improve`, or a `DEFERRED (results expected ~date)` row is logged to MEMORY.md as a standing obligation.

### Changed
- **SKILL.md preflight** — Step 2 item 9 (`refuted/INDEX.md`) and Step 3 (matcher invocation) are now live instead of "when Tier 1 #N ships"; the self-check gains two boxes.
- **`prompts/phases/00_preflight.md`** (driver mode, kept in sync) — STEP 1c adds `refuted/INDEX.md`; new STEP 3.5 runs the matcher after language detection; output template + self-check extended.
- **`methodology/INDEX.md`** — registered the previously-MISSING **M-13** and **M-14** rows. Both files existed since 2026-04 but were absent from the registry the preflight reads, so they could never be surfaced. "How to use" gains step 0 (run the matcher).
- **`methodology/M09-sync-gap-detection.md`** — trigger pattern extended with standard DeFi aggregate vocabulary (`totalShares|totalAssets|totalBorrows|totalDebt|totalDeposits|totalBonded|totalLocked`) after the share-inflation benchmark exposed a recall gap in the initial pattern.
- **MEMORY.md** — added the missing Sherlock 1260 post-mortem metrics row (0% H/C recall, 5/9 valid, RC = 3 METHOD / 2 DEPTH / 4 AGENT) and a 1.18.0 summary paragraph; the ledger previously stopped at 1.10.1.
- **SKILL.md accuracy fixes** — banner version was stale at v1.0.0; Phase 4a breadth-count wording (8 core / 13 thorough); FILE STRUCTURE rewritten to match the actual repo (was missing `methodology/`, `refuted/`, `patterns/`, `platform-quirks/`, `contest/`, `LEARNED_INDEX.md`, `prompts/phases/`, `prompts/{stellar,cpp}/`, `agents/l1/`, 9 rules files, and 8 scripts).
- **`improve/SELF-IMPROVEMENT-PLAN-2026-04.md`** — status table updated: 1.2 / 1.3 / 2.4 → SHIPPED (v1.20.0); 2.6 → PARTIAL (frontmatter `applies_to` half shipped); 2.5 annotated with existing partial coverage.
- **`VERSION`** → 1.20.0.

## [1.19.1] - 2026-06-05

**Origin**: User triage directive during the Polymarket CTF Exchange v2 bounty review. Finding M-02 (self-pause kill-switch keyed to the EOA via `pauseUser()` but validated against `order.maker`, so it is inert for POLY_PROXY/POLY_GNOSIS_SAFE makers) is real and has a passing Polygon mainnet-fork PoC (a live operator `matchOrders` settles the paused proxy user's order), but its entire attack path is gated on the victim's own signer key being compromised. That class is an out-of-scope auto-invalidator on virtually every bug-bounty program, yet `references/criteria/cantina.md` had no such rule and the realism filter had no tag for it — so the pipeline could waste a verification / bug-validator pass before concluding "invalid". This closes the gap as a discovery-time filter so the class is rejected up front, no validator pass needed.

### Added
- **`rules/realism-filter.md` — new filter value `compromised-key`** (REJECT). Any exploit chain whose precondition includes a leaked / phished / compromised private key (victim user EOA, admin, or operator) is rejected at discovery (Phase 5d, before the severity-decision-tree), surfaced as Informational at most, with no PoC / bug-validator spend. Wired into the Filter Values table, the decision tree (new step 0, runs first), the output-format enum, and the mechanical-enforcement list (new rule 5). Holds even when the bug is a safety feature *designed* for the post-compromise scenario (e.g. a mis-keyed self-pause kill-switch).
- **`references/criteria/cantina.md` — new invalidator `AI-11`**: "Requires a compromised / leaked / phished private key (user, admin, or operator) → INVALID / out-of-scope." Brings Cantina in line with `c4-bounty.md` (AI-2), `immunefi.md`, and `c4-competitive.md` (AI-13), which already encode this exclusion.

### Changed
- **`VERSION`** → 1.19.1.

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
