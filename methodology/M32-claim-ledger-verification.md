---
id: M-32
name: claim-ledger-verification
trigger_type: process
trigger: "final submittable candidates only — every finding scoring >= 70 in Phase 5d, before it enters the report"
trigger_languages: [all]
applies_to_protocol_types: [any]
recon_flags: []
---

# M-32 — Claim-Ledger Verification (adversarial, line-by-line, on final candidates)

> **Purpose**: before a finding is written to the report, decompose it into its **atomic factual claims** and verify EACH one against source (`file:line`) — never assume, never credit an unverified assertion. The output is a **verification ledger** (claim → source line → VERIFIED / REFUTED / JUDGMENT) plus a one-line **verification-debt** verdict. The goal is to separate what the code *proves* from what is *interpretation*, so a finding ships with zero unverified mechanical claims and its residual risk is known to be pure judge-discretion.
>
> **Origin**: Metric OMM re-audit (Sherlock #1279, 2026-07). A one-directional skeptical pass (`bug-validator`) had tentatively concluded one finding's *mechanism* might be misidentified; an adversarial line-by-line claim-verification pass refuted that from source (the alleged wrong-oracle was correct; the missing-tolerance gap was real and code-confirmed), and separately surfaced a leaked internal ID in a PoC. The net lesson: the existing Gate-2 enabler check verifies *preconditions*; it does not verify *every* mechanical claim (the mechanism chain, the dedup claims, the severity-basis claims). M-32 closes that gap for final candidates only. (RC-METHOD; extends Phase 5d Gate 2.)
>
> **Relationship to the judge you already have**: this EXTENDS `bug-validator` Phase 5d Gate 2 (`enabler_check`) — it does not replace it. Gate 2 verifies load-bearing enablers; M-32 verifies the whole claim set and emits the ledger. Run it AFTER a finding scores >= 70, not on every candidate (cost control).

---

## When to apply (and when NOT to)

- **Apply**: only to findings that survive Phase 5d with score >= 70 (FINDING-class), before Phase 6 report / submission. These are the candidates whose per-claim cost is justified.
- **Do NOT apply**: as a breadth/depth stage, or to every candidate, or to LEAD/excluded findings. It is a final gate, not a discovery tool.
- **Do NOT use it to re-litigate severity**: M-32 *classifies* a claim as JUDGMENT when it is not a code fact; it does not resolve the judgment. Severity stays with the severity-decision-tree and M-27. M-32's job is only to prove the mechanical claims and quarantine the interpretive ones.

---

## Method

### STEP 1 — Decompose into atomic claims
Extract every factual assertion the finding depends on, across four buckets:
1. **Mechanism chain** — each link from root cause to impact ("X reverts", "Y is credited to Z", "the call reaches W").
2. **Precondition/enabler** — actors, settable params, external state (this overlaps Gate 2 — reuse its result, don't redo).
3. **Distinctness/dedup** — "not known issue N", "different contract/branch/fix than prior-audit finding M".
4. **Severity basis** — the specific rule/clause the claimed severity rests on (README line, invariant, threshold).

Write each as a one-line, checkable statement. Vague claims ("the design is unsafe") are not verifiable — split them until each is a concrete `file:line`-checkable fact.

### STEP 2 — Verify each claim adversarially, from source
For EACH claim run a two-sided check and let the code decide:
- **Refute pass** (judge): try to falsify the claim by reading the actual source. Look for the missing guard, the sibling that behaves differently, the overload that changes the answer.
- **Defend pass** (white-hat): confirm the claim by reading the actual source.
- **The code decides.** Cite the exact `file:line` that settles it. **Never mark a claim VERIFIED without a citation, and never credit a rebuttal (either direction) you have not confirmed in source.**

Classify each claim:
| Verdict | Meaning | Consequence |
|---------|---------|-------------|
| **VERIFIED** | source line confirms the claim | claim stands; cite the line |
| **REFUTED** | source line contradicts the claim | if load-bearing → finding **dies or downgrades**; fix the writeup |
| **JUDGMENT** | not a code fact (severity call, runtime/economic interpretation, off-chain timing, judge discretion) | quarantine — do NOT present as fact; it becomes the finding's known residual risk |

### STEP 3 — Emit the verification ledger
Write to `{SCRATCHPAD}/verify_ledger_{finding_id}.md`:

```markdown
# Verification Ledger — {finding id / title}
| # | Claim | Source (file:line) | Verdict |
|---|-------|--------------------|---------|
| 1 | {atomic claim} | Foo.sol:123 | VERIFIED |
| 2 | {atomic claim} | Bar.sol:88 (no such check) | REFUTED |
| 3 | {severity rests on README line 99} | — | JUDGMENT |

**Verification debt**: {none | N unverified/refuted load-bearing claims}
**Residual (JUDGMENT-only) risk**: {1-line list — the interpretive questions a judge, not the code, decides}
```

### STEP 4 — Gate on the ledger (HARD)
- **Every VERIFIED row has a `file:line`.** A VERIFIED with no citation is not verified — re-do it.
- **A REFUTED load-bearing claim blocks submission** until the writeup is corrected (or the finding is dropped).
- **The JUDGMENT section must be non-empty and honest.** A finding claiming *zero* interpretive residual is a red flag — either a JUDGMENT claim was mislabeled VERIFIED, or the severity basis was not examined. Re-check.
- **Verification debt must be `none`** before the finding enters the report.

---

## Anti-theater rules (the value is the citations, not the debate)

1. The two-sided pass is a discipline, not a script — if "judge" and "white-hat" agree without a `file:line`, nothing was verified.
2. Do not paraphrase the finding's own writeup as evidence — read the *source*, not the submission's quotes of it (the two can diverge; the Metric session caught a leaked ID and a stale claim this way).
3. One REFUTED load-bearing claim outweighs ten VERIFIED cosmetic ones — weight by whether the claim is load-bearing for impact.

---

## Cross-language mapping

The ledger is language-agnostic; "verify against source" means reading the real code in whatever language:

| Bucket | EVM (Solidity) | Solana (Rust) | Move (Aptos/Sui) |
|--------|----------------|---------------|------------------|
| Mechanism link | `revert`/`require`/storage write at `Foo.sol:L` | `require!`/`return Err`/account write at `lib.rs:L` | `abort`/`assert!`/resource write at `module.move:L` |
| Enabler | caller-supplied vs storage-set param | `Signer`/PDA-owned vs `AccountInfo` arg | `&signer` vs public entry arg |
| Dedup | diff vs prior-audit contract/branch/fix | same, per program | same, per module |
| Severity basis | README clause / invariant | README clause / invariant | README clause / invariant |

---

## Related

- **`bug-validator` Phase 5d Gate 2 (`enabler_check`)** — M-32 extends it from load-bearing enablers to the full claim set; reuse Gate 2's enabler result as ledger bucket 2.
- **`rules/severity-decision-tree.md` + M-27** — own the severity JUDGMENT rows; M-32 only quarantines them, it does not resolve them.
- **`rules/fork-poc-execution.md` §6** — a `[FORK-PASS]`/`[POC-PASS]` is the mechanical proof a mechanism-chain claim VERIFIES against; a bare `expectRevert` is not (verify the revert originates from the exploit path).
- **`refuted/INDEX.md`** — the dedup bucket (claim type 3) checks candidate claims against documented refuted/known-issue classes.

## Validated in

- Metric OMM (Sherlock #1279, 2026-07): three final candidates each decomposed into ~5-6 atomic claims and verified line-by-line; all mechanical claims VERIFIED (zero verification debt), residual isolated to judge-discretion (severity + one runtime-timing item). Surfaced one REFUTED-then-corrected mechanism assumption and one leaked internal PoC ID that a one-directional score pass had missed.
