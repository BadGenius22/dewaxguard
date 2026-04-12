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

## Composition Coverage Map

Track all finding pairs explored. Cross-class pairs (state + token, access + external) are HIGH PRIORITY.
