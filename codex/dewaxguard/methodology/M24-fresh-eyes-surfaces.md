---
id: M-24
name: fresh-eyes-surfaces
trigger_type: process
trigger_event: "late-stage sweep after >=1 prior breadth/depth pass completed (enumerate surfaces no themed pass covered)"
trigger_languages: [all]
applies_to_protocol_types: [any]
---

# M-24 — Fresh-Eyes Surface Sweep

> **Origin**: K2 audit Pass 5 (FE-1: `flash-liquidation-helper` close-factor regression → QA-L06) and Pass 6 (Observation A: `claim_rewards` MAX_CLAIMABLE_ASSETS gap → QA-04). Both surfaced via a structured "what did the prior passes NOT investigate?" sweep.
>
> **Trigger**: After ≥1 prior breadth/depth pass has completed. Apply once per audit.
>
> **Yield class**: Typically Low / Info, but uniquely **novel** — finds gaps that themed passes don't cover by definition.

---

## The Pattern

Prior passes have explicit themes (e.g., Pass 4 = Stellar TTL, Pass 5 = adapter integration, Pass 6 = consistency-of-defenses). Each themed pass covers ONE corner of the attack surface. The fresh-eyes pass enumerates 5-8 surfaces deliberately NOT covered by the active hypothesis set, then runs a single agent to investigate each.

This is the only methodology that systematically asks *"what surface did we NOT investigate?"* — most audits answer the question implicitly via the auditor's prior knowledge, which biases toward already-known patterns.

---

## When to Apply

| Trigger | Action |
|---------|--------|
| ≥1 prior pass completed | Mandatory once per audit |
| Codebase has ≥5 satellite contracts | Mandatory — peripheral contracts are the highest-yield fresh-eyes target |
| Audit window has ≥1 day remaining after main passes | Apply early; results inform final pass selection |
| Single-contract audit with full coverage in pass 1 | SKIP — fresh-eyes adds no value |

---

## Process

### Phase 1: Surface enumeration (orchestrator inline)

Build a list of 5-8 surfaces NOT covered by the current hypothesis set. Categories:

1. **Tertiary contracts** (helpers, validators, view-only — typically lightly audited)
2. **Recently-modified files** (`git log --since` filtered to scope; bug-prone)
3. **Lightly-used helpers** (called by ≤2 sites — get less audit attention)
4. **Magic numbers** (hex literals, bit masks — often outdated constants)
5. **Cross-contract invariants** (state shared between satellites — falls between agent specialisations)
6. **Dead code paths** (`if false`, conditional features) — could be silently activated
7. **Test-only code that survived to production** (constants like `TEST_MODE`, fixture helpers)
8. **Inline TODO/FIXME/HACK comments** — explicit known-bug markers
9. **Never-externally-reviewed files** (re-audits only) — diff the contest's in-scope file list against the union of every prior audit's scope list from `{SCRATCHPAD}/prior_audit_scopes.md` (**M-10 step 3a**). Files in the current scope but in NO prior scope have had zero external review, and on a post-fix re-audit they are systematically where new code landed. Decompose these BY FILE (one agent per file or tight inheritance cluster), not by vulnerability lens — a re-audit has usually already been swept lens-wise, and narrow single-file scope is what buys depth that broad passes dilute. Rank by cross-referencing against your own artifacts: lowest mention count + zero prior review = thinnest coverage. Note: yields nothing on a first audit (no prior scope to diff) and is unvalidated for bug-finding — it demonstrably closes surface, but has not yet caught a bug.

For each surface, note:
- Why prior passes missed it (1 sentence)
- The specific file path or grep pattern to investigate

### Phase 2: Single agent sweep

Spawn ONE `general-purpose` agent (role=worker) with the surface list and a strict scope:

```
Investigate the 8 surfaces below. For each, identify:
- Any candidate finding NOT covered by the prior hypothesis set
- The realism filter result (PASSES / FAILS — admin-trust dependency, etc.)
- The dedup result (NOVEL / DUPLICATE OF X)

Output one block per surface. Cap total findings at 5 — quality over quantity.
```

### Phase 3: Triage

Each candidate goes through:
- **Realism filter** (per `rules/realism-filter.md`) — admin-trust → ADDITIONAL_LEADS, design-choice → drop, permissionless → keep
- **Dedup** (per M-10 / M-13 + project-local KNOWN_ISSUES_INDEX) — known → drop, novel → keep
- **Severity assignment** — typically Low or Info; Medium only if reaches Code4rena threshold ($1k+ loss)

### Phase 4: Output

Surviving candidates are filed alongside themed-pass findings (QA-Bundle for Low/Info, separate submission file for Medium+).

---

## Cross-Language Mapping

| Language | Common fresh-eyes targets |
|----------|--------------------------|
| Solidity / EVM | Tertiary contracts (Pausable wrappers, Multisig validators), `selfdestruct` callsites, `delegatecall` targets, `extcodesize` checks, deprecated functions |
| Rust / Solana | View-only program functions, account close instructions, sysvar reads, recent IDL changes |
| Rust / Soroban | Helper crates (e.g., `flash-liquidation-helper`), recently-modified PoC files, `panic_with_error!` usage in non-validation contexts |
| Move / Aptos+Sui | Module entry functions outside the main flow, recently-introduced abilities/capabilities, `friend` declarations |
| C/C++ (XRPL/rippled) | Helper RPC handlers, `account_objects`-style introspection, recently-added SLE field consumers |

---

## Anti-Patterns

1. **Don't combine with themed-pass agents** — the orchestrator's surface enumeration must happen with full visibility of what the themed agents are covering, otherwise scope drift
2. **Don't make it the FIRST pass** — fresh-eyes works because prior passes have catalogued the explored surface; without that catalogue the sweep is just another open-ended breadth pass
3. **Don't run multiple fresh-eyes passes** — diminishing returns; one structured sweep > N ad-hoc sweeps
4. **Don't skip the realism filter** — fresh-eyes surfaces tend toward admin-only paths because peripheral contracts are admin-configured

---

## Validated Findings

- **K2 Code4rena**:
  - Pass 5 fresh-eyes found **FE-1** (`flash-liquidation-helper::validate_flash_liquidation` hardcodes 50% close-factor, regresses WP-M2 fix) → filed as QA-L06
  - Pass 6 fresh-eyes found **Observation A** (`claim_rewards` lacks `MAX_CLAIMABLE_ASSETS` cap that `claim_all_rewards` enforces) → filed as QA-04
- Both findings were genuinely novel — not in V12, Halborn, WatchPug, or any prior K2 audit
- Both required the structured surface-list approach to find; ad-hoc breadth wouldn't have surfaced them

---

## Integration Points

- **Spawn point**: After Phase 4b depth completes, before Phase 4c chain analysis
- **Cost**: 1 worker agent per audit
- **Output file**: `{SCRATCHPAD}/fresh-eyes-sweep.md`

---

## Why This Yields When Themed Passes Don't

Themed passes prioritise *expected* surfaces (oracle, math, auth). Bugs in *unexpected* surfaces (helper validators, view functions, inline constants) survive themed passes by definition. Fresh-eyes is the structured complement — its scope is "everything the themes don't cover."

The K2 results validate this: FE-1 is in `flash-liquidation-helper` (a peripheral validator), Observation A is a missing constant in a lightly-audited claim path. Neither would surface in a "liquidation deep dive" or "incentives deep dive" themed pass because they're not in those surfaces' centres of gravity.
