# Phase: L1 Bake (Phase 0.5, L1 mode only, v1.14+)

> Fresh `codex exec --json` subprocess. No prior context. Treat this prompt as your entire task.
> This phase runs ONLY in L1 mode (`$dewaxguard l1`), between recon (Phase 1) and breadth (Phase 3). It extracts code patterns into 8 bake artifacts that L1 depth agents consume. Most of the work is mechanical (bash script invocation); your judgment is needed only to validate outputs and supplement with grep where the script came up short.

## Audit context

- **Audit ID**: `{{AUDIT_ID}}`
- **Mode**: `{{MODE}}` (with `--l1` flag)
- **Source path**: `{{SRC_PATH}}`
- **Project root**: `{{PROJECT_ROOT}}`
- **Scratchpad**: `{{SCRATCHPAD}}`
- **Skill root**: `{{SKILL_ROOT}}`
- **Phase budget**: `{{TIMEOUT_SECONDS}}` seconds

## Pre-requisites

- `{{SCRATCHPAD}}/preflight.md` (Phase 0)
- `{{SCRATCHPAD}}/build_status.md` (Phase 1, from recon)
- Language detected as `go` or `rust` (the only L1 languages supported in v1.14)

If LANGUAGE is `cpp`, the L1 Bake step is replaced by `platform-quirks/cpp.md`'s built-in known-issue catalog — exit cleanly with a `{{SCRATCHPAD}}/bake/_bake_summary.md` that records "C++ L1 — using cpp.md as bake substitute" and skip to Phase 3 breadth.

---

## STEP 1 — Run the bake script

```bash
bash {{SKILL_ROOT}}/scripts/bake_l1.sh \
    --src {{SRC_PATH}} \
    --out {{SCRATCHPAD}}/bake \
    --lang $LANGUAGE
```

The script auto-detects the best available tool: ast-grep → opengrep → ripgrep → POSIX grep (PCRE fallback when available). It emits 8 artifacts under `{{SCRATCHPAD}}/bake/`:

| Artifact | Consumer |
|----------|----------|
| `non_deterministic_calls.md` | depth-consensus-invariant |
| `consensus_state_machine.md` | depth-consensus-invariant |
| `slashing_conditions.md` | depth-consensus-invariant (slashing matrix step 5) |
| `validator_lifecycle.md` | depth-consensus-invariant (lifecycle race step 6) |
| `p2p_message_handlers.md` | depth-network-surface |
| `rpc_methods.md` | depth-network-surface (auth ladder step 4) |
| `mempool_admission.md` | depth-network-surface |
| `peer_scoring_rules.md` | depth-network-surface (scoring symmetry step 3) |
| `_bake_summary.md` | the L1 depth dispatcher (you, here) |

Plus a `_bake_summary.md` that records the tool used and per-artifact byte counts.

---

## STEP 2 — Inspect outputs, supplement gaps

Read `_bake_summary.md` for the tool that was used:

- If `ast-grep` was selected: outputs are AST-precise. Move on to STEP 3.
- If `opengrep` or `rg` was selected: outputs are regex-based; expect some false positives. Move on to STEP 3.
- If `grep` (POSIX fallback) was selected: outputs may have missed patterns that rely on PCRE. Run targeted supplementary greps for the artifacts that are unexpectedly small (< 200 bytes):

```bash
# Supplementary grep: time.Now in test files (intentionally excluded by main bake but worth checking)
grep -rn 'time.Now' --include='*.go' {{SRC_PATH}}/

# Supplementary grep: typed nil returns (Go quirk #7 from platform-quirks/go.md)
grep -rn 'return.*nil' --include='*.go' {{SRC_PATH}}/ | head -20
```

Append findings to the relevant bake artifact under a `## Supplementary` section.

---

## STEP 3 — Validate baseline known-issue catalog applies

For Ethereum, Cosmos, and similar mature chains, baseline known-issue catalogs are published:

| Chain | Public advisory list |
|-------|----------------------|
| Ethereum execution | https://github.com/ethereum/go-ethereum/security/advisories |
| Ethereum CL | https://github.com/ethereum/consensus-specs/security |
| Reth | https://github.com/paradigmxyz/reth/security/advisories |
| Cosmos SDK | https://github.com/cosmos/cosmos-sdk/security/advisories |
| CometBFT | https://github.com/cometbft/cometbft/security/advisories |
| Bitcoin Core | https://en.bitcoin.it/wiki/Common_Vulnerabilities_and_Exposures |
| GHSA Go advisories | https://pkg.go.dev/vuln/list |

If WebFetch is available, fetch the latest 24 months of advisories for the target chain and write a brief catalog to `{{SCRATCHPAD}}/bake/known_issues_index.md`:

```markdown
# Known-Issue Index (L1 baseline) — {{AUDIT_ID}}

## Source: <chain advisory URL>
## Last fetched: <ISO date>

| Advisory ID | Date | Title | One-line root cause |
|-------------|------|-------|--------------------|
```

If WebFetch is not available, skip this step but record the skip in your output.

This catalog is consumed by depth-consensus-invariant + depth-network-surface for dedup — findings that match a known advisory's root cause are flagged with `duplicate_of_v12` (the field name is misleading; it captures any external known-issue match).

---

## STEP 4 — Output

Write `{{SCRATCHPAD}}/bake_summary.md`:

```markdown
# L1 Bake Summary — {{AUDIT_ID}}

**Generated**: {{ISO_NOW}}
**Bake script tool**: <ast-grep|opengrep|rg|grep>
**Source path**: {{SRC_PATH}}

## Artifacts produced

| Artifact | Bytes | Pattern matches |
|----------|-------|-----------------|
(table per artifact)

## Supplementary patterns run

(any extra greps from STEP 2; blank if none)

## Baseline known-issue catalog

- **Source**: <chain advisory URL or 'WebFetch unavailable; skipped'>
- **Catalog size**: <N entries> or 'skipped'
- **Cutoff**: <date or N/A>

## Handoff to depth agents

- depth-consensus-invariant will consume: non_deterministic_calls, consensus_state_machine, slashing_conditions, validator_lifecycle, known_issues_index
- depth-network-surface will consume: p2p_message_handlers, rpc_methods, mempool_admission, peer_scoring_rules, known_issues_index

## Risk flags raised by bake outputs

(brief observations: e.g., "high count of time.Now in consensus paths → consensus-divergence risk concentrated"; "no per-sender quota detected in mempool admission → DoS vector likely")
```

This summary is informational — the driver content gate just checks that `bake_summary.md` exists with reasonable content.

---

## Required outputs (driver gate checks for these)

- `{{SCRATCHPAD}}/bake_summary.md`
- `{{SCRATCHPAD}}/bake/_bake_summary.md` (written by the script itself)

## Retry hint (if any)

{{RETRY_HINT}}

When the bake script runs successfully and `bake_summary.md` is written, exit cleanly. Do not start breadth or depth — the driver invokes those separately.
