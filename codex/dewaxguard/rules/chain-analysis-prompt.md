# Phase 4c: Chain Analysis

> **Purpose**: Combine findings into compound attack paths. Match postconditions to preconditions.

## Agent 1: Enabler Enumeration + Grouping

For each finding, extract dangerous precondition states. For EACH state, check 5 actor categories:
1. External attacker (permissionless)
2. Semi-trusted role (within permissions)
3. Natural protocol operation
4. External event (governance, pause, slash)
5. User action sequence (normal usage)

Group by root cause into hypotheses. Max 5 findings per hypothesis.

## Agent 2: Chain Matching

For each PARTIAL/REFUTED finding:
1. Extract missing precondition
2. Search ALL CONFIRMED findings for matching postconditions
3. If found: Create CHAIN HYPOTHESIS with combined attack

Chain severity: never lower than highest constituent. Upgrade if combined impact > either alone.

## Subsumption direction (MANDATORY)

When one hypothesis absorbs another ("weaker variant of", "already dominated by", "subsumed into"), absorption runs toward the **more reachable** hypothesis — never toward the bigger number.

- A `permissionless` finding is **NEVER** subsumed by an actor-gated one (`admin-trust`, `semi-trusted-role`, `compromised-key`), regardless of magnitude. Magnitude does not survive the realism filter; reachability does. Absorbing a permissionless finding into an admin-gated one deletes the only submittable member of the pair.
- When two findings share a root cause but differ in actor gate, the surviving hypothesis inherits the **lowest** gate among its constituents, and its severity is re-derived from that gate — not from the largest constituent impact.
- "X is a weaker variant of Y" is a valid dismissal **only** when X and Y carry the same actor gate. Otherwise both are recorded, separately.
- Before writing NEG/subsumed in the coverage map, state the actor gate of both sides. If they differ and you are still subsuming, that is a workflow error.

## Composition Coverage Map

Track all finding pairs explored. Cross-class pairs (state + token, access + external) are HIGH PRIORITY. Every `NEG/subsumed` row must carry the actor gate of both sides (see Subsumption direction above).
