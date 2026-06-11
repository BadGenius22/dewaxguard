---
id: M-25
name: v12-style-ai-auditor-dedup
trigger_type: artifact
trigger_glob: "*V12*.md *zellic*.md"
trigger_languages: [all]
applies_to_protocol_types: [any]
---

# M-25 — V12-style AI-auditor finding-index pre-grep

> **Origin**: K2 Code4rena audit (2026-04 → 2026-05, Stellar Soroban). The audit shipped with Zellic V12 outputs as the official known-issue index: 183 findings across 3 files (Critical/High/Med-Low) totaling ~125k lines. Two false-positive findings (DD-5 "broken `update_atoken` caller forwarding" and L-09 "TTL-expiry → default-on-read") were investigated, PoC'd, written up, and only THEN discovered to be V12 duplicates. Combined wasted time: ~1.5 hours.
>
> **Trigger**: any competitive audit where the contest sponsor publishes a V12-style structured AI-auditor output (Zellic V12, similar emerging tools) as the official "known issues" index.
>
> **Yield class**: time-saving (negative-finding methodology). Eliminates duplicate investigation. Validates novel findings before submission.
>
> **Distinction from M-13 (Kuprum-style)**: M-13 covers *unstructured* third-party catalogs scraped from Twitter/Discord/Gist. V12 outputs are *structured* — every finding has consistent fields (Targets, Severity, Validity, Description, Root Cause, Impact, PoC, Invalid Reason). The structure enables mechanical pre-grep that M-13 doesn't. Use M-13 for human-curated catalogs, M-25 for AI-auditor outputs.

---

## The Pattern

V12-style outputs have three properties that change the dedup workflow:

1. **Volume**: hundreds of findings (V12 K2: 11 Critical + 73 High + 99 Med-Low = 183 total). Reading top-to-bottom is uneconomical.
2. **Structure**: every finding starts with `# Title` and `**#FindingID**` then has fixed fields. Greppable.
3. **Validity field**: marked `Unreviewed`, `Invalid`, or `Valid`. **The Invalid entries are the highest-value reading material** — they document why something LOOKS like a bug but isn't (platform semantics, public-entry-point reachability, etc.). My L-09 was invalidated by V12 #44792 "Expired position keys are treated as repaid or empty state" → marked Invalid because Soroban v23 auto-restores archived persistent entries; the test at ledger 650000 confirmed `get` returned live data, not zero.

If a contest's known-issue index is a V12-style structured output, the dedup workflow MUST include programmatic pre-grep before any PoC investment.

---

## When to Apply

| Trigger | Action |
|---------|--------|
| Contest README cites V12 / Zellic / similar AI-auditor as known-issue baseline | MANDATORY — apply at audit start AND before every PoC |
| Output files are >5MB total | MANDATORY — grep is the only economical access pattern |
| Output files include explicit "Invalid Reason" sections | MANDATORY — read these as a corpus before writing any finding |
| Single-finding writeup of ≥30 minutes | MANDATORY pre-grep before continuing |

---

## Process

### Phase 0: Audit-start preflight (mandatory)

1. **Locate V12 output files**. Common patterns: `K2-V12-Critical-output.md`, `{project}-V12-{severity}-output.md`. Confirm with `ls *.md | grep -iE "V12|zellic"`.
2. **Build header index**: `grep -nE "^# " {file}` for each file. Each match is one finding's title. Save count per severity tier.
3. **Build invalid catalog**: `awk '/^- Validity: Invalid/{print prev; print} {prev=$0}' {file}` — surfaces all Invalid-marked entries. Read each one's `Invalid Reason` field. These are the platform-semantic landmines.
4. **Cite in MEMORY.md**: write a one-line summary per Invalid entry. Future hypotheses that touch the same code area should re-read the cite.

### Phase 1: Pre-PoC dedup (mandatory before every Medium+ candidate)

For any finding candidate before writing a PoC:

1. **Extract keywords**: function names, file:line references, error variants, magic constants, contract names from the candidate's hypothesis.
2. **Grep V12 outputs**: use the helper script `scripts/grep_v12.sh` (see below) OR manually:
   ```bash
   grep -nE "^# " *V12*-output.md | grep -iE "{keyword1}|{keyword2}|{keyword3}"
   awk '/^# / {h=$0; ln=NR} /{file_under_investigation}/ {print FILENAME":"ln": "h}' *V12*-output.md
   ```
3. **For each match**: read the matched finding's full body. Check Targets, Validity, Description.
4. **Verdict**: 
   - **Match found, Validity=Valid or Unreviewed** → STOP. Per contest README, V12 findings are out of scope. Drop the candidate.
   - **Match found, Validity=Invalid** → READ the `Invalid Reason` carefully. If the reason explains why the bug is theoretical-only, the same reason may apply to YOUR finding too. If you proceed, your writeup must explicitly distinguish from the Invalid V12 entry's reasoning.
   - **No match found** → proceed to PoC.

### Phase 2: Pre-submission second pass (mandatory)

Even after Phase 1 passed, re-grep at submission time. Reasons:
- Your finding may have evolved during PoC development; new keywords may match a V12 entry you missed.
- A new keyword may emerge from the PoC itself (specific revert reason, etc.).

Re-grep the FINAL keywords from the writeup before submitting.

---

## Programmatic helper

The companion script `scripts/grep_v12.sh` automates Phase 1 step 2:

```bash
./scripts/grep_v12.sh <keyword> [more keywords...]
```

Output: per V12 file, finding IDs + severity + validity + 1-line Description for every header that contains any keyword OR any body that contains all keywords.

Use `--strict` for AND-mode (all keywords must match), default is OR-mode.

---

## Validated examples (K2 audit)

| Avoided dup | V12 entry | What I almost did | What V12 said |
|-------------|-----------|-------------------|---------------|
| **DD-5** "Broken `update_atoken` caller forwarding bricks token upgrades" | #44797 ("Wrong actor forwarding bricks token upgrade flows", Medium, Unreviewed) | Wrote a PoC test, ran it (passed), drafted a Medium submission writeup | Same root cause: pool-configurator passes pool_admin EOA where router expects pool_configurator contract address. Same fix. |
| **L-09** "Persistent storage entries flip to no-restriction on TTL expiry" | #44792 ("Expired position keys are treated as repaid or empty state", Critical, **Invalid**) | Wrote a 4-row finding (debt_ceiling, whitelist, blacklist, deficit), inserted into QA-Bundle | Soroban v23 auto-restores archived persistent entries — `get()` returns the original value, not the default. Verified at ledger 650000. |

In both cases, a 10-second pre-grep would have killed the candidate before investigation. Combined time saved: ~1.5h.

The L-09 case is more interesting: V12's Invalid entry was actively useful as platform-semantics reference. Reading it shaped my understanding of Soroban v23 storage. **Invalid V12 entries are not noise — they are platform-knowledge cards.** Always read them.

---

## Anti-patterns

1. **Reading V12 outputs top-to-bottom at audit start** — uneconomical. Use header-grep + invalid-only first pass.
2. **Skipping V12 grep on "small" findings** — DD-5 was Medium-class severity (had it been valid). Even Low candidates deserve a 10-second grep.
3. **Treating V12 as Kuprum (M-13)** — M-13's process assumes ~50-200 entries with narrative summaries. V12 has structured entries; use this methodology instead.
4. **Ignoring `Invalid` entries** — the highest-leverage V12 content. Each Invalid entry is a saved future audit hour.
5. **Not citing in MEMORY.md** — the next session needs the same Invalid catalog you built; persist it.

---

## Cross-language applicability

- **EVM / Solidity**: AI auditors increasingly producing structured outputs (Cantina/Sherlock auto-summary panels, Code4rena bot-finding pre-publish lists). Same workflow applies.
- **Solana / Anchor**: V12 covers Solana too. Same methodology.
- **Stellar / Soroban**: K2 was the validating audit.
- **Move (Aptos / Sui)**: V12 is multi-language. When V12 outputs ship for a Move audit, this methodology applies.
- **C / C++ (rippled, Bitcoin Core)**: kuprum-style indices typical (M-13). If V12 emerges for these, this methodology applies.

---

## Integration with existing methodologies

- **M-10 (3-layer dedup)**: extend with a 4th layer "V12 grep" before submission.
- **M-13 (Kuprum-style)**: complementary, not redundant. A contest may have BOTH V12 (official) and a kuprum-style index (community). Run both.
- **M-24 (Fresh-eyes sweep)**: M-24 surfaces uncovered surfaces; M-25 verifies those surfaces aren't already V12'd. Run M-25 BEFORE M-24's PoC stage.
- **Per-audit MEMORY.md**: V12 invalid-catalog one-liners persist into MEMORY.md and re-load on session resume.
