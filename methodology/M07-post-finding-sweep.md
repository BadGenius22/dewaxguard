---
id: M-07
name: post-finding-sweep
trigger_type: process
trigger_event: "after any finding is CONFIRMED whose root cause is a shared helper — fan out across all callers of that helper for analogous findings"
trigger_languages: [all]
applies_to_protocol_types: [any]
---

# M-07: Post-Finding Root-Cause Sweep

**Origin**: XRPL Sherlock April 2026, L-14 sweep run that converted 1 open lead into an additional Medium finding (ESC-3) after ESC-1 validated F-13.

**One-line**: When one caller of a shared helper becomes a finding, don't close the lead — sweep all callers for analogous findings.

## Trigger

Apply when:
- A finding's root cause is a **shared helper** / framework function (e.g. `accountHolds`, `balanceOf`, `requireAuth`, `safeTransferFrom`).
- The helper has **multiple callers** across the codebase.
- The blind spot or asymmetry the helper exposes is **caller-independent** (anyone using it inherits the flaw).

## Process

1. **Grep** for all callers of the helper in scope:
   - `grep -rn "helperName" src/ --include="*.{cpp,rs,sol,move}"`
2. **Cluster** callers by amendment / feature / module. Reduces cognitive load and maps to reward pools (M-04).
3. **Per caller, classify usage**:
   - **Threshold check**: "does X have enough of Y" → **HIGH** exploit surface if helper has a blind spot
   - **Delta compute**: "how much to transfer/credit" → medium surface (may underpay)
   - **Informational**: pure getter for logging / RPC → zero exploit surface
4. **Apply immunity filters**:
   - **Pseudo-account immunity**: if the address being queried is a pseudo-account that cannot sign tx, it cannot create the adversarial state → skip
   - **Protective-direction immunity**: if the helper's result is used CONSERVATIVELY (fail-closed on low values), the blind spot is not exploitable constructively
5. **Per candidate caller**, apply the original attack template (M-03 / M-08) with the new context.
6. **Parallelize**: spawn one agent per cluster for fan-out. Each agent gets the original finding as template + their cluster's files.

## Cross-language mapping

| Chain | Example helper with many callers | Sweep strategy |
|-------|----------------------------------|----------------|
| **EVM / Solidity** | `SafeERC20.safeTransferFrom` | Find all callers; for each, ask if the helper's failure mode is handled correctly |
| **Solana / Rust** | `token_2022::transfer_checked` | Callers must handle the account-data-too-small error; sweep for unhandled cases |
| **Move / Aptos** | `coin::withdraw<T>` | Sweep for callers that assume amount availability |
| **C++ / XRPL** | `accountHolds(mpt)` | Sweep converted ESC-1 into ESC-3 in ~15 agent-minutes |

## Template prompt for sweep agents

```
You are Sweep Agent {N} — {CLUSTER_NAME}.

## Context
Finding {ID} validated that {HELPER} has {BLIND_SPOT}. The flaw is caller-independent — anyone using {HELPER} inherits it if they use the result as a threshold check.

## Scope
{LIST of files in this cluster}

## Process
1. Grep all `{HELPER}` calls in these files.
2. Classify each: threshold / delta / informational.
3. For threshold-class callers, apply M-08 template (holder plants state → admin action breaks).
4. Apply immunity filters (pseudo-account, conservative-direction).
5. Report each as CONFIRMED / PARTIAL / REFUTED with file:line.

## Output
Per-caller verdict table + findings in standard format.
```

## Anti-patterns

- **Don't sweep without the immunity filters**. Pseudo-account callers waste agent effort and create false positives.
- **Don't use M-07 for unrelated findings**. It's only for shared-helper root-cause fan-out.
- **Don't confuse sweep with breadth recon**. M-07 is targeted post-finding; initial breadth recon already covers callers but without the specific attack template.

## ROI data point

**L-14 sweep (XRPL)**:
- Input: 1 validated finding (ESC-1), 1 shared helper (`accountHolds`), 18 callers across 4 amendments
- Cost: 3 parallel agents, ~15 agent-minutes
- Output: 1 additional Medium (ESC-3), 2 new refuted classes (R-22, R-23), 1 new framework fact (F-15 pseudo-account immunity)
- ROI: 1 extra finding per 5 minutes of agent time

## Related methodology

- **M-04 feature-pool coverage**: apply to each new finding from the sweep individually.
- **M-08 holder-plants-trap**: the template each sweep candidate is probed against.
- **F-15-style immunity notes** from prior audits save sweep time — check them first.
