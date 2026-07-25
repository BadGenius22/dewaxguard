---
id: M-10
name: prior-audit-dedup
trigger_type: process
trigger_event: "pre-submission — before marking a finding submission-ready, run 3-layer dedup (prior audits / project issue tracker / remediation status)"
trigger_languages: [all]
applies_to_protocol_types: [any]
---

# M-10: Pre-Submission 3-Layer Dedup

**Origin**: XRPL Sherlock April 2026 — validated during final submission prep. 4 Mediums passed clean against 4 prior audit reports + GitHub baseline.

**One-line**: Before marking any finding submittable, run a 3-layer dedup sweep (prior audits / project issue tracker / remediation status). ~10 minutes per 4 Mediums; prevents wasted submissions and negative quality signals.

## Trigger

Apply once per finding, after PoC is running and before calling it "submission-ready". Mandatory for any paid-contest submission (Sherlock, C4, Cantina, Immunefi).

## The Three Layers

### Layer 1: Prior audit reports

1. **Identify prior audits** listed in the contest README or announced in Discord.
2. **Fetch each one** (WebFetch for HTML; curl + pypdf for PDFs).
3. **Extract structurally**: title, severity, 1-sentence root cause.
3a. **Also extract the report's own SCOPE** — its audited file list, plus its `Audited Commit → Final Commit` pair if stated. Write to `{SCRATCHPAD}/prior_audit_scopes.md`, one section per report. Two payoffs beyond dedup: (i) when a report's Final Commit equals the contest's scope commit, the code on disk IS the post-fix state those reviewers signed off on — so blanket per-finding fix-tracing is unnecessary, and diffing the two file lists tells you whether you are looking at point fixes or an architecture rewrite (prior findings targeting now-deleted files are moot); (ii) the file list feeds the coverage diff at **M-24 Phase 1 item 9**, which is where never-externally-reviewed code gets identified. Cheap — the reports are already fetched and parsed at step 2.
4. **Match** against your finding:
   - Same transactor / function name? **Investigate deeper**, not automatic duplicate.
   - Same root cause mechanism? **LIKELY DUPLICATE**.
   - Same fix required? **LIKELY DUPLICATE** (matches contest judging consolidation rules).
5. **Remediation-status check**: if prior audit finding is marked "Remediated" / "Fixed", check the current commit still contains the bug pattern.

### Layer 2: Project issue tracker baseline

Most contests specify a cutoff date — anything public before that date = known issue.

1. **Get the cutoff** (from contest README or FAQ).
2. **Enumerate public issues/PRs** on the project's GitHub before cutoff.
3. **Grep-search** the title list for your finding's keywords (function names, error codes, flag names).
4. **For matches**, read the issue/PR thread to verify mechanism match.
5. **Known-issue lists** in platform-quirks files (e.g. `~/.claude/skills/dewaxguard/platform-quirks/cpp.md` has XRPL #6863/#6867/#6875/#6884/#6894/#6895/#6908) are pre-curated shortcuts — check them first.

### Layer 3: Finding classification matrix

Cross-reference per-finding × per-prior-audit in a dedup table:

| Finding | Halborn Batch | Halborn MPT DEX | FYEO PD | FYEO SF | GH baseline | **Verdict** |
|---------|---------------|-----------------|---------|---------|-------------|-------------|
| ESC-1 | clean | clean | clean | clean (different SLE surface) | clean | **NOT DUPLICATE** |
| ESC-2 | clean | clean | clean | clean | clean | **NOT DUPLICATE** |
| ...   | ... | ... | ... | ... | ... | ... |

## Process (~10 minutes per 4 Mediums)

1. **Preparation** (~2 min): list finding IDs + root-cause 1-liners + location cites.
2. **Fetch audits** (~3 min): parallel WebFetch / curl.
3. **Extract** (~2 min): ask the WebFetch prompt for "title + severity + 1-sentence root cause per finding" — structured output saves time.
4. **Match** (~2 min): construct the matrix.
5. **Verdict** (~1 min): per finding, record dedup status + reasoning.

## Cross-platform mapping

| Contest | Prior audits location | Issue-baseline location |
|---------|----------------------|------------------------|
| **Sherlock** | Linked in contest README | GitHub org repo issues; cutoff in README/FAQ |
| **Code4rena** | `README.md` "Previous audits" section | GitHub issues; no cutoff — all time |
| **Cantina** | Cantina cover page "Previous audits" | Project GitHub |
| **Immunefi bounty** | Program description | Project issue tracker |

## Fetch commands

### HTML audit pages (Halborn-style)
```bash
# Use WebFetch directly; works for auditor-hosted reports.
```

### PDF audit reports (FYEO-style, GitHub-hosted)
```bash
# WebFetch to GitHub redirects — follow to raw.githubusercontent.com
# Then:
pip install pypdf --quiet
curl -sL "https://raw.githubusercontent.com/.../report.pdf" -o /tmp/report.pdf
python3 -c "
from pypdf import PdfReader
r = PdfReader('/tmp/report.pdf')
for i, p in enumerate(r.pages):
    print(f'=== PAGE {i+1} ==='); print(p.extract_text()[:3000])
"
```

## Anti-patterns

- **Don't skip for "obvious" novelty**. Your finding may be novel to you but known internally. Always fetch.
- **Don't dedup based on titles alone**. "MPToken escrow path" can mean sponsor-field attribution or balance-check — read the root cause section.
- **Don't treat "Remediated" as "can't be duplicated"**. The fix may be incomplete or partially reverted in the delta under review.
- **Don't rely on cached tool results from weeks ago**. Contest info evolves; re-fetch for current submission.

## Validated application

**XRPL Sherlock April 2026 dedup sweep** (2026-04-17):
- Input: 4 Medium findings (ESC-1/2/3, CONF-1) + 4 prior audits (Halborn Batch/MPT DEX, FYEO PD/SF) + 7 GitHub baseline issues
- Duration: ~10 minutes total
- Output: all 4 findings cleared as NOT DUPLICATE with explicit per-layer reasoning

## Related methodology

- **M-04 feature-pool coverage**: always apply BEFORE dedup, so the finding has a clean feature label to classify under.
- **M-05 / M-06 submission structure** (TBD methodology docs): dedup is the last step before submission. After dedup clean, move to submission markdown.
