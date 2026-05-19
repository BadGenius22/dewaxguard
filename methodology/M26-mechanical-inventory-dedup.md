# M-26 — Mechanical Inventory + Dedup + Severity Routing (v1.12+)

> **Origin**: Plamen v2.0.0 (2026-05-13) deprecated its LLM orchestrator after observing context-saturation drift on multi-agent audits — late-pipeline phases silently skipped mandatory dedup work, and the same finding showed up 3-5x in the report under slightly different titles. dewaxguard v1.12 ports the mechanical-Python pattern: three deterministic scripts replace the LLM-led inventory phase.
>
> **Trigger**: every audit, between Phase 3 (Breadth) and Phase 4b (Depth). Not protocol-specific, not language-specific.
>
> **Yield class**: reliability + cost. Removes a class of failure ("orchestrator silently skipped dedup, report ships with duplicates") and reduces inventory cost from 1 LLM agent to 0.1 LLM agent equivalent.

---

## The Pattern

When 8 breadth agents each find 5-15 candidate vulnerabilities, the orchestrator typically has to:

1. Read every `analysis_*.md` from scratchpad
2. Group findings by root cause (same bug found by multiple agents)
3. Pick a canonical for each cluster
4. Assign severities via the Impact×Likelihood matrix
5. Apply realism-filter downgrades
6. Feed the deduped table to Phase 4b depth agents

Doing this with an LLM agent has three failure modes:

- **Non-determinism**: same input → different clusters across runs. Hard to debug, hard to validate.
- **Attention saturation**: with 60+ findings the LLM starts collapsing distinct bugs into "see above" or skipping severity assignment for low-priority items.
- **Cost**: a single inventory agent costs more than running the three Python scripts a hundred times.

The fix is to push the mechanical work into Python and only invoke an LLM for cases the heuristic can't resolve.

---

## When to Apply

| Trigger | Action |
|---------|--------|
| Phase 3 has produced ≥ 2 `analysis_*.md` files | MANDATORY — run the v1.12 pipeline |
| Light mode with only 2-3 breadth agents | OPTIONAL — savings are smaller; skip if budget tight |
| Phase 3b re-scan produced additional `analysis_rescan_*.md` files | Re-run the pipeline on the union of all analysis files |
| Phase 5 verification reshuffles severities | Re-run `severity_router.py` only (parse + dedup unchanged) |

---

## Process

### Step 1 — Parse breadth output into the schema

```bash
python3 scripts/parse_findings.py \
    $SCRATCHPAD/analysis_*.md \
    --audit-id "$AUDIT_ID" \
    --phase breadth \
    -o $SCRATCHPAD/findings_breadth.json
```

The parser handles both formats agents may emit:

- `FINDING | contract: X | function: Y | bug_class: Z | group_key: X | Y | Z` (breadth agents)
- `## Finding [H-01]: Title [VERIFIED]` with `**Severity**:`/`**Location**:`/etc. (Phase 5/6 re-runs)

Optional schema-aligned fields are parsed when present: `severity:`, `impact:`, `likelihood:`, `realism_filter:`, `location:`, `evidence:`. Agents are NOT required to emit these — they default to None and downstream scripts fill them in.

### Step 2 — Mechanical dedup

```bash
python3 scripts/dedup.py \
    $SCRATCHPAD/findings_breadth.json \
    -o $SCRATCHPAD/findings_merged.json \
    --clusters-out $SCRATCHPAD/dedup_clusters.json \
    --ambiguous-out $SCRATCHPAD/dedup_ambiguous.json
```

Three-stage clustering, runs in milliseconds even on 200+ findings:

| Stage | Rule | Score |
|-------|------|-------|
| A | exact `group_key` match | 1.00 → MERGE |
| A2 | same `contract`+`function` + bug_class overlap ≥ 0.3 | 0.92 → MERGE |
| A2 | same `contract`+`function` + title similarity ≥ 0.55 | 0.88 → MERGE |
| A2 | same `contract`+`function` + partial alignment | 0.74-0.78 → AMBIGUOUS |
| B | same file + line proximity (±5) + bug_class jaccard ≥ 0.6 | 0.95 → MERGE |
| B | same file + line proximity + partial bug_class | ≥ 0.70 → AMBIGUOUS |
| C | cross-file bug_class token overlap + title similarity ≥ 0.85 | MERGE |
| C | cross-file token overlap + title 0.70-0.85 | AMBIGUOUS |

Each pair is evaluated **at most once** across all stages (deduped by `evaluated` set). Cluster picker selects the canonical with the highest severity, FINDING over LEAD, most evidence tags.

**Output**:
- `findings_merged.json` — canonical findings + duplicate rows pointing at canonical via `canonical_id`
- `dedup_clusters.json` — per-cluster audit trail
- `dedup_ambiguous.json` — pairs in the fuzzy band (0.70-0.85) — need human or LLM tie-break

### Step 3 — LLM tie-break for ambiguous pairs (conditional)

If `dedup_ambiguous.json` is non-empty:

```python
# Pseudocode for orchestrator
import json
ambig = json.load(open(f"{SCRATCHPAD}/dedup_ambiguous.json"))["ambiguous"]
if ambig:
    # Spawn a single haiku agent with the full pair list. Cheap (≤1k tokens).
    prompt = f"""For each pair, decide MERGE or SEPARATE. Output one line per pair.
Pairs:
{json.dumps(ambig, indent=2)}
Findings table:
{open(f"{SCRATCHPAD}/findings_merged.json").read()}
"""
    # ... spawn agent, parse response, update findings_merged.json
```

Skip Step 3 if `ambig` is empty. Typical audit produces 0-5 ambiguous pairs.

### Step 4 — Severity routing

```bash
python3 scripts/severity_router.py \
    $SCRATCHPAD/findings_merged.json \
    -o $SCRATCHPAD/findings_routed.json \
    --diff-out $SCRATCHPAD/severity_changes.json
```

Applies the matrix from `rules/report-template.md`:

| Impact \ Likelihood | High | Medium | Low |
|---------------------|------|--------|-----|
| High | Critical | High | Medium |
| Medium | High | Medium | Medium |
| Low | Medium | Low | Low |
| Informational | Info | Info | Info |

Then applies downgrades per `rules/realism-filter.md`:

- `realism_filter: admin-trust` → −1 tier (floor: Informational)
- `realism_filter: design-choice` → cap at Informational
- `realism_filter: unreachable-precondition` → cap at Informational
- `extra.VIEW_ONLY = true` → cap at Medium
- `extra.ON_CHAIN_ONLY = true` without off-chain impact → −1 tier

Use `--proven-only` to cap any finding without a proof tag (`POC-PASS`, `MEDUSA-PASS`, `PROD-*`, `FUZZ-PASS`) at Low. This implements PROVEN_ONLY mode per the report-template.md guidelines.

### Step 5 — Feed depth agents

The deduped, severity-routed table becomes Phase 4b's input. Each canonical finding (where `canonical_id is null`) becomes one row sent to the appropriate depth agent:

| Bug class root token | Depth agent |
|----------------------|------------|
| auth, access, role, permission | depth-state-trace |
| math, precision, overflow, rounding | depth-edge-case |
| oracle, external, callback, cpi | depth-external |
| token, balance, share, donation | depth-token-flow |
| serialization, layout, type | depth-lowlevel |
| consensus, mempool, p2p | depth-network-surface (v1.14 L1 only) |

---

## Fallback (when scripts unavailable)

If `python3` is not available on the orchestrator's machine, fall back to the legacy LLM inventory agent. The fallback path is documented in SKILL.md under `--legacy`. Findings will be functionally equivalent but non-deterministic across runs.

---

## Validation

Tested on synthetic multi-agent overlap scenarios:

- 3 agents finding the same bug with slightly different `bug_class` spellings (`missing-auth` / `missing-access-check` / `auth-missing`) → all 3 merged into 1 canonical
- Same function with two legitimately different bugs (`missing-auth` + `rounding-loss` on `liquidate`) → correctly kept separate, no false merge
- Cross-contract same-class bugs (`oracle-staleness` on both `PriceOracle` and `BackupOracle`) → correctly kept separate (different fixes needed per `Root-Cause Consolidation Rule` in report-template.md)
- Mixed `FINDING |` pipe + `## Finding [H-01]:` markdown in same file → both formats parsed and deduped together

End-to-end run time on 50-finding input: < 100ms (vs ~30s for an LLM inventory agent).

---

## Cross-language applicability

Schema and scripts are language-agnostic — work on EVM, Solana, Soroban, Aptos Move, Sui Move, C/C++ findings indifferently. The `bug_class` taxonomy is kebab-case strings the agents define; dedup works on token overlap regardless of which language the bugs belong to.

---

## Integration with existing methodologies

- **M-13 (Kuprum-style external dedup)**: independent — M-13 is *external* dedup against community-curated indices, M-26 is *internal* cross-agent dedup. Both run.
- **M-25 (V12-style external dedup)**: independent — M-25 uses `scripts/grep_v12.sh` against external V12 outputs, M-26 uses `scripts/dedup.py` against internal findings. Both run.
- **M-10 (3-layer dedup)**: M-26 IS the new mechanical foundation for M-10's "layer 1" (internal). Layers 2 (M-13/Kuprum) and 3 (M-25/V12) continue as before.

---

## Anti-patterns

1. **Asking an LLM agent to "do the inventory" instead of running the scripts** — non-deterministic, expensive, prone to attention saturation. Use scripts.
2. **Skipping `severity_router.py` because "findings already have severities"** — the diff log catches realism-filter downgrades that the breadth agents missed.
3. **Treating `dedup_ambiguous.json` as merge-everything** — these are genuinely uncertain pairs; some should NOT merge. Use an LLM tie-break or human review, not blind merge.
4. **Re-running Phase 4a after Phase 5 verification on the full pipeline** — only `severity_router.py` needs re-running when severities shift; dedup is stable.
