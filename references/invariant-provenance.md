# Traceable invariants and lifecycle analysis

Read during recon/protocol modelling when accounting, state transitions or
external dependencies matter. Depth agents read the resulting property records,
not a new catalogue of bug patterns. This adapts Pashov X-Ray v2 and Fizz v1 at
`8ce544c9c9affab448d3dc4c79191d052e3a57ec`.

## Recon evidence

Add compact evidence rows to the existing `invariant-extract.md`,
`state-flags.md`, `integration-map.md` and `design_context.md`:

- **Delta writes:** storage variable, function, symbolic change and `file:line`.
  Resolve helper effects only after reading their implementation. Unread
  inherited/custom helpers remain unknown. Do not infer conservation merely
  because two writes occur nearby; account for intervening calls and reverts.
- **Storage guards:** exact predicate and citation; identify the write sites
  that can invalidate it. A local `require` is a call precondition, not evidence
  that the relation holds after all operations.
- **Transitions:** before-state guard, after-state write, role and citations.
  Include one-time initialization, role handoff, pause, shutdown and upgrades
  where in scope. Deployment scripts affect configuration and ownership; inspect
  them as source, never execute them as a discovery step.
- **Lifecycle/dependencies:** identify the applicable deployment, normal-use,
  market-stress, upgrade and wind-down windows. For each relevant dependency,
  record the caller's assumption and the callee evidence. Changed governance,
  token behavior, shared liquidity or oracle inputs can invalidate an assumption.
- **Git signals (optional):** changes reachable from audited HEAD may prioritize
  review. Cite commit and source lines; shallow/missing history stays unknown.
  Churn, author counts and test co-change are not vulnerability or coverage proof.

## Property records in the blind model

Extend `{SCRATCHPAD}/protocol-model.md` with stable `I-N` property records. Keep
the existing findings-blind input boundary. Each record carries:

| Field | Meaning |
| --- | --- |
| `id`, `statement`, `category` | Stable ID and precise guard/local/global/cross-system/economic claim |
| `basis` | `SPEC-STATED`, `CODE-DERIVED` or `EXPLORATORY`; independent of priority |
| `evidence` | Spec/code citations and a derivation; both sides of a cross-system claim |
| `write_sites` | Relevant writers and transitions; unread sites explicitly unknown |
| `enforcement` | Cited enforcing checks or `NOT ENFORCED IN CODE` / `UNKNOWN` |
| `actors`, `domain` | Reachable roles, assets, lifecycle states and supported token assumptions |
| `observable`, `failure_witness` | Independent state/delta to measure; concrete violation that would fail the assertion |
| `validation` | `NOT RUN`, or exact authorized receipt and result; no automatic verdict |

Before lifting a guard into a global invariant, inspect every relevant writer.
Economic properties derive from identified accounting/state properties, not
generic claims like "nobody should ever lose money". A stated guarantee can be
wrong or out of scope; its violation still needs harness, reachability, harm and
eligibility checks. An exploratory property tests a hypothesis, not a promise.

Attack-surface rows reference property IDs. During depth, record the tested or
traced path against each ID and carry unknowns into `negative-space.md`. An
unsupported dependency assumption stays unknown rather than being called safe.

## Turn a property into meaningful targeted validation

These are design rules for an authorized candidate PoC, not permission to run a
fuzz campaign. Read `rules/execution-policy.md` before any target execution.

1. Select the smallest real action sequence that exercises the suspected
   lifecycle edge. Include normal keeper/admin transitions when the defect
   depends on them; do not fabricate attacker privileges.
2. Use before/after snapshots at named victim, attacker and protocol accounts.
   A failed snapshot read invalidates the observation: do not replace it with
   zero or swallow an exception into a passing assertion.
3. Track cumulative flows with ghost state only if an assertion needs it. Update
   ghosts after successful calls, including each successful leg of a sequence.
   The expected result must be independent of the suspected faulty formula.
4. Record successful action counts and state changes. A sequence that only
   reverts or never enters the relevant state cannot validate the property.
   Separate actor-only losses from involuntary victim harm.
5. Bound input domains by real balances, roles and supported states. Clamping
   every input into the safe region hides boundary defects; where relevant,
   exercise an unmodified adverse input and explain why it is reachable.
6. Require the existing positive-control, mutation, real-path and assertion
   receipts. No property violation automatically becomes a valid finding, and
   a passing sequence proves only its measured path and property.

Do not import Fizz installers, Echidna/Medusa campaigns, automatic coverage runs
or auto-confirmation rules. Learning-only sessions can write property designs
and analyse existing tests without compiling or executing the target.
