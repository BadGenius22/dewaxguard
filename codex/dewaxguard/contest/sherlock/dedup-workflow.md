# Sherlock Pre-Submission Dedup Workflow

> Mandatory final step before submitting. See [M-10](../../methodology/M10-prior-audit-dedup.md) for cross-platform methodology.

## Sherlock-specific inputs

Sherlock contest READMEs typically list prior audits in one of:
- A "Previous audit reports" section
- A FAQ / judging-update announcement
- A Discord pin

Always check all three.

## Process

1. **Fetch prior audits**.
   - HTML reports (Halborn-style): direct WebFetch.
   - PDF reports (FYEO-style, GitHub-hosted): follow redirect to `raw.githubusercontent.com`, then curl + pypdf.
2. **Extract structurally**:
   - Ask WebFetch: "List every finding: title + severity + 1-sentence root cause. Then verify NONE of these concepts are covered: [your 5 concepts]"
3. **GitHub issue baseline**:
   - Sherlock READMEs specify a cutoff like "before April 13th 3:00 PM UTC"
   - Enumerate issues / PRs before cutoff via `gh issue list --state all --search "{keyword}" --repo {org}/{project}`
   - Check `~/.agents/skills/dewaxguard/platform-quirks/{lang}.md` for pre-curated known-issue lists
4. **Per-finding matrix**:

   ```
   | Finding | Prior1 | Prior2 | ... | GitHub baseline | Verdict |
   |---------|--------|--------|-----|-----------------|---------|
   | ESC-1   | clean  | clean  | ... | clean           | NOT_DUP |
   | ...     | ...    | ...    | ... | ...             | ...     |
   ```

5. **Per-finding reasoning** — for anything not marked `clean`, add a sentence explaining the structural difference (same surface ≠ same root cause).

## Fetch scripts (validated April 2026)

```bash
# Halborn HTML
# Use WebFetch directly with prompt:
#   "List every finding: title + severity + 1-sentence root cause.
#    Verify NONE of these concepts are covered: [list]"

# FYEO PDF via GitHub
curl -sL "https://raw.githubusercontent.com/fyeo-io/public-audit-reports/main/Code%20Audit%20Reports/YEAR/Ripple/REPORT_NAME.pdf" \
     -o /tmp/fyeo_report.pdf
pip install pypdf --quiet
python3 -c "
from pypdf import PdfReader
r = PdfReader('/tmp/fyeo_report.pdf')
for i, p in enumerate(r.pages):
    print(f'=== PAGE {i+1} ==='); print(p.extract_text()[:3000])
"
```

## Self-invalidation policy

If your finding IS a duplicate, Sherlock's judging update from April 2026 explicitly rewards self-invalidation:
> "please re-check your submitted findings. If you find what you describe in the list of known issues, you would do me a great service if you invalidate your finding yourself. For that you only need to close the issue in your private repo."

Self-invalidation preserves quality rating. Ignoring a known-dup and submitting anyway harms your Watson score.

## Anti-patterns

- **Don't rely on my prior claims** — "I already dedup'd" from a stale session is not valid; re-run for current submission.
- **Don't treat `Remediated` status as immune** — the fix may be incomplete. Verify the current-commit code against the described bug pattern.
- **Don't assume "not in prior audit" = novel** — some bugs are in Discord pins / FAQ items / protocol-team known lists. Search those too.

## Sherlock-specific quality signal

From CONTEST_FAQ April 2026: "Live Issues Enabled" means real-time triage. Submit quickly after validation, but only after dedup. Submitting a dup loses weight; submitting quickly after clean dedup preserves your early-finder status.
