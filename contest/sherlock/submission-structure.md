# Sherlock Submission Structure

> Mandatory layout for every Sherlock-contest finding markdown. Derived from XRPL April 2026 audit practice.

## Required sections (in order)

1. **Title** — `# {ID}: {One-line root cause}` — ID format e.g. `ESC-1`, `CONF-1`, `H-01`.
2. **Feature label** — `**Feature**: {Feature pool name} ({XLS spec ID})` — immediately after title. Follow with a paragraph explaining root-cause code path's feature-amendment gate, and the PoC's tie-in transaction.
3. **Severity** — `**Severity**: Critical / High / Medium / Low / Informational`
4. **Status** — `**Status**: New in the {contest-delta} ({commit range}). {Sentence explaining what was new in the delta that enabled this attack}.`
5. **Summary** — plain-language description of the bug. Code snippet of the bad code with file:line.
6. **Root cause** — 1-paragraph structural explanation.
7. **Contest scope discussion** — quote relevant README trust-model rules. Defend the finding's scope-eligibility.
8. **Attack cost** — bullet list with specific fees + reserves.
9. **Impact** — numbered list of distinct consequences.
10. **Proof of Concept**
    - **What the PoC does** — numbered step list
    - **The code artifact** — must be preceded by a copy-to-file BANNER:
      ```
      > **👉 COPY THE ENTIRE `cpp` BLOCK BELOW AND SAVE IT AS A NEW FILE AT:**
      > **`rippled/src/test/app/MyTest.cpp`**
      ```
      Then the full source inline in a ```cpp fenced block.
    - **How to apply** — plain instructions (save to X path; CMake auto-globs).
    - **Prerequisites** — standard dev env + built repo + no extra deps.
    - **How to run** — exact shell commands with comments.
    - **Expected output** — sample run text. Include FTL log lines if applicable.
    - **Sample from my own run** — reproduction of the same output, showing you ran it.
11. **Recommendation** — 2-3 fix options in order of preference, with code snippets where short.
12. **References** — every file:line cited anywhere in the finding.

## Why this structure

- **Feature label first** → judge classifies to reward pool without reading further.
- **Status field** → establishes "new in delta" eligibility per Sherlock scope rules.
- **Copy-to-file banner before code** → reviewer cannot miss where the PoC goes.
- **Prerequisites + How-to-run + Expected output** → reviewer reproduces without thinking.
- **Sample from my own run** → proves you actually ran it; FTL log lines match expected tec codes.

## PoC code block requirements

- **Inline** (not attached as separate file). Sherlock judges read markdown-only.
- **Self-contained** — no imports from other changed files. If you modified another file, include its diff too.
- **Auto-globbed build target** preferred — `BEAST_DEFINE_TESTSUITE` for XRPL, Hardhat/Foundry standard paths for EVM, Anchor `#[cfg(test)]` module for Solana.
- **Comment banner at top of cpp/rs/move source**:
  ```
  // ===========================================================
  //  SAVE THIS FILE AS: {exact/path/to/file.ext}
  // ===========================================================
  ```
- **Expected output section MUST include assertions that prove the bug**. "0 failures" on a negative test asserting `INVARIANT_FAILED` is the standard.

## Anti-patterns

- **Don't put patches in a separate file** — Sherlock doesn't support attachments.
- **Don't use `/path/to/findings/X.patch` placeholder** — reviewers copy-paste literally.
- **Don't omit the feature label** — if the PoC doesn't touch a reward-pool XLS spec's tx, apply [M-04](../../methodology/M04-feature-pool-coverage.md) first.
- **Don't skip dedup** — always run [M-10](../../methodology/M10-prior-audit-dedup.md) before declaring submittable.

## Length guide

| Severity | Recommended length |
|----------|-------------------|
| Critical | 400-600 lines inc. PoC |
| High | 300-500 lines |
| Medium | 250-450 lines |
| Low | 150-300 lines |
| Informational | 100-200 lines |

PoC inline typically adds 150-250 lines.

## Checklist before submission

```
[ ] Feature label with XLS spec ID and reward-pool name
[ ] Status paragraph explaining new-in-delta impact
[ ] Summary with bad-code snippet + file:line
[ ] Root cause paragraph
[ ] Contest-scope discussion quoting README rules
[ ] Attack cost bullets with concrete fees/reserves
[ ] Impact numbered list with distinct consequences
[ ] PoC: What-it-does numbered steps
[ ] PoC: Copy-to-file banner above fenced cpp block
[ ] PoC: Full source inline
[ ] PoC: How-to-apply instruction
[ ] PoC: Prerequisites list
[ ] PoC: How-to-run commands
[ ] PoC: Expected output with assertion matches
[ ] PoC: Sample-from-own-run evidence
[ ] Recommendation with 2-3 fix options
[ ] References section with every file:line
[ ] Dedup verdict (internal note or appendix) — run M-10
```
