# Cross-Language Methodology Index

> **Cross-language, cross-platform audit methodology.** Entries here apply to EVM/Solidity, Rust/Solana, Rust/Soroban, Move/Aptos, Move/Sui, and C/C++ alike.
>
> **Origin**: distilled from completed audits where each entry was validated against concrete findings.
>
> **Read these before every audit.** They encode attack-template thinking that pays off across projects.

## Entries

| ID | Name | Validated in | Purpose |
|----|------|--------------|---------|
| [M-03](M03-inverse-trust-lens.md) | Inverse-trust-direction lens | XRPL Domain 4 ESC-1/2 | Probe every compliance primitive from the opposite trust direction |
| [M-04](M04-feature-pool-coverage.md) | Feature-pool PoC coverage | XRPL Domain 4 ESC-1 | Bridge shared-infrastructure root cause to a specific contest feature pool |
| [M-07](M07-post-finding-sweep.md) | Post-finding root-cause sweep | XRPL L-14 sweep → ESC-3 | Fan-out a validated blind spot across all callers of the affected helper |
| [M-08](M08-holder-plants-trap.md) | Holder-plants-trap / admin-action-bricks-state | XRPL ESC-1/2/3 + CONF-1 + DEL-1 (5/5) | The highest-yield attack template across audits |
| [M-09](M09-sync-gap-detection.md) | Aggregate-vs-per-entity SYNC_GAP | XRPL CONF-1 | Any aggregate counter gating a state transition is a SYNC_GAP candidate |
| [M-10](M10-prior-audit-dedup.md) | Pre-submission 3-layer dedup | XRPL Sherlock submission | Mandatory pre-submission validation — prior audits / GitHub baseline / remediation |
| [M-11](M11-retired-amendment-poc-feasibility.md) | Retired-amendment PoC feasibility check | XRPL Domain 7 SPON-M1 (not submitted) | Before investing in a finding in a legacy code branch, verify PoC reachability |
| [M-12](M12-granular-permission-sandbox.md) | Granular permission sandbox ↔ semantic override audit | XRPL Domain 6 DEL-1 (OOS via #6890 — template still valid) | Any "capability templates / per-op masks" system has default-permissive scope creep |
| [M-13](M13-kuprum-known-issue-index-ingestion.md) | Kuprum-style known-issue index ingestion | XRPL 2026-04 (caught DEL-1 OOS mid-audit) | Ingest 3rd-party non-authoritative known-issue catalogs EARLY in any competitive audit |
| [M-14](M14-elevated-impact-vs-unchanged-legacy.md) | Elevated-impact vs unchanged-legacy judgment | XRPL 2026-04 L-32 (contested) | Decide whether a bug in unchanged code is IN-SCOPE because a new feature makes it common-case |

## How to use

1. **Before starting an audit**: skim all 8 templates. They prime the attention system.
2. **During breadth analysis**: at each transactor/function, ask:
   - Does M-08 apply? (cheap-plant + admin-op dependency?)
   - Does M-09 apply? (aggregate counter gates transition?)
   - Does M-12 apply? (granular permission with default-permissive semantic hook?)
3. **After a finding**: apply M-07 sweep to related helpers.
4. **Before submission**: run M-04 (feature classification) + M-10 (dedup) + M-11 (feasibility).

## Per-audit high-yield template

From the XRPL audit: **M-08 accounts for 4 of 4 submittable Mediums** (5/5 at writeup, reduced to 4/4 after DEL-1 OOS via kuprum dedup; M-12 was M-08-adjacent). Start every audit by running M-08 probe on every privileged operation. Yield > effort by a wide margin.

**M-13 is now equally critical for competitive audits** — ingesting a kuprum-style known-issue index before domain runs saved ~6h of wasted PoC development on DEL-1.

## Contribution guide

When a new audit validates a new template, add it here as M-NN with:
- **Name** + 1-sentence description
- **Origin** (which audit, which finding validated it)
- **Trigger** (when to apply)
- **Process** (concrete steps)
- **Cross-language mapping** (at least 2 language examples)
- **Anti-patterns** (when NOT to apply)
