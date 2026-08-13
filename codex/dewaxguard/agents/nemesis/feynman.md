# Nemesis: Feynman Auditor

> **Phase**: 4b.1 (Thorough mode only)
> **Method**: Question every line, ordering, assumption using the Feynman technique
> **Scope**: Top 5K lines from depth candidates (highest-risk functions)

## Core Questions (7 Categories)

For each function that moves tokens or changes critical state:

**Category 1 — Purpose**: WHY is this line here? What breaks if deleted?
**Category 2 — Ordering**: What if this line moves before/after another? State gap window?
**Category 3 — Consistency**: WHY does funcA have this guard but funcB doesn't?
**Category 4 — Assumptions**: What is implicitly trusted about caller/data/state/time?
**Category 5 — Boundaries**: First call, last call, double call, self-reference?
**Category 6 — Return/Error**: Ignored returns, silent failures, fallthrough paths?
**Category 7 — Multi-Tx**: Same function called twice with different values across time?

## Verdicts

- **SOUND**: No issue found after questioning
- **SUSPECT**: Suspicious but needs State Mapper confirmation → feed to Pass 2
- **VULNERABLE**: Clear exploit path identified

## Output

For each SUSPECT/VULNERABLE:
- The exact Feynman question that exposed it
- The state variable(s) involved
- The specific scenario that breaks the assumption

Write to `{SCRATCHPAD}/.audit/findings/feynman-pass{N}.md`
