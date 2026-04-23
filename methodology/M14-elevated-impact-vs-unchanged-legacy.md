# M-14: Elevated-Impact vs Unchanged-Legacy Judgment

> **Origin**: XRPL Sherlock April 2026, Domain 14 (dev test diff as design oracle), L-32 candidate analysis.
>
> **Trigger**: you find a concrete bug in code that is UNCHANGED between pre-delta and post-delta, BUT a new amendment introduced a new code path / feature / input shape that makes the pre-existing bug MORE REACHABLE or MORE IMPACTFUL.
>
> **Yield**: prevents weak submissions that collapse on "unchanged legacy code" OOS rulings. The earlier you run this check, the less wasted PoC development.

## The decision problem

Contest rules universally have some variant of:

> "Only NEW or ELEVATED impact vs baseline is in scope. Pre-existing bugs with unchanged impact are OOS."

This creates a 2×2 decision matrix for any candidate:

| Code changed? | Impact changed? | Verdict |
|---|---|---|
| YES | YES | **IN-SCOPE** (clear case) |
| YES | NO | **IN-SCOPE** if the new code has its own bug independent of impact class |
| NO | NO | **OOS** (clear unchanged-legacy) |
| **NO** | **YES** | **CONTESTED** — this is the M-14 decision zone |

The bottom-left cell (code unchanged, impact elevated) is where M-14 lives. You need a clear argument for IN-SCOPE to survive judge review.

## Concrete example: L-32 (XRPL 2026-04)

**The bug**: `AccountObjects.cpp:223` `if (++i == mlimit)` — pagination counter increments on EVERY loop iteration, regardless of whether the entry passed the filter and was appended.

**Pre-delta reality**: The code had the same `++i == mlimit` placement, with a `typeFilter` option that rarely excluded many entries (most user queries for `account_objects` don't specify a type filter, or the filter is narrow enough that page-exhaustion is an edge case).

**Post-delta reality**: A new `sponsored` filter (part of XLS-0068 Sponsored Fees integration) was added. The new filter is much more AGGRESSIVE — most user accounts have few sponsored objects, so the pagination drain moves from "rare edge case" to "common-case failure".

**The M-14 argument**: code at L223 is unchanged (so OOS on its face), BUT the NEW sponsored filter elevates the impact from edge-case UX glitch to common-case pagination breakage. This is an ELEVATED IMPACT finding under the contest's new-or-elevated rule.

**The honest risk assessment**: a Sherlock judge may rule EITHER way. The argument is coherent but judge-dependent.

## When elevated-impact arguments succeed

Strong when:
1. The pre-delta impact was THEORETICAL or EDGE-CASE (no real-world victim existed)
2. The new code makes the scenario COMMON-CASE (the majority of typical users / operations hit the bug)
3. You can quantify the shift (e.g., "pre-delta: 0 observed reports in 5 years; post-delta: any account with <10 sponsored objects")
4. The new amendment is explicitly advertised as supporting the use case the bug breaks

Weak when:
1. The pre-delta impact was already observable (just not reported)
2. The shift is from "rare" to "slightly less rare"
3. You have no way to quantify the common-case frequency
4. The new amendment is orthogonal to the buggy code path

## When elevated-impact arguments fail

- The bug has a pre-delta issue report / GitHub issue / existing audit finding → automatic OOS
- The new code path has its OWN independent guard that prevents the impact
- "Common case" is defined relative to rare user behavior (e.g., delegated sponsored multisig — not a common deployment)

## Process

1. **Isolate the bug** to a specific code site. Get file:line precision.
2. **Diff the site** between pre-delta and post-delta. Confirm the BUGGY LINES are unchanged.
3. **Identify the reachability source** — what new amendment / new code introduces new callers / new input shapes that make this bug more hit-able?
4. **Quantify pre-delta vs post-delta severity distribution**:
   - Pre-delta: typical-user hit rate ≈ X
   - Post-delta: typical-user hit rate ≈ Y
   - Ratio Y/X is your elevation argument
5. **Build the writeup** with an explicit "Elevated-impact argument" section that addresses the unchanged-legacy concern head-on. Don't hide it; a judge will find it anyway.
6. **Set expectations honestly** — flag the submission as RISKY in your own internal notes. If you have time-constrained options, prioritize clearly NEW-code findings first.

## Sherlock-specific nuances (as of 2026)

- Sherlock judges tend to be strict on unchanged-legacy. A clear ELEVATED-IMPACT argument is required, not just a passing mention.
- An entry in any 3rd-party known-issue index (see M-13) that mentions the general area of the bug raises the OOS risk further.
- Cantina judges tend to be more lenient (my anecdotal read as of 2026-04).

## Anti-patterns

- **DON'T use M-14 to rescue a weak finding**. If your candidate is an obvious stretch, don't dress it up with M-14 language — the judge will see through it.
- **DON'T mix M-14 with a "CONTESTED" severity**. If you're arguing ELEVATED IMPACT, commit to a specific severity. "Low-or-Medium-depending-on-judge" is worse than clear Low.
- **DON'T submit without the elevation quantification**. An unquantified "this is now more common" is not compelling.

## Cross-language mapping

| Platform | Equivalent contest rule |
|---|---|
| **Sherlock** | "Only new or strictly elevated impact vs baseline" |
| **Code4rena** | Usually "scope = specific commit range" — unchanged code outside the range is OOS |
| **Cantina** | Typically "all code in scope unless explicitly excluded" — less M-14 ambiguity |
| **Immunefi** | Bounty per-severity — elevated impact often recognized via "novel attack vector" rating |

## Validated findings

- **XRPL 2026-04 L-32**: `account_objects sponsored` filter drains pagination. M-14 argument built; submission held pending user decision. Not yet submitted — outcome TBD.

## Anti-validation (saves)

- When to NOT use M-14: if the pre-delta impact was already DOCUMENTED (in any form — issue, audit, blog post, known-issue index), M-14 is blocked. The finding is OOS regardless of new reachability, because the bug itself was public knowledge.
