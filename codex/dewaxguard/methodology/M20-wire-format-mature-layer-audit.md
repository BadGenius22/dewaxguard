---
id: M-20
name: wire-format-mature-layer-audit
trigger_type: code
trigger_grep: "serializ(e|er|ation)|deserializ|\bborsh\b|\brlp\b|\bbcs\b|\bscale\b|protobuf|varint|wire[_ ]?format|canonical[_ ]?(form|ization)|\bsfield\b|stobject|type[_ ]?(code|tag|prefix|ordinal)|uleb128"
trigger_languages: [all]
applies_to_protocol_types: [any]
---
# M-20: Wire-Format Mature-Layer Audit Methodology

> **Validated origin**: XRPL Sherlock April 2026 contest, Binary Serialization / Canonical-Form Attacks domain. 8-agent /dewaxguard thorough breadth on the SField + STObject + STAmount + STParsedJSON + STTx + Serializer layer. Result: 0 Medium+, 0 Low submittables. Domain produced 4 latent informational properties, all REFUTED-FOR-CONTEST. Methodology validated against a structurally-sound serialization framework: the most valuable output was the plan exit-criterion table (35/35 NEW SFields PASS 4 dimensions), not findings.
>
> **Cross-language applicability**: Any audit on a mature wire-format / typed-binary serialization layer. Direct analogues: Bitcoin `CTransaction` (script + witness), Ethereum RLP, Solana `borsh`/Anchor IDL, Cosmos protobuf wrapping, Sui BCS, Aptos BCS, Substrate SCALE.

---

## When to apply M-20

- Protocol delta adds NEW typed wire-format additions to an EXISTING binary serializer
- Serializer has been deployed at scale for ≥2 years (high invariant-strength assumption)
- Hypothesis surface includes: type-code / ordinal collision, REQUIRED enforcement, canonical-form encoding, duplicate-field rejection, signature-form omission semantics, JSON↔binary parity, common-field positioning
- Determinism is consensus-bound (validators must produce identical bytes from identical objects)

**Skip if**: serializer is brand-new (first deployment) — that's not "mature-layer", it's "novel-type" auditing with different priorities.

---

## Core principle

**On a mature serialization layer, the most valuable audit output is the N-dimensional verdict table over all NEW typed elements — NOT findings.** The table validates the framework's invariant strength against the new additions. Findings are rare; when multiple agents converge on the same Informational property, it's a signal that the property is REAL but NON-EXPLOITABLE.

---

## Methodology steps (in order)

### Step 1 — SCOPE_HINT validation against baseline

**Mandatory before investing depth budget.** Diff every SCOPE_HINT hypothesis against the previous-version source tree (`<protocol>-prev/`, `bitcoin-prev/`, `solana-prev-version/`).

Example: a SCOPE_HINT may claim *"FIELD_TYPE_X is brand-new — first time this width is ever used as a field type"*. Empirical diff against the previous tree may show two pre-existing fields already use that width. **Multiple agents may independently refute the SCOPE_HINT via the same baseline diff**, but if SCOPE_HINT is trusted blindly, agents waste budget probing for "new encoder/decoder" that doesn't exist.

**Action**: For every SCOPE_HINT hypothesis that asserts novelty ("brand-new", "first-time"), open the baseline file and grep. If pre-existing, downgrade the hypothesis to a re-confirmation pass (cheap) and redirect depth budget to genuinely-novel surface.

### Step 2 — Enumerate the N-dimensional verdict table FIRST

**Before doing depth probes, enumerate the table that the plan exit criterion mandates.** Examples: 4 dimensions × 35 new fields = 140 cells. For Bitcoin: type-prefix uniqueness × witness-stack canonicality × script-encoding ambiguity × hash-input-stability × pre-segwit-replay-resistance = 5 dimensions per new opcode.

The table-first approach has two advantages:
- **Negative-result protection**: even if no findings emerge, the table is a valuable deliverable (exit criterion satisfied).
- **Convergence detection**: when multiple agents fill the table independently, divergent cells flag candidate bugs. When the table is unanimous PASS, that's mechanical evidence of framework soundness.

Validated origin: 7 of 8 agents independently produced the 4-dim table; all converged on 35/35 PASS-PASS-PASS-PASS. Convergence itself was the strongest signal of framework health.

### Step 3 — Apply F-53 cross-agent contradiction protocol (M-18)

**Multiple agents converging on the same Informational property = signal it's a real but non-exploitable latent property.** Don't dismiss; document.

Validated origin example: 4 of 8 agents independently flagged the same MPT-zero canonical-form latent property. The convergence is mechanical evidence that the property is REAL. The unanimous "REFUTED-FOR-CONTEST" verdict (legacy, OOS; downstream mitigations identified) is mechanical evidence it's non-exploitable. Both signals are valuable for future audits even though no submission resulted.

**Action**: When ≥2 agents flag the same code location, do NOT use majority-vote on severity. Read source code directly with all agents' citations side-by-side (M-18 protocol). Determine: (a) is the property real? (b) is there an exploit path? (c) is it pre-existing or NEW? If real + non-exploitable + pre-existing → REFUTED-FOR-CONTEST + record as Framework Fact for future audits.

### Step 4 — Distinguish CONSENSUS-BOUND vs RPC-ONLY surfaces

Per M-19 Gate 1 (which this methodology inherits): wire-format determinism IS consensus-bound (every node serializes/parses the same bytes the same way). Findings here would AUTO-ELEVATE one tier IF exploitable. Therefore:

- **High-yield**: bugs that cause two honest validators to disagree on bytes for the same logical value (canonical-form violation, ordinal collision, signature-hash divergence)
- **Low-yield**: bugs in JSON↔binary parity that affect RPC layer only without consensus impact (those are typically Informational by Sherlock T-13)

### Step 5 — Identify defensive layers and mark dependencies

For each new wire-format element, identify the defensive layers it depends on:

| Layer | Question |
|---|---|
| Type-code uniqueness | Is `(type, ordinal)` unique across all pre-existing fields? |
| Parse-time duplicate rejection | Does the binary parser reject duplicate fields BEFORE schema validation? |
| Schema enforcement (REQUIRED + unknown) | Does the templating layer throw on missing REQUIRED + unknown non-discardable fields? |
| Writer-side canonicalization | Do writers auto-cancel-to-absent for default values? |
| Polymorphic-type constraint at choke point | Are polymorphic types constrained at preflight (single coherent type per usage site)? |
| Signing-form omission semantics | Are notSigning fields correctly excluded from sign hash AND included in tx hash? |
| Cross-template field-collision | Does the same SField in two different SLE templates have consistent semantics? |
| State-tree hash-binding | Are non-canonical SLEs unconvergeable across nodes? (cryptographic guard) |

A finding requires breaking one of these AND finding an exploitable consequence. If the latent property exists but ALL layers protect, the property is non-exploitable.

### Step 6 — Test-coverage gaps and documentation gaps are NOT contest findings

Per CONTEST_FAQ "test files cannot contain valid findings" + "documentation gaps without exploit have no PoC" rule: test gaps and doc gaps are RECORDABLE in open-leads but NEVER submittable.

**Action**: When a periphery agent surfaces test/doc gaps, do NOT promote. Always add to the open-leads section with a flag for protocol team consideration.

### Step 7 — Signature-payload binding analysis

For wire-formats with signature fields, verify what the signer commits to. The canonical question: *"What outer-tx fields does each signer's signature transitively bind to?"*

**Action**: For every new signature field, write out the explicit "signer commits to: [list]" inventory. Failure modes to look for:
- Signer commits to LESS than expected (replay surface across tx variants)
- Signer commits to MORE than expected (signature unnecessarily fragile to refactoring)
- Signer commits to fields the signer cannot observe (sig depends on data attacker controls)
- Two parties (e.g. originator + co-signer) commit to DIFFERENT bytes (asymmetric authorization, exploitable)

### Step 8 — Reward-pool labeling discipline

Per M-04: every submittable finding must include a PoC tx from one of the protocol's reward-pool features' specs. Wire-format findings are particularly susceptible to "no reward pool match" rejection because the bug may be in shared infrastructure consumed by multiple features.

**Action**: wire-format findings should ALWAYS PoC at the highest-impact transaction type that uses the affected wire-format element. If the element is consumed by multiple reward-pool features, pick the one with most economic surface.

---

## Cross-language template

For any audit on a mature typed-binary serialization layer, populate this matrix:

| Dimension | XRPL SField | Bitcoin script | Ethereum RLP | Solana borsh | Cosmos protobuf | Sui BCS | Aptos BCS |
|---|---|---|---|---|---|---|---|
| Type-code uniqueness | (type, ordinal) | opcode | type-tag | enum discriminant | field number | type-tag | type-tag |
| Length-prefix codec | VL 1/2/3-byte | varint | length-prefix | LE u32 | varint | varint | uleb128 |
| Canonical-form (one byte sequence per value) | sMD_Default + canonicalize() + Proxy::assign | minimal-push | RLP canonical | borsh strict | proto3 default | BCS strict | BCS strict |
| Duplicate-field rejection at parse | adjacent_find at parse | N/A (positional) | N/A (positional) | borsh strict | proto3 last-wins (NON-canonical!) | BCS strict | BCS strict |
| Schema enforcement | applyTemplate REQUIRED throw | script verify | type tags | borsh deserialize | proto field presence | type checking | type checking |
| Signing-form omission | shouldInclude(notSigning) | sighash flags | tx struct | message fields | sign_doc | personal sign | personal sign |
| JSON↔binary parity | STParsedJSON | RPC encoding | tx encoding | base64/hex | JSON serialization | JSON serialization | JSON serialization |
| State-tree hash binding | STObject::getHash | tx hash | RLP hash | account hash | merkleized state | object digest | resource hash |

Each cell: "PASS / FAIL / N/A / TODO". An audit completes when every cell has a verdict + 1-line justification.

**Cross-language traps validated by Domain 20 (5 platforms)**:

1. **Bitcoin**: BIP62/BIP146 made non-minimal pushes non-standard. Any new opcode must comply. Equivalent to XRPL's `Proxy::assign` auto-canonicalization for default values.
2. **Ethereum RLP**: leading zeros in integers are non-canonical. Equivalent gap class to XRPL MPT negative-zero — pre-existing implementations may have leniency that newer code needs to handle.
3. **Solana borsh**: strict size-tagged; less surface for canonical-form bugs than XRPL/Bitcoin/Cosmos but type-discriminant collision IS possible if Anchor IDL accidentally reassigns ordinals.
4. **Cosmos protobuf last-wins**: proto3 spec says duplicate fields → last value wins. This is NON-canonical (two byte sequences → same logical value). Cosmos chains that use proto3 for tx encoding need explicit canonical-form check ON TOP OF protobuf. (XRPL avoids this via SField duplicate-rejection at parse layer.)
5. **Sui BCS / Aptos BCS**: strict canonical encoding by spec; main risk is type-tag drift between client and on-chain definitions.

---

## Negative-result methodology validation

**Validated outcome**: 0 submittables in a domain with 35 NEW typed elements and 5 reward-pool feature surfaces. This is a NEGATIVE RESULT, but the methodology produced 5 valuable artifacts:

1. Parse-time duplicate-rejection BEFORE schema validation (the layered defense pattern)
2. Sponsor-signature payload binding inventory (cross-tx replay structurally impossible)
3. SCOPE_HINT correction via baseline diff (saved depth budget)
4. Layered-defense pattern (parse + template both protect)
5. Polymorphic-type-constraint at preflight choke point (closes type-confusion at choke point)

Plus the 4-dimensional verdict table for 35 new typed elements, plus 2 informational latent properties recorded for future cross-domain reference.

**ROI assessment**: If the framework had been weak, the same methodology would have surfaced bugs. The methodology is "lossless against framework strength" — strong frameworks return architectural insights; weak frameworks return findings. Both outcomes are valuable.

---

## Anti-patterns to avoid

1. **Trusting SCOPE_HINT.md without baseline diff**: SCOPE_HINT may be wrong. Always validate against the previous-version source tree.
2. **Submitting test-coverage gaps as findings**: per CONTEST_FAQ, tests cannot contain valid findings. Same for documentation gaps.
3. **Conflating consensus-bound and RPC-only surfaces**: M-19 Gate 1 is critical. RPC-only divergences are typically Informational; consensus-bound divergences are Critical IF exploitable.
4. **Submitting "latent canonical-form non-canonicality" without exploit path**: latent properties may be real but produce zero economic impact. Document as informational, not submittable.
5. **Filing one submission per agent for the same convergent property**: 4 agents finding the same property is ONE finding (or zero, if non-exploitable), not 4. Apply M-18 dedup before submission.
6. **Skipping the N-dimensional verdict table**: it's the highest-yield deliverable for mature-layer audits. Don't skip even if you have findings.

---

## Validation history

- **Validated 1×**: XRPL April 2026 Sherlock contest, Binary Serialization / Canonical-Form Attacks domain. 8-agent breadth on 35 new typed wire-format elements. 0 Medium+, 0 Low submittables. 4-dimensional verdict table 35/35 PASS unanimously across 7 of 8 agents. 5 framework facts / defensive patterns extracted. The cross-agent contradiction protocol (M-18) successfully applied (zero contradictions detected; multiple converging informational clusters correctly handled).

---

## Cross-references to other manifest entries

- **M-04** (PoC must touch reward-pool feature): applies even when finding is wire-format-layer
- **M-10** (3-layer dedup): pre-existing baseline diff is layer 1
- **M-18** (cross-agent contradiction handling): applied during convergence detection
- **M-19** (path-selection determinism × asymmetry): inherits Gate 1 (consensus-bound vs RPC-only)
