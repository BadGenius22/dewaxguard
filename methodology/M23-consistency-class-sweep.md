# M-23 — Consistency-Class Sweep

> **Origin**: K2 Lending Protocol audit (2026-04-17 → 2026-05-27, Code4rena Stellar Soroban). 8 of 9 Lows + 4 of 5 Info findings followed this pattern across 8 audit passes (~89% of all findings).
>
> **Trigger**: Aave V3 forks, OR any protocol with ≥3 instances of the same defensive macro/check/convention. Specifically applicable when the codebase contains explicit comments like *"always round up to favor protocol"*, *"more accurate than subtraction"*, or *"consistent with regular flash loan premium"* — these comments mark a documented convention whose outliers are bug candidates.
>
> **Yield class**: Low / Info (rarely Medium). High volume, low individual severity, mechanical fix.

---

## The Pattern

K2 produced 14 findings in this class. Each has the same shape:

1. The protocol implements the same defensive convention in N call sites (N ≥ 3)
2. One or two outliers silently omit the convention
3. The fix is a one-line mechanical alignment (replace one helper with another, add one missing check)
4. No fund-loss exploit; the impact is **invariant break** or **off-chain integrator confusion**

K2 examples:
- **QA-L01**: per-asset pause re-check on both reserves (`prepare_liquidation:532-537`) — `execute_liquidation:711` + 2 callback layers omit collateral pause
- **QA-L02**: hard treasury revert when unset (`flash_loan.rs:52`) — flash-liquidation path uses soft `if let Some(treasury)` instead
- **QA-L03**: `percent_mul_up` for protocol fees (3 sites) — `swap.rs:197` uses `percent_mul` (HALF-UP)
- **QA-L04**: `MAX_USER_RESERVES` count guard (5 sites) — `set_user_use_reserve_as_coll(true)` + `swap_collateral` skip the guard
- **QA-L05**: reward-index flush before config mutation (`set_emission_per_second:619-643`) — `set_distribution_end` + `remove_asset_reward` skip the flush
- **QA-L06**: dynamic close-factor logic (`liquidation.rs:12-39`) — `flash-liquidation-helper::validate` hardcodes 50%
- **QA-L07**: `effective_collateral_removed` for fee + emit consistency — `LiquidationCallEvent` on niche branch over-reports
- **QA-L08**: scaled-balance return value for bit-clear (`swap.rs:323-326`) — withdraw + repay + 2 liquidation sites use subtraction-based remainder
- **QA-L09**: configurable `get_health_factor_liquidation_threshold` — `set_user_use_reserve_as_coll(false)` + `calculate_swap_health_factor` hardcode `1e18`

---

## When to Apply

| Trigger | Action |
|---------|--------|
| Repo is a fork of Aave V3, Compound, MakerDAO, or another battle-tested protocol | Mandatory — run early in Phase 3 breadth |
| Codebase has explicit comments documenting a defensive convention | Mandatory — the comments are the convention catalog |
| Codebase has ≥2 helpers with similar names but different rounding/error handling (e.g., `percent_mul` vs `percent_mul_up`) | Mandatory |
| Codebase has ≤2 entry points and no shared helpers | SKIP — yield will be near-zero |

---

## Process

### Phase 1: Convention Catalog Build (orchestrator inline)

For the audit codebase, build a catalog of defensive conventions. Each entry has:
- **Convention name** (e.g., "round protocol fees up")
- **Canonical helper or pattern** (e.g., `percent_mul_up`)
- **Documented intent source** (a code comment or doc reference)
- **All call sites** (grep-derived list)

Example catalog row from K2:
```
Convention: "Round protocol fees in protocol's favor (always up)"
Canonical: percent_mul_up (shared/utils.rs:131)
Intent source: flash_loan.rs:492 comment "L-10: round fee UP to favor protocol"
All sites:
  - liquidation.rs:358 (uses percent_mul_up) ✓
  - flash_loan.rs:86  (uses percent_mul_up) ✓
  - flash_loan.rs:492 (uses percent_mul_up) ✓
  - swap.rs:197       (uses percent_mul) ✗ ← OUTLIER
```

### Phase 2: Outlier Detection

For each convention, identify call sites that don't use the canonical pattern. The outlier set IS the candidate finding set.

Each outlier becomes a candidate Low or Info, with:
- Same severity tier across all outliers in one convention (consistency)
- Title format: `"<Function/Site> <breaks convention X by using Y instead of Z>"`
- Description: cite the inconsistency precedent line and the outlier line

### Phase 3: Realism Filter (per `rules/realism-filter.md`)

Each candidate must pass:
- **Permissionless trigger** OR clearly user-impacting at semi-trusted boundary
- **NOT marked "by design"** in docs
- **NOT a known issue** (per M-10 dedup)

Outliers that fail the realism filter go to ADDITIONAL_LEADS, not QA-Bundle.

### Phase 4: Severity Assignment

Default severity for consistency-class findings:
- **Low** if the convention is documented (comment, naming, doc)
- **Informational** if the convention is implicit (pattern repetition without explicit doc)
- **Medium** ONLY if the outlier produces fund loss with permissionless trigger AND the canonical pattern was specifically a security fix (e.g., a known-CVE patch). This case is rare.

### Phase 5: QA-Bundle Routing

Per Code4rena submission rules: consistency-class findings consolidate into a single QA-Bundle.md file with `[QA-Lxx]` IDs. Do NOT split into per-finding submission files.

---

## Cross-Language Mapping

| Language | Common Conventions to Sweep |
|----------|----------------------------|
| Solidity / EVM | `SafeERC20.safeTransfer` vs raw `transfer`; `OpenZeppelin.AccessControl` vs custom auth; rounding helpers (`mulDiv` ceiling vs floor); event emission for setters; `_requireNotPaused` re-checks at callbacks |
| Rust / Solana | `try_from` vs `as` narrowing; `Account::pack` vs raw `BorshSerialize`; `ProgramError` mapping consistency; `Pubkey::find_program_address` vs `create_program_address`; reentrancy guards on cross-program invocations |
| Rust / Soroban | `percent_mul_up` vs `percent_mul`; `safe_u128_to_i128` vs `as i128`; `try_invoke_contract::<T, E>` error-handling pattern; `extend_ttl` consistency; pause re-check at entry vs callback |
| Move / Aptos+Sui | `assert!(amount > 0)` vs implicit; `SignerCapability` rotation patterns; `move_from`/`move_to` ordering; vector-bounds checks |
| C/C++ (XRPL/rippled) | `tesSUCCESS` propagation through transactor phases; `STAmount` arithmetic guards; `SLE` field validation; pre-claim vs do-apply firewalls; canonical-XDR encoding |

---

## Anti-Patterns (when NOT to apply)

1. **Greenfield code with no documented conventions** — there's nothing to sweep
2. **Single-entry-point contracts** — no convention pool to compare against
3. **Math-heavy code without conventions** (e.g., a pure ZK verifier) — use M-16 instead
4. **Audits where the realism filter is undefined** — consistency-class findings flood the report and dilute Mediums

---

## Validated Findings

- **K2 Code4rena (2026-04-17 → 2026-05-27)**: 14 of 14 QA-Bundle entries (9 Lows + 5 Info) followed this pattern. Discovered across passes 4, 5, 6, 7. Yield: 100% of all post-Pass-1 findings. The submitted Medium (`swap_collateral` missing oracle floor) is also a consistency-class finding (Pass 1 found it via the same shape — `flash_loan.rs:465-484` enforces oracle floor, `swap.rs:192-194` doesn't).

---

## Integration Points

- **Trigger flag in `template_recommendations.md`**: `CONSISTENCY_SWEEP = true` if recon detects ≥3 helpers with similar names or ≥2 documented conventions
- **Spawned agent**: `general-purpose` with model="sonnet" (mechanical task), reading the convention catalog as input and producing the outlier list as output
- **Cost**: 1 sonnet agent per 5 conventions

---

## Why Humans Miss This

Human auditors trace one function at a time. They notice "this site uses `percent_mul_up`" but not "the OTHER site uses `percent_mul`" because they're not in the same field-of-view. Consistency-class sweep is mechanical pattern matching — exactly the work an agent does well.
