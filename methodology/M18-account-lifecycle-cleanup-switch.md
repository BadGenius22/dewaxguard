# M-18 — Account-Lifecycle Cleanup-Switch Completeness Matrix

> **Cross-language methodology for auditing account/object lifecycle close operations.**
>
> **Origin**: XRPL Domain 18 full 8-agent breadth (2026-04-25; AccountDelete × new-SLE matrix).
> **Validated**: ~28 cells populated; 0 Medium+ submissions; 1 contested Low post-arbitration; 4 known kuprum issues all surface as predicted by matrix.
> **Trigger**: Audit any protocol that has account/object lifecycle close operations gated on "no obligations" check.

---

## When to apply M-18

Apply this methodology whenever the protocol has:
- An account/contract closure operation: `AccountDelete` (XRPL), `selfdestruct` (EVM, deprecated), `close` instruction (Solana), `object::delete` (Sui), `move_from` (Aptos), `keeper.Delete()` (Cosmos).
- **ANY object-level teardown / delete operation — not just account-level closure.** Enumerate EVERY destroyable object's teardown op and run the matrix per op: AMM delete, Vault delete, LoanBroker delete, pool/market close, token-issuance destroy, position close. *(Sherlock 1260 post-mortem: M-18 was applied to `AccountDelete` only and missed **F13** — High, 19 finders — attacker blocks AMM/Vault/LoanBroker teardown and forces repeated deletion failures. The teardown-griefing shape lives on every deletable object, not just accounts.)*
- The closure is gated on a "no obligations" / "no held state" check.
- New state-object types are introduced (or extended) in the audit delta.

The yield correlates with: how many NEW state-object types were added; how unilateral their creation is (creator-self vs counterparty-required vs unilateral-against-victim); how the cleanup switch handles unhandled types (block-by-default vs cascade-default vs silent-orphan).

---

## Phase 0 — Inventory (mandatory pre-read)

Before writing any matrix cells, build these inventories:

0. **Teardown-operation roster (mandatory first)** — list EVERY object-teardown / close / delete operation in scope, not just the account-level one. For each (AccountDelete, AMM delete, Vault delete, LoanBroker delete, IssuanceDestroy, position/market close), run Phases 0–2 of this matrix. The **shared-object grief variant** (Sherlock 1260 **F13**): an attacker plants state on a SHARED / pooled object (AMM / Vault / Broker) that the OWNER must tear down — the owner can never complete teardown because the planted state is a permanent obligation. This is distinct from account-level AccountDelete and is the higher-yield variant on pooled objects.

1. **The closure operation file** — read end-to-end. Identify:
   - Pre-conditions (who is allowed to close; what blocks closing).
   - The cleanup switch / dispatch table (one entry per per-state-type cleanup helper).
   - The default fall-through behavior.
   - The post-cleanup invariant(s) (orphan walks, balance assertions).

2. **The new state-object-type inventory** — list every new type added in delta:
   - Type identifier (XRPL `lt*` enum; EVM contract address-set; Solana account discriminator; Sui object type-tag; Aptos struct).
   - Owner/creator field(s) — single-AccountID or multi-AccountID?
   - Owner-directory linking discipline — primary owner only or both parties?

3. **The dormancy / time-lock window** — does the closure require a quiescent period? How is the timer reset?

4. **The known-issue baseline** — search the bug-tracker / kuprum-equivalent for `<closure-operation>` AND `<new-type>` references.

---

## Phase 1 — Build the matrix

For every NEW state-object type × held-state combination, fill ONE matrix cell:

| Coordinate | Description |
|---|---|
| **State-object type** | The new type (e.g. `ltSPONSORSHIP`, ERC-6900 plugin, Solana derived-PDA) |
| **Side-of-relationship** | If type has multiple parties: enumerate each side (sponsor / sponsee, delegator / delegatee, issuer / subject) |
| **Held-state** | Active / quiescent / dormant / pending-tx-in-queue / orphan-after-related-deletion |
| **Cleanup-coverage** | Switch-case explicit / default-fall-through-block / default-fall-through-cascade / silent-orphan |
| **Adversarial-creation surface** | Self-signed only / bilateral-required / unilateral-by-other-party / external-event |
| **Verdict** | VERIFIED-safe / KNOWN-ISSUE / CONFIRMED-bug / DEFENSE-IN-DEPTH-gap / OOS-LEGACY |

### The 8 audit dimensions per cell

1. **Switch-completeness**: Is the new type explicitly handled in the cleanup switch? What does the default fall-through do? **The default IS a policy decision** — silent-orphan is the worst; block-with-informative-error is the safest; cascade-by-default is dangerous if creator's intent isn't preserved.

2. **Block vs cascade vs orphan choice**: Match against the spec/intent. If spec says "creator paid the reserve, creator's intent prevails" → block-by-default. If spec says "the close-operation is destructive of dependent state" → cascade. **Silent-orphan is never the right choice.**

3. **Dual owner-dir linking**: When the SLE has two AccountID parties, both owner directories MUST be linked. If only one side is linked, the other side's closure won't see the SLE in the owner-dir walk → may proceed → silent-orphan.

4. **Reserve refund symmetry across both parties**: Cascade-deletion must refund the reserve to the ORIGINAL payer (typically tracked via a sponsor-aware accounting helper), not the destroyer. Both sides of a bilateral-creation must have correct refund accounting.

5. **Dormancy / time-lock window** (composition aggravator class): Can an adversary re-create an obligation during the dormancy window to extend the lockup? If the cleanup transaction by the victim resets the dormancy clock, the attacker can grief indefinitely at low cost. **Document the dormancy semantics explicitly.**

6. **Post-cleanup invariant coverage**: Does any walk-and-check invariant catch orphan references? Most lifecycle invariants only check single-AccountID-keyed state types (XRPL `directAccountKeylets` is a 6-element hard-coded array). Multi-AccountID-keyed state types depend entirely on the owner-dir walk discipline + per-writer secondary-dir-link discipline.

7. **Test coverage**: Are adversarial scenarios (especially timing attacks during dormancy) tested for every new state-object type? Zero test coverage for new types is a CI hardening gap.

8. **RPC observability**: Do RPC handlers consistently report deletion blockers to UIs? Drift between the actual cleanup switch and the RPC-exposed blocker list creates UX bugs (wallet UIs misreport "what's preventing closure").

---

## Phase 2 — Anti-patterns to flag

For each cell, classify into one of 4 tiers (D-47 in M-18 source):

| Tier | Adversarial creation? | Cleanup coverage? | Architectural verdict |
|---|---|---|---|
| **A** | NO (self-signed only) | Block-by-default OR cascade | SAFE — best practice |
| **B** | YES (bidirectional dir-insert with consent) | Cascade via switch | SAFE — switch must be exhaustive |
| **C** | YES (unilateral insert, but creator pays reserve) | Cascade via switch | SAFE — but creator pays reserve, victim doesn't |
| **D** | YES (unilateral insert) | Block-by-default (no cascade) | **UNSAFE** — kuprum #6892 anti-pattern |

**Tier-D is the canonical bug class.** Every new state-object type in tier D is a candidate AccountDelete-DoS bug. Cross-language examples of tier-D anti-pattern:

- XRPL: `ltSPONSORSHIP` (sponsor unilaterally creates; sponsee must pay tx fees per SLE for cleanup before AccountDelete) — kuprum #6892.
- EVM: ERC-2771 meta-tx forwarder unilateral state-injection without target consent + default-revert on `selfdestruct` if any leftover state (rare; modern EVM avoids this via no auto-cleanup).
- Solana: Third-party-creatable PDAs in target's owned-list without close-handler — close instruction may revert.
- Sui: Shared-object capability inserted into target's address dynamic-field without consent + immutable shared-object can't be cleaned up.
- Aptos: Resource published into target's account via `signer::create_signer_with_capability` without consent (rare but possible with specific designs).

### Other anti-patterns to flag

- **New SLE type added without updating cleanup switch** (kuprum #6892 archetype). Tier-D verdict.
- **Single-side owner-dir linking when SLE has two parties** (legacy ltDELEGATE pre-`sfDestinationNode` archetype). Causes silent-orphan when one side closes.
- **Dormancy clock reset on cleanup tx** (composition with cleanup-blocker = permanent lockup). Aggravator class.
- **Block-by-default with unhelpful TER** (`tecINTERNAL` instead of `tecHAS_OBLIGATIONS`). User can't diagnose; observability defect.
- **Orphan-detection invariant only walks fixed keylet array, missing multi-AccountID SLEs** (XRPL `directAccountKeylets` blind spot). Defense-in-depth gap.
- **Confidential/encrypted residue not removed on drain-to-zero** (D-50 family — F-16 in XRPL). Field-presence-vs-value asymmetry creates 4-instance bug family at preclaim layer (over-block AND under-block directions).

---

## Phase 3 — Cross-agent contradiction handling (mandatory protocol)

> **The highest-value methodology contribution from XRPL Domain 18.** Codified into M-18 as a sub-methodology after the VS18-3 vs ECS18-1 arbitration.

When two breadth agents return opposite verdicts (REFUTED vs CONFIRMED) on the same surface, citing different code locations:

1. **Diagnose**: At least one agent has performed citation-without-end-to-end-read (cited a specific line range without reading the rest of the relevant branch).

2. **Resolution protocol**:
   - The merge orchestrator MUST read source code directly with both versions side-by-side (current + previous, if delta-audit).
   - The merge orchestrator MUST NOT rely on either agent's citation as authoritative.
   - The merge orchestrator MUST trace the disputed scenario step-by-step through the actual code.
   - The arbitration verdict MUST be documented prominently with line-numbered code snippets from BOTH versions.

3. **Outcome documentation**:
   - The losing agent's verdict is overridden.
   - The winning agent's finding stands.
   - A new framework fact codifying the actual behavior is added to the manifest.
   - The arbitration protocol is reinforced in the methodology.

**Concrete validation (XRPL Domain 18)**: Vector Scan VS18-3 REFUTED "confidential MPT residue blocks holder AccountDelete" citing `MPTokenAuthorize.cpp:44-48`. Economic Security ECS18-1 CONFIRMED the same surface citing `MPTokenAuthorize.cpp:78-95`. Merge orchestrator read both versions of the file end-to-end:
- `rippled-prev/.../MPTokenAuthorize.cpp` — preclaim `tfMPTUnauthorize` branch ENDS at line 78 with `return tesSUCCESS;`.
- `rippled/.../MPTokenAuthorize.cpp` — preclaim `tfMPTUnauthorize` branch contains the NEW confidential block at lines 78-95 BEFORE returning at line 97.

Lines 78-95 are INDISPUTABLY NEW in the audit delta. ECS18-1 wins. VS18-3 was wrong. Codified into manifest as F-53 (framework fact).

---

## Cross-language ordering mechanisms

Who can race the cleanup vs the obligation creation:

| Platform | Ordering mechanism | Race surface |
|---|---|---|
| XRPL | CanonicalTXSet ordering (AccountID XOR parentHash; seqProxy secondary; txId tertiary). Same-account = deterministic by seqProxy. Cross-account = pH-seeded random. Batch inner-tx order = attacker-controlled via `sfRawTransactions` array. | Sponsor can race victim's AccountDelete by submitting `SponsorshipSet` immediately before. |
| EVM | Block-builder mempool ordering. MEV-boost / Flashbots bundles. EIP-7702 set-code authority. | Adversary can race target's `selfdestruct` (deprecated) via private mempool front-run. |
| Solana | Slot-based ordering. Jito bundle priority. Instruction-array order within a tx. | Cross-program close races via CPI ordering. |
| Sui | PTB (Programmable Transaction Block) per-tx atomic ordering. Validator-determined inter-tx ordering. | PTB ordering is fully deterministic within a single tx. |
| Aptos | Block-stm parallel execution + sequence-number-based ordering. | Sequence-number gates same-account ordering; cross-account is parallel. |

---

## Cross-language examples

### XRPL AccountDelete (this audit's validation)

- `nonObligationDeleter` switch + `directAccountKeylets` walk + 256-ledger dormancy.
- 9 explicit cases (cascade-delete with sponsor-aware refund per F-11).
- `default: return nullptr` ⇒ `tecHAS_OBLIGATIONS` (informative TER).
- New ac4f142 SLE types: `ltSPONSORSHIP` (tier-D anti-pattern, kuprum #6892), `ltVAULT` (tier-A), `ltLOAN_BROKER` (tier-A), `ltLOAN` (tier-A), `ltDELEGATE` (tier-B, correctly handled).

### EVM `selfdestruct` (deprecated EIP-6049)

- Historical pattern with destroyed-contract reentry race.
- Modern EVM (post-Shanghai) effectively no-ops `selfdestruct` for new contracts; only legacy contracts can self-destruct.
- For ERC-6900 plugin uninstall: similar matrix — does the plugin-registry have a `default: revert` for unregistered plugin types? Are plugin-stored values (mappings) safely cleared?
- **Anti-pattern**: contract holding state for the destructing contract is orphaned (no `delete` on the storage by default).

### Solana `close` instruction

- Lamport recovery + account zeroing + reentrancy considerations.
- Per-program close-handler is the analog of XRPL's `nonObligationDeleter` cleanup helpers.
- **Anti-pattern**: third-party-creatable PDA in the closing account's owned-list without a close-handler that the closing tx can invoke → close fails silently or unexpectedly orphans state.

### Sui `object::delete` with `key + store` ability

- Cascade rules: object with `store` ability can be wrapped/embedded in other objects → deleting the wrapping object cascades to the wrapped.
- Shared-objects can be touched by anyone — UNILATERAL state-injection during owner's pre-delete preparation could analogously block deletion.
- **Anti-pattern**: object with `key + store` referenced via dynamic-field on the closing account but lacking a cascade-delete handler.

### Aptos resource destruction with `move_from`

- Resource lifecycle owner-bounded but events/notifications can pile up.
- Capabilities revocation must be explicit — destroying a `ResourceAccount` requires manual capability cleanup.
- **Anti-pattern**: pending coin-store at `move_from` time → revert.

### Cosmos `keeper.Delete()` patterns

- Account pruning + staking-delegation cleanup.
- **Anti-pattern**: AccountDelete with active delegation → may revert or silently leave delegation orphaned.

---

## Validated findings

XRPL Domain 18 (2026-04-25):

| Cell | Verdict | Cross-ref |
|---|---|---|
| `ltSPONSORSHIP × sponsee × active` (tier-D anti-pattern) | KNOWN-ISSUE kuprum #6892 (5-way agent concurrence) | VS18-1, ET18-1, AC18-1, F18-INV-7, F-FP-1 |
| `ltDELEGATE × delegatee × active` (tier-B, cascade-correct) | VERIFIED safe (with informational silent-revoke UX side-effect ET18-2) | AC18 §1.a, ET18 §2.3 |
| `ltLOAN × borrower` (tier-A, bilateral signature required) | VERIFIED safe (closes VS18-2 / L-46) | AC18-2, ET18 §2.5, F-FP-3 |
| `ltMPTOKEN × confidential-residue × COA > 0 × Unauthorize` | CONFIRMED soft-lockup ECS18-1 (Low; HOLD per T-13; **post-arbitration win over VS18-3 incorrect REFUTAL**) | ECS18-1, F-53, D-50 |
| 256-ledger dormancy + ltSPONSORSHIP composition | REFUTED-DUPLICATE per CONTEST_FAQ §Known-issue (root cause is kuprum #6892) | AC18-1, ET18-5, F-FP-1 |
| `AccountRootsDeletedClean` walks 6 singleton keylets only (multi-AccountID SLE blind spot) | DEFENSE-IN-DEPTH gap (no current exploit; methodology contribution) | F18-INV-1, L-48 |
| `account_objects?deletion_blockers_only=true` filter omits ltLOAN_BROKER/ltLOAN/ltAMM | RPC-only HOLD (CONTEST_FAQ empty-feature-label invalid risk) | F-PER-1 |

**Negative-result methodology multiplier**: 0 Medium+ submissions but 8 cross-language meta-patterns validated against concrete code; arbitration protocol codified; D-50 unifies CONF-1/kuprum#6869/kuprum#6887/ECS18-1 into single F-16 family.

---

## Anti-patterns to flag

When auditing any new state-object type in any chain, ABORT-AND-FILE if:

- New SLE type added without updating cleanup switch → **tier-D anti-pattern** (kuprum #6892 archetype).
- Single-side owner-dir linking when SLE has two parties → silent-orphan when other side closes.
- Dormancy-clock reset on cleanup tx → composition with cleanup-blocker = permanent lockup.
- Block-by-default with unhelpful TER (`tecINTERNAL` instead of `tecHAS_OBLIGATIONS`) → observability defect.
- Orphan-detection invariant only walks fixed keylet array, missing multi-AccountID SLEs → defense-in-depth gap.
- Confidential/encrypted residue not removed on drain-to-zero → field-presence-vs-value asymmetry (D-50 family).
- Cascade-deletion that refunds the destroyer instead of original payer → reserve-recovery accounting bug.
- Cross-agent contradiction on a surface NOT resolved via direct source-code arbitration → methodology violation.

---

## How to use M-18 (workflow)

1. **Phase 0** (mandatory): inventory closure operation + new types + dormancy + known issues.
2. **Phase 1**: build matrix for every new type × side-of-relationship × held-state. Fill 8 dimensions per cell.
3. **Phase 2**: classify each cell into tier A/B/C/D. Tier-D cells are bug candidates.
4. **Phase 3**: if cross-agent contradictions arise during merge, apply mandatory source-code arbitration protocol.

Total effort per audit: ~28 cells × 5 minutes per cell = ~2.5 hours of merge work after the 8-agent breadth completes.

---

## Maturity

- **Validated audits**: 1 (XRPL Domain 18, 2026-04-25)
- **Cells populated**: ~28
- **Confirmed findings**: 1 contested Low post-arbitration (ECS18-1)
- **Known-issue dedups successful**: 4 (kuprum #6889, #6892, #6893, #6900 all surface as predicted by the matrix)
- **Cross-language meta-patterns**: 8

Re-validate on next chain with closure operations: EVM (`selfdestruct` + ERC-6900), Solana (`close` instruction), Sui (`object::delete`), Aptos (`move_from`), Cosmos (`keeper.Delete`).
