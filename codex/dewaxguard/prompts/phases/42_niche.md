# Phase: Niche Agents (flag-triggered, v1.13.1 driver)

> Fresh `codex exec --json` subprocess. No prior context. Treat this prompt as your entire task.
> This phase runs AFTER inventory (Phase 4a) and BEFORE depth (Phase 4b). Niche agents are flag-driven: if no flags fire, this phase exits cleanly with an empty summary.

## Audit context

- **Audit ID**: `{{AUDIT_ID}}`
- **Mode**: `{{MODE}}`
- **Scratchpad**: `{{SCRATCHPAD}}`
- **Skill root**: `{{SKILL_ROOT}}`

## Pre-requisites

- `{{SCRATCHPAD}}/template_recommendations.md` (from recon Phase 1.1) — names which niche agents to spawn
- `{{SCRATCHPAD}}/findings_routed.json` (from inventory)

If `template_recommendations.md` does not exist OR contains no `## Niche Agents` section: write `{{SCRATCHPAD}}/niche_summary.md` using the "none triggered" template below (it opens with the `NO-FINDINGS` sentinel the content gate recognises) and exit cleanly. Do NOT spawn any agents.

## Your task — flag-driven dispatch

Read `template_recommendations.md` and find a `## Niche Agents` section. It looks like:

```markdown
## Niche Agents

- EVENT_COMPLETENESS — trigger: MISSING_EVENT flag on setter_list.md
- SIGNATURE_VERIFICATION_AUDIT — trigger: HAS_SIGNATURES (ecrecover/EIP712 detected)
- SPEC_COMPLIANCE_AUDIT — trigger: HAS_DOCS (whitepaper/spec provided)
- SEMANTIC_CONSISTENCY_AUDIT — trigger: HAS_MULTI_CONTRACT (2+ contracts sharing params)
```

For each listed niche agent, spawn a Codex subagent in parallel. Use a unique task name and `fork_turns="none"`; request high reasoning effort for `core`/`thorough` and medium for `light` when supported. These are finding agents even though this dispatcher subprocess only coordinates them.

### Niche agent specs

#### EVENT_COMPLETENESS

```
You are the EVENT_COMPLETENESS niche agent.
Read: {{SKILL_ROOT}}/methodology/INDEX.md for the niche-agent description; if missing, default to: "for every admin/state-changing function, verify a corresponding event is emitted with the right parameters; flag missing events, wrong parameters, or events emitted before state change".

## Inputs
- {{SCRATCHPAD}}/findings_routed.json (existing findings; do not duplicate)
- {{SCRATCHPAD}}/contract_inventory.md (function list)
- {{SCRATCHPAD}}/attack_surface.md (state-changing functions)
- Source files for the contracts in scope

## Method
For each state-changing function in scope:
1. Identify what state it changes
2. Check whether an event is emitted
3. Check the event includes all material parameters (old value, new value, actor)
4. Check the event is emitted AFTER the state change (not before)
5. Flag: missing event / wrong parameters / wrong ordering / wrong indexing

## Output
{{SCRATCHPAD}}/niche_event_completeness_findings.md
Use pipe-delimited FINDING/LEAD format, IDs [NEC-1], [NEC-2]...

SCOPE: write only to that file. Return findings and stop.
```

#### SIGNATURE_VERIFICATION_AUDIT

```
You are the SIGNATURE_VERIFICATION_AUDIT niche agent.
Per skill-index niche category: signature replay, malleability, EIP-712 domain, permit front-run, nonce management, cross-chain replay.

## Inputs
- Source files containing ecrecover / ECDSA.recover / EIP712Domain / permit / isValidSignature
- {{SCRATCHPAD}}/findings_routed.json

## Method
For each signature verification site:
1. Replay across nonces — does the signed payload include a nonce that's monotonically incremented?
2. Replay across chains — does the EIP-712 domain include chainid?
3. Malleability — is the s value upper-bounded? (secp256k1)
4. Permit front-run — does the contract accept arbitrary permit calldata as a public function?
5. Cross-domain — same signature usable on multiple verifiers?

## Output
{{SCRATCHPAD}}/niche_signature_verification_findings.md
IDs [NSV-1]...

SCOPE: write only to that file. Return findings and stop.
```

#### SPEC_COMPLIANCE_AUDIT

```
You are the SPEC_COMPLIANCE_AUDIT niche agent.

## Inputs
- The spec/whitepaper/design doc referenced by recon (path in template_recommendations.md or `{{PROJECT_ROOT}}/docs/`)
- {{SCRATCHPAD}}/findings_routed.json

## Method
1. Extract every TESTABLE claim from the spec (numeric formulas, invariants, ordering claims, boundary values)
2. For each claim, find the corresponding code site
3. Verify: code matches spec / code diverges from spec / spec is ambiguous
4. Flag every mismatch and every ambiguity that affects security

## Output
{{SCRATCHPAD}}/niche_spec_compliance_findings.md
IDs [NSC-1]...

SCOPE: write only to that file. Return findings and stop.
```

#### SEMANTIC_CONSISTENCY_AUDIT

```
You are the SEMANTIC_CONSISTENCY_AUDIT niche agent.

## Inputs
- All in-scope contracts/modules
- {{SCRATCHPAD}}/findings_routed.json

## Method
For configuration variables, formulas, and magic numbers shared across ≥2 contracts:
1. Catalog the canonical value/formula per contract
2. Find outliers — same variable name with different unit, different bound, different formula
3. Flag every drift (likely cut-and-paste bug)

## Output
{{SCRATCHPAD}}/niche_semantic_consistency_findings.md
IDs [NSCO-1]...

SCOPE: write only to that file. Return findings and stop.
```

### Spawn rule

Read the `## Niche Agents` list. For EACH listed agent, spawn the matching block above. Skip agents not listed. If a niche agent's trigger condition is no longer met (e.g., the file it depends on disappeared), skip it with a note in the summary.

### Summary

After all spawned agents return, write `{{SCRATCHPAD}}/niche_summary.md`:

```markdown
# Niche Agents Summary — {{AUDIT_ID}}

**Triggered**: <list>
**Skipped (trigger absent)**: <list>
**Total findings**: <N>

| Agent | Findings file | Findings count |
|-------|---------------|---------------|

(One row per spawned agent.)
```

If no niche agents were listed in `template_recommendations.md`, write exactly:

```markdown
NO-FINDINGS

# Niche Agents Summary — {{AUDIT_ID}}

**Triggered**: none
**Reason**: no niche agent flags in template_recommendations.md
```

The leading `NO-FINDINGS` line is the sentinel the content gate accepts for a legitimately-empty phase; keep it as the first line.

## Required outputs (driver gate checks for these)

- `{{SCRATCHPAD}}/niche_summary.md`

The content gate accepts this file when it either carries the `NO-FINDINGS` sentinel (the "none triggered" case above) or is a non-stub summary ≥ 200 bytes with ≥ 3 non-header lines (the "agents ran" case).

## Retry hint (if any)

{{RETRY_HINT}}

When the summary is written and all spawned agents have produced their findings files, exit cleanly.
