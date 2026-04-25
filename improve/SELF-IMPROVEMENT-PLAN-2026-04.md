# /dewaxguard Self-Improvement Plan — 2026-04

> Generated 2026-04-25 after XRPL April 2026 Sherlock contest (Domains 1-19, 4 still pending). Captures the strategic plan for evolving /dewaxguard into a measurably-improving cross-language audit system.

## Context

After 17 of 21 audit domains, the dewaxguard methodology library has 9 templates (M-03/04/07/08/09/10/11/12/13/14/15/16/17). In-session learning works (manifest R-entries pre-refute hypotheses, F-entries shortcut analysis). Cross-session learning is partially-implemented (templates pushed to GitHub, but next-session loading is unverified). Mechanisms below would close the loop.

## Tier 1 — Mechanical, ship in a day

### 1. Mandatory session-start load of LEARNED_INDEX.md + methodology/INDEX.md
The dewaxguard skill must hard-load these at session bootstrap, not optionally. Without this, every Tier 2+ improvement is wasted because the next session never sees them.

**Implementation**: Add to dewaxguard SKILL.md a mandatory pre-flight step:
```
Before any audit work begins, READ:
- LEARNED_INDEX.md (one-liners per past audit)
- methodology/INDEX.md (template registry)
- platform-quirks/{detected_language}.md
- refuted/INDEX.md (cross-audit refuted classes)
This is non-skippable. If LEARNED_INDEX.md is empty, log "first run".
```

### 2. Trigger-pattern matching per methodology
Add frontmatter to each methodology/M-NN-*.md:
```yaml
---
trigger_grep: "Escrow|sfFinishAfter|sfCancelAfter|expir"
trigger_languages: [evm, sui, aptos, move, xrpl]
applies_to_protocol_types: [vault, escrow, payment]
---
```

At session start, the orchestrator runs the greps against the audit codebase and emits "Applicable methodologies: M-08, M-15, M-17 — load these first." Removes the burden of manual recall.

**Implementation**: Add a session-start scanner script or skill rule. Each M-template gets the frontmatter retroactively.

### 3. Negative-results retrieval
Today R-entries (refuted classes) live in per-audit MANIFEST.md and die when the audit closes. Promote them to a cross-audit `refuted/INDEX.md` keyed by vulnerability-class + language.

Before any agent declares a hypothesis worth investigating, it searches `refuted/` first. Stops re-investigating "BP H_vec[0]==pk_base forge" on every Confidential MPT audit.

**Implementation**: Create `refuted/INDEX.md` and migrate R-09/R-20/R-68 (BP collision class), R-06/R-24/R-25/R-26 (XRPL flag retroactivity by-design), R-02/R-04 (mpt-crypto identity-point + scalar overflow), etc. Each entry: `{vulnerability_class, language_or_protocol, refutation_evidence, source_audit}`.

## Tier 2 — Architectural, ship in a week

### 4. Mandatory post-audit Phase A retrospective
The post-audit-improvement-protocol.md already specifies this. Make it a hard gate: no audit closes without running Phase A (compare submissions vs eventual contest results).

Output: a single-line MEMORY entry like "Sherlock XRPL April 2026: 4M+2L submitted, contest validated 3M+2L, recall=75%, RC-METHOD=1, RC-AGENT=1."

Without this loop, you have no signal whether any M-template actually helped.

**Implementation**: Add to dewaxguard SKILL.md a post-audit step that BLOCKS audit closure until Phase A is run. If contest results aren't yet available, log "deferred" and re-run when results land.

### 5. Wire up the evals/ folder
The repo already has `solidity-auditor/evals/benchmarks/{pooltogether,dodo,megapot}` — ground-truth-with-known-bugs corpora. Run M-templates against them weekly via cron.

Any template that stops detecting any benchmark bug → flag for review or removal. This is regression testing for methodology.

**Implementation**: Add `solana-auditor/evals/benchmarks/`, `move-auditor/evals/benchmarks/`, `c-auditor/evals/benchmarks/`. Wire up `evals/runner` skill that takes a methodology + a benchmark and reports detection.

### 6. Cross-language analog enforcement
Every M-template MUST have a cross-language section with concrete syntactic triggers per language. Right now M-08 has it (rich), M-15 has it (decent), but M-13 (kuprum-ingestion) doesn't because it's XRPL-specific.

Either generalize or mark explicitly as `applies_to: [xrpl]`. Otherwise the next EVM auditor wastes effort trying to map an XRPL-only template.

**Implementation**: Audit existing M-templates. Add `applies_to:` frontmatter. For language-agnostic templates, require a "Cross-language examples" section with at minimum 2 language analogs.

## Tier 3 — Self-improving, ship in a month

### 7. Adversarial methodology-skeptic agent at session start
Spawn an "Adversary" agent whose only job is to argue against every loaded M-template's applicability to *this specific* audit. This counters the bias where M-08 won 5/5 Mediums on XRPL and now everyone over-applies it elsewhere.

**Implementation**: Add `agents/methodology-adversary.md` with prompt: "For each loaded M-template, argue why it does NOT apply to the current audit. Produce a counter-argument list. The orchestrator demotes templates with strong counter-arguments to 'optional' status."

### 8. Per-language platform-quirks auto-detection
Today `platform-quirks/cpp.md` only loads if Claude remembers. Add `meta:applies_to: [c, cpp]` and have the skill auto-load matching files based on `Move.toml`/`package.json`/`Cargo.toml`/`foundry.toml` detection.

**Implementation**: Add a session-start language-detection step. Map detected build files to platform-quirks files. Load matching files automatically.

### 9. Failure-mode database
Every "missed finding" from Phase A retrospective gets a structured entry: `{vulnerability_class, language, root_cause: RC-METHOD/SCOPE/AGENT, fix_methodology}`.

Aggregating these reveals patterns ("we miss reentrancy in Move because no M-template covers it"). This becomes input to "what M-template should I write next?" rather than guessing.

**Implementation**: Create `failure-modes/INDEX.md` with structured-entry template. Phase A retrospective populates it. Quarterly review identifies methodology gaps.

## Tier 4 — Hard truths

### 10. Most M-templates will NOT survive scrutiny
The post-audit-improvement-protocol explicitly warns against M-template proliferation. Realistically, after 3-5 audits, expect to *delete* M-templates more than add them. The current 13 templates is already high; Tier 2's eval framework will probably collapse this to 5-7 high-value templates.

### 11. Cross-language transfer is harder than it looks
M-08 "holder-plants-trap" maps cleanly to XRPL escrow. The EVM analog ("attacker stages a wrapper contract that locks state until admin acts") looks similar but the actual attack surface is different — gas dynamics, atomicity guarantees, ordering control all differ. Rich cross-language sections are necessary but not sufficient; you'd need actual cross-language benchmarks (Tier 2 #5) to validate transfer.

### 12. The biggest single improvement is feedback loop closure
Right now the audit ends, you submit findings, and you never feed contest results back into the methodology. That's the single highest-leverage gap. Tier 2 #4 (mandatory Phase A) is the unlock for all the others.

## Recommended sequencing

If you want to do ONE thing: **wire up Phase A retrospective as mandatory** (Tier 2 #4). It's the only mechanism that converts contest outcomes into methodology improvements. Without it, the system is open-loop and everything else is theater.

If you want to do TWO things: add **trigger-pattern matching** (Tier 1 #2). Cuts cognitive load at session start and forces you to make M-template applicability explicit.

If you want to ship over a sprint: Tier 1 (#1, #2, #3) + Tier 2 #4. That's: hard-load on session start, trigger-grep, negative-results index, mandatory retrospective. Together they create an actual feedback loop.

## Status tracking

| Tier | Item | Status | Owner |
|---|---|---|---|
| 1.1 | Mandatory session-start load | SHIPPED (commit: 8bc4622) | — |
| 1.2 | Trigger-pattern matching | NOT_STARTED | — |
| 1.3 | Negative-results retrieval | NOT_STARTED | — |
| 2.4 | Mandatory Phase A retrospective | NOT_STARTED | — |
| 2.5 | Wire up evals/ | NOT_STARTED | — |
| 2.6 | Cross-language analog enforcement | NOT_STARTED | — |
| 3.7 | Adversarial methodology-skeptic | NOT_STARTED | — |
| 3.8 | Per-language platform-quirks auto-detect | NOT_STARTED | — |
| 3.9 | Failure-mode database | NOT_STARTED | — |

Update this table as items ship.

## Origin

Strategic discussion 2026-04-25, session continuation of XRPL April 2026 Sherlock audit (Domains 1-16 + 19 complete; 4 domains pending). Discussion prompted by user question "should we make /dewaxguard run smarter after every audit domain session?" The plan above is the consolidated answer — what mechanism gaps exist, what fixes are highest-leverage, and what hard truths (Tier 4) prevent the system from scaling naively.
