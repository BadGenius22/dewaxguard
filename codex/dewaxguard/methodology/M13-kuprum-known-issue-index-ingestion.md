---
id: M-13
name: kuprum-known-issue-index-ingestion
trigger_type: artifact
trigger_glob: "*KNOWN_ISSUES* *known_issues* *kuprum* *KNOWN-ISSUES* *known-issues*"
trigger_languages: [all]
applies_to_protocol_types: [any]
---
# M-13: Kuprum-style Known-Issue Index Ingestion (read 3rd-party dedup aids early)

> **Origin**: XRPL Sherlock April 2026, ingested mid-audit on day 10 of the contest window.
>
> **Trigger**: any competitive audit platform (Sherlock, Code4rena, Cantina, Immunefi) where other researchers produce shareable known-issue catalogs.
>
> **Yield**: DEL-1 (Medium, XLS-0075 pool hit) was discovered to be a duplicate of public GitHub issue #6890 only AFTER the kuprum index was ingested. The ingestion happened mid-audit — had it happened at the start, ~6 hours of PoC development would have been saved. Conversely, the ingestion ALSO confirmed 4 other Mediums (ESC-1/2/3, CONF-1) were unique and produced 3 Low candidates (L-30/31/32) dedup-clean, which made the eventual submission confidence sharply higher.

## What it is

**Kuprum-style index**: a non-authoritative catalog of known issues compiled by a third-party researcher (e.g., `kuprumxyz` for XRPL April 2026) that aggregates:

- Previous audit findings (Halborn / FYEO / etc. — expanded narrative summaries)
- Public GitHub issues created in the contest codebase repo BEFORE contest start
- Attack-branch specific findings on known project branches

For XRPL April 2026, the kuprum index had **186 finding entries across 2158 lines** — vastly more comprehensive than the official contest README's 7-issue baseline. Every audit platform has its version: Code4rena "known issues" comments, Sherlock "known issues" thread, private Watsons sharing catalogs.

## Trigger signals that one exists

- Search Twitter/X for `{contest name} known issues`
- Search GitHub gists for `{contest name}`, `{contest id}` — e.g., `site:gist.github.com xrpl sherlock april 2026`
- Search Discord/Telegram audit-alumni groups for shared catalogs
- Check the contest sponsor's own attack branch (e.g., `ripple/attackathon-*`) for issue traffic from other Watsons

## Why it matters

Contest rules almost universally declare "any public GitHub issue in the project repo opened before contest start = known issue = OOS." The official contest README often lists ~5-10 issues. A third-party index typically surfaces **10-100x more** pre-contest issues because:

1. Some issues are created BEFORE the official baseline cutoff but aren't linked from the contest README
2. Placeholder/vague issues (e.g., #6923 "Permission delegation no-op bypass patterns" — title only, no details) are NOT in the README but ARE pre-contest-start
3. Previous-audit findings are summarized (saves you reading 10 PDFs)

## Process (MANDATORY early in every competitive audit)

1. **Day 1-2**: search for kuprum-style indices. If any exist, fetch them.
2. **Day 2-3**: read the index top-to-bottom. Note every entry's issue-ID + ONE-LINE root cause.
3. **Day 3+**: during every domain run, pass the index reference to every breadth agent's pre-read list. Any finding candidate whose root cause matches an index entry gets immediate OOS classification.
4. **Before submission**: 3-layer dedup per M-10, but EXTENDED with the kuprum index as a 4th layer.
5. **For every candidate close to a vague placeholder entry** (e.g., "{topic} no-op bypass patterns" — title only, no body), build an explicit distinction section in the finding writeup. Vague placeholders are adversarial — a judge may classify your concrete finding as absorbed by the vague title.

## The ~22h-before-contest-start race

The highest-risk scenario: an index entry is created HOURS before contest start. In XRPL April 2026:

- Contest start: 2026-04-13 15:00 UTC
- Kuprum catalog's most-dangerous entries (#6890, #6893, the 10-issue Confidential MPT cluster #6867..#6882) were all created **2026-04-12 14:00..23:00 UTC** — within 24h of contest start.

Researchers who ingest the kuprum index early eliminate ~22h of wasted parallel work. Researchers who ingest late risk DEL-1-style surprises — in that audit, our DEL-1 was Medium-ready with a working PoC before discovering it duplicated #6890.

## Anti-patterns

- **DON'T treat the kuprum index as authoritative**. The official contest README is the legal baseline; the kuprum index just helps.
- **DON'T skip verification**. For every apparent-duplicate, fetch the GitHub issue's `created_at` and confirm it's truly before contest start.
- **DON'T abandon a close-but-not-identical finding**. Many kuprum entries describe a pattern, not a specific site — sibling instances at different code sites are often submittable. See CONF-1 vs #6869 / #6873 as a template.

## Cross-language mapping

| Platform | Equivalent |
|---|---|
| **Code4rena** | "Known issues" comments in the contest README + per-contest note files |
| **Sherlock** | Contest README + kuprum-style 3rd-party gists for popular contests |
| **Cantina** | Pre-published Cantina report of the same codebase (if any) + contest README known issues |
| **Immunefi** | Bug bounty prior-submission catalog (if the sponsor permits sharing) |

## Validated findings

- **XRPL April 2026**: DEL-1 (Medium) identified as OOS — kuprum #6890 created 22.5h pre-contest. Save = avoiding a rejected submission. Also confirmed ESC-1/2/3, CONF-1, L-30/31/32 as dedup-clean.

## Template placement

For XRPL April 2026, the ingested index lives at `context/KNOWN_ISSUES_INDEX_kuprum.md` in the audit workspace. Every breadth agent was instructed to read it as part of their MANDATORY pre-read list, alongside the manifest and contest FAQ.
