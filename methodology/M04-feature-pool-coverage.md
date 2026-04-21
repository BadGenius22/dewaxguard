# M-04: Feature-Pool PoC Coverage

**Origin**: XRPL Sherlock April 2026, Domain 4 — derived from CONTEST_FAQ feature-labeling requirement + ESC-1 classification.

**One-line**: When a finding's root cause lives in shared infrastructure, extend its PoC with a transaction that exercises a specific reward-pool feature — so the judge can cleanly classify it.

## Trigger

Apply when **all** of the following hold:
1. The contest has **separated reward pools by feature** (Sherlock contests often; Code4rena bounty-pool style).
2. The finding's **root cause code path** lives in a shared helper / base layer, not a feature-specific transactor.
3. The **naive PoC** (minimum reproducer) uses only base-layer transactions that don't tie to any specific feature XLS/spec.

## Process

1. **Map** the root-cause code path to its amendment / feature flag gate (e.g. `featureMPTokensV2` → XLS-0082 MPT DEX).
2. **Identify** which reward-pool feature the gate belongs to.
3. **Find** a signature transaction from that feature's XLS spec (e.g. `OfferCreate` with `TakerGets=MPT` for MPT DEX).
4. **Extend** the PoC with that transaction BEFORE or DURING the exploit sequence — even if it doesn't directly participate in the exploit.
5. **Document** in the finding: "The PoC exercises XLS-XXXX transactions directly in test case N, tying the root cause to the {feature} reward pool via {tx type}."
6. **Judge-proof**: state in the feature-label paragraph WHY the finding maps to that pool — "root-cause code path is gated on `feature*`, and the PoC uses `{feature-signature-tx}` to demonstrate impact".

## Cross-platform mapping

| Contest | Pool structure | When M-04 needed |
|---------|----------------|------------------|
| **Sherlock** | Named features, each with own reward pool | Whenever root cause is in shared helper — always apply M-04 |
| **Code4rena** | Single pool, bounty per severity | Usually not needed — severity matters, not classification |
| **Cantina** | Similar to Sherlock for contest format | Apply if contest defines feature buckets |
| **Immunefi bug bounty** | Per-program, vary | Apply if program has scope buckets |

## Anti-patterns

- **Don't over-bridge**: if the root cause is ACTUALLY in the feature's code (not shared infra), M-04 is unnecessary — the naive PoC already covers it.
- **Don't fake the bridge**: the feature-tx you add must genuinely exercise the root-cause code path. Pure "decorative" transactions that don't touch the bug don't help.
- **Don't mis-label**: if the root cause is truly cross-feature (e.g. a generic library), label accurately. Judges catch over-claims.

## Validated application

- **ESC-1** (XRPL): root cause in `TokenHelpers.cpp` `accountHolds` — shared between base MPT and MPT DEX. PoC initially used only Clawback. Added `testMPTDEXCoverage` case with `OfferCreate` (TakerGets=MPT, XLS-0082 signature) + cross-currency `Payment` via BookStep. Finding labeled MPT DEX with defensible root-cause gate (`featureMPTokensV2`).
- **ESC-3** (XRPL): vault shares carry `lsfMPTCanTrade` — PoC posts an OfferCreate on vault shares before the escrow-shield step.

## PoC extension checklist

When extending a PoC for M-04 coverage:

```
[ ] Identified the feature amendment gate in the root-cause code path
[ ] Found a signature transaction from that feature's XLS spec
[ ] Added the tx to the PoC in a way that actually exercises the gated code
[ ] Asserted observable state change from the feature tx (not just silent acceptance)
[ ] Documented the feature-pool classification reasoning in the finding's header paragraph
[ ] Re-ran the PoC end-to-end to ensure the added tx doesn't break the exploit sequence
```
