# Docs Intent Map (False-Positive Killer)

> **Phase**: 1 (recon emits artifact) → 5d (validator consults artifact)
> **Purpose**: Pre-extract every "by design", "intentional", "expected behavior", "accepted trade-off" signal from project docs, so the validator can REJECT findings that contradict documented intent before they reach the report.
> **Origin**: Ported from cosminmarian53/skills `soroban-auditor` (docs-intent-map preprocessor).

---

## Why this exists

Many findings get filed as bugs when the protocol's docs explicitly call them out as intentional — admin trust assumptions, accepted MEV, deferred features. Without a pre-extracted intent map, each agent re-discovers and re-flags the same documented behavior, then a human has to reject it at report time.

The map turns "is this by design?" from an open-ended judgment into a single grep against an artifact.

---

## Artifact contract

**Path**: `{SCRATCHPAD}/docs-intent-map.md`
**Owner**: Recon agent 1B (Docs + External)
**Consumers**: every breadth agent (Phase 3), every depth agent (Phase 4b), the Nemesis validator (Phase 4b.1), and **mandatorily** the Bug Validator (Phase 5d Gate 1).

**Format**:

```markdown
# Documented Intent Map

## docs/06-LIQUIDATION.md:142 — by design
> Health factor improvement post-liquidation may exceed the configured target by up to LIQUIDATION_HF_TOLERANCE_BPS. This is intentional to handle rounding.

## docs/09-SECURITY.md:88 — accepted trade-off
> Pool admin can pause but cannot unpause. Emergency-only unpause is delegated to the pool admin to prevent emergency-admin compromise from halting the protocol indefinitely.

## README.md:301 — out of scope
> Self-liquidation, flash-liquidation memory budget, and DEX depth assumptions are publicly known and excluded from awardable findings.
```

Each entry MUST include:
- File:line of the documentation source
- Intent class (one of: `by design` / `intentional` / `accepted trade-off` / `out of scope` / `known limitation` / `expected behavior` / `internal helper` / `not for direct use`)
- The quoted documentation passage (≥1 sentence of context)

---

## Recon emit recipe

The recon agent (or `scripts/build_recon_maps.sh` — see commit 2) MUST grep all in-scope `*.md` documentation for these case-insensitive patterns:

```
by design|intentional|internal helper|not for direct|expected behavio|on purpose|deliberately|accepted trade.?off|known limitation|out of scope|documented exception|this is fine|note:.*always
```

Search paths (in priority order):
1. `docs/**/*.md`
2. `README.md`
3. Any root-level `*security*.md`, `*architecture*.md`, `*spec*.md`, `*invariant*.md`, `*design*.md`

Each match emits ±3 lines of context plus the file:line anchor. Empty result is acceptable — write the header and `_No documented intent signals found._` so downstream `cat` never fails.

Exclude paths: `target/`, `node_modules/`, `skills/`, anything under `.git/`.

---

## Validator consult rule (HARD)

In Phase 5d (Bug Validator), Gate 1 (Refutation) MUST execute this check **before any other refutation work**:

```
1. Grep {SCRATCHPAD}/docs-intent-map.md for the function name OR the feature keyword from the finding.
2. If a match is found whose intent class is one of:
     - "by design"
     - "intentional"
     - "accepted trade-off"
     - "out of scope"
     - "known limitation"
     - "expected behavior"
   → REJECT the finding with verdict reason: `docs-intent: {file:line} marks this as {class}`.
3. If a match is "internal helper" or "not for direct use" and the finding alleges that the function is callable by an attacker:
   → DOWNGRADE to LEAD; require evidence that an external entry point reaches it.
4. If no match is found, proceed to Gate 2 (Reachability).
```

The validator MUST emit a `docs_intent_check:` field for every finding:

```
docs_intent_check: NO_MATCH
docs_intent_check: REJECT — docs/09-SECURITY.md:88 marks unpause asymmetry as accepted trade-off
docs_intent_check: DOWNGRADE — docs/internal/helpers.md:14 marks _internalLiquidate as internal helper
```

Findings without `docs_intent_check:` populated are auto-failed by the validator harness.

---

## Anti-overreach guard

The map is a **rejection tool**, not a discovery tool. Agents MUST NOT use it as a hint catalog ("docs say X is by design, so let me find a way to violate X"). The map's only job is short-circuiting documented intent during validation.

Inverse-trust framings — where the doc claims something is by design but the code does the opposite — are still findings (and they're often the highest-value findings). When the validator finds a docs-intent match but the finding's mechanism actually contradicts the intent claim, escalate rather than reject:

```
docs_intent_check: ESCALATE — docs claim invariant X but {file:line} shows code violates X
```

Escalations bypass the rejection gate and proceed to Gate 2 with elevated severity prior.

---

## False-positive class this prevents

Without the map: agents file findings on documented behavior, validator manually re-reads docs for each one, judge rejects them at submission time as "by design".

With the map: documented behavior is filtered at validation time, before the finding consumes a submission slot. Saves judging cycles and reduces severity-inflation noise.
