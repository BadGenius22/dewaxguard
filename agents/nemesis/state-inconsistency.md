# Nemesis: State Inconsistency Auditor

> **Phase**: 4b.1 (Thorough mode only)
> **Method**: Map coupled state pairs, find mutation gaps, trace consequences
> **Scope**: Enriched by Feynman's SUSPECT verdicts

## Pipeline

### Step 1: Coupled State Dependency Map
For every storage variable: "What other values MUST change when this one changes?"
- per-user balance ↔ accumulator/checkpoint
- numerator ↔ denominator
- position size ↔ derived values (health, rewards, shares)
- total/aggregate ↔ sum of components
- cached computation ↔ inputs it was derived from

### Step 2: Mutation Matrix
For EACH coupled pair, list EVERY function that writes to EITHER side.
Mark: updates BOTH (synced) or only ONE (GAP).

### Step 3: Parallel Path Comparison
Group functions with similar outcomes (transfer vs burn, withdraw vs liquidate, direct vs wrapper).
Do ALL paths update the SAME coupled state?

### Step 4: Operation Ordering Within Functions
Trace exact order of state changes. Between steps: are coupled pairs consistent?
If external call happens between steps — can callee see inconsistent state?

### Step 5: Feynman-Enriched Targets
For each SUSPECT from Feynman:
1. Is the suspect state part of a coupled pair?
2. Does the suspect function update all counterparts?
3. Does the ordering concern create a measurable state gap?

## Output

For each GAP found:
- Coupled pair (State A ↔ State B)
- The function that updates A but NOT B
- Downstream functions that read stale B
- Concrete trigger sequence

Write to `{SCRATCHPAD}/.audit/findings/state-pass{N}.md`
