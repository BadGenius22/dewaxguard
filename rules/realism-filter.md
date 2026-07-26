# Realism Filter (Mandatory First-Class Filter)

> **Origin**: K2 audit (2026-04 → 2026-05). Without this filter, agents auto-promoted HF38-b to Medium when its trigger was `set_distribution_end` (admin-only, parked as Pass 1 LEAD-D). The filter reclassified ~40% of candidate findings.
>
> **Status**: MANDATORY at Phase 5d (bug validator). Apply BEFORE severity-decision-tree.

---

## The Filter Values

Every finding MUST be tagged with one of:

| Value | Meaning | Severity Action |
|-------|---------|----------------|
| `permissionless` | Trigger is callable by any unprivileged actor; impact lands on a victim who didn't consent | **No adjustment** — proceed to severity-decision-tree |
| `admin-trust` | Trigger requires a trusted role (admin, governance, multisig, emission_manager, treasury_admin, oracle_admin, upgrade_admin, emergency_admin) acting maliciously OR in legitimate-but-buggy way | **Park to ADDITIONAL_LEADS.md** unless platform criteria explicitly allow admin findings |
| `design-choice` | Behavior is documented as intentional in protocol docs, README, or sponsor clarifications (covered by `docs-intent-map.md`) | **REJECT** — do not include in report |
| `unreachable-precondition` | Trigger requires a state combination that cannot occur in any realistic deployment | **REJECT** unless reachability is proven |
| `semi-trusted-role` | Trigger is a semi-trusted actor (operator, keeper, oracle relayer) acting within stated trust assumption | **−1 severity tier** (per severity-matrix.md downgrade modifier) |
| `compromised-key` | Exploit chain's precondition includes a leaked / phished / compromised private key (victim user EOA, admin, or operator) | **REJECT** — auto-invalidator on virtually every bug-bounty program; surface as Informational at most, no PoC / bug-validator spend |
| `uneconomic-grief` | Trigger IS permissionless and the victim IS involuntary, but the attacker's **unrecoverable** cost meets or exceeds the quantified victim harm — griefing that costs the griefer more than the grief | **Cap at Low** (per `rules/severity-matrix.md` → Grief economics). Do NOT reject: the underlying defect is usually real and belongs in the QA/Low bundle |

---

## Decision Tree

For each candidate finding, walk in order:

```
0. Does the exploit chain REQUIRE a compromised / leaked / phished private key
   (victim user EOA, admin, or operator) as a precondition?
   YES → tag = compromised-key → REJECT (Informational at most). Auto-invalidator on
         virtually every bug-bounty program; do NOT spend a PoC / bug-validator pass.
   NO  → continue

1. Does the docs-intent-map (rules/docs-intent-map.md) mark this behavior as
   "by design" / "intentional" / "accepted trade-off" / "out of scope" / "known limitation"?
   YES → tag = design-choice → REJECT, write to ADDITIONAL_LEADS with reason
   NO  → continue

2. Is the trigger callable by an unprivileged actor with no special role assumptions?
   YES → continue to 2a (permissionless is NOT yet final for availability findings)
   NO  → continue to 3

2a. Is the finding's impact availability / griefing (DoS, queue blocking, liveness)
    rather than theft, fund loss, or accounting drift?
   NO  → tag = permissionless → continue to severity-decision-tree
   YES → is the attacker's UNRECOVERABLE cost >= the quantified victim harm?
         (burnt dust, locked principal, sacrificed position — cost the attacker
          never gets back; compare against harm in $ or "delay only, no funds lost")
         YES → tag = uneconomic-grief → cap at Low, route to QA/Low bundle
         NO  → tag = permissionless → continue to severity-decision-tree
         UNQUANTIFIED → tag = uneconomic-grief → cap at Low until both
                        `attacker_cost:` and `victim_harm:` are declared

3. Does the trigger require a TRUSTED role (admin, governance, fully-trusted multisig)?
   YES → tag = admin-trust → park to ADDITIONAL_LEADS (default platform policy)
         EXCEPTION: if platform criteria explicitly allow admin findings (see below)
   NO  → continue

4. Does the trigger require a SEMI-TRUSTED role (operator, keeper, relayer)?
   YES → tag = semi-trusted-role → continue to severity-decision-tree with -1 tier
   NO  → continue

5. Is the precondition reachable in any realistic deployment?
   NO  → tag = unreachable-precondition → REJECT
   YES → continue (this case usually means "permissionless" was the right tag — re-walk)
```

---

## Per-Platform Defaults

| Platform | Admin-Trust Findings? | Semi-Trusted Findings? | Design-Choice Findings? |
|----------|----------------------|------------------------|------------------------|
| **Code4rena Competitive** | NO (parked as LEAD or QA-L) | YES with -1 tier | NO (rejected) |
| **Code4rena Bug Bounty** | YES if explicitly in scope | YES | YES if not explicitly OOS |
| **Sherlock Competitive** | NO (per AI-4) | YES with -1 tier | NO |
| **Sherlock Bug Bounty** | YES if in scope | YES | YES if not explicitly OOS |
| **Cantina** | YES | YES | NO |
| **Immunefi** | NO unless explicitly | YES | NO |

The orchestrator MUST set platform defaults at Phase 1 recon (read from `--platform:{name}` flag) and apply them in Phase 5d.

---

## Per-Project Override

Projects may declare their own realism filter in `{PROJECT_ROOT}/CLAUDE.md` under a "Realism filter" section. The project-local declaration **overrides platform defaults**.

K2 example (project-local override):
```markdown
**Realism filter (HARD)**: Per warden directive, this audit excludes any finding that depends on
(a) a trusted role acting maliciously,
(b) a sponsor design-choice argument,
(c) a precondition that is unreachable in any realistic K2 deployment.
Findings that fail this filter go to ADDITIONAL_LEADS.md for warden discretion, not the main report.
```

When the orchestrator reads `CLAUDE.md` during preflight, it MUST:
1. Detect the realism-filter section (grep for "Realism filter" or "realism filter")
2. Extract the project's filter rules
3. Apply them in addition to (more restrictive than) platform defaults

---

## Output Format

Every finding written by an agent MUST include:

```markdown
## Finding [{PREFIX}-N]: Title
...
**Realism Filter**: permissionless | admin-trust | design-choice | unreachable-precondition | semi-trusted-role | compromised-key | uneconomic-grief
**Filter Reason**: [1-line explanation of why this tag applies]
**Trigger Actor**: [specific role or "any user"]
...
```

For any **availability / griefing** finding, three further fields are MANDATORY (the severity router caps the finding at Low without them):

```
attacker_cost: [concrete figure + whether it is RECOVERABLE or UNRECOVERABLE]
victim_harm:   [concrete figure, or "delay only, no funds lost, recoverable via X"]
operator_recoverable: true | false   [if false, one clause on why no routine admin action helps]
```

Findings without a `Realism Filter` field default to `admin-trust` (most conservative) and route to ADDITIONAL_LEADS pending review.

---

## Mechanical Enforcement

Phase 5d (bug validator) MUST:
1. Reject any finding with `Realism Filter: design-choice` (move to /dev/null with reason)
2. Park any finding with `Realism Filter: admin-trust` to ADDITIONAL_LEADS unless platform allows
3. Apply -1 severity tier for `Realism Filter: semi-trusted-role` (floor: Informational)
4. Reject any finding with `Realism Filter: unreachable-precondition` unless reachability is proven via code path
5. Reject any finding with `Realism Filter: compromised-key` (out-of-scope on virtually every program; surface Informational at most, no PoC / bug-validator spend)
6. Cap at Low any finding with `Realism Filter: uneconomic-grief`, and any availability/griefing finding that is operator-recoverable or has not declared `attacker_cost:` + `victim_harm:`. This is enforced mechanically by `scripts/severity_router.py::apply_grief_economics` — including the **self-admission rule**: a finding whose own text concedes a recovery path ("the TREASURY can still recover", "requires manual fills") is treated as operator-recoverable unless it explicitly sets `operator_recoverable: false`.

This filter runs BEFORE the severity-decision-tree (`rules/severity-decision-tree.md`). The decision tree assumes the filter has already pruned non-permissionless findings.

---

## Why This Is First-Class

In the K2 audit, the realism filter was project-local (declared in CLAUDE.md only) and had to be re-applied manually at every agent prompt. Without explicit propagation:
- Pass 5 HF38-b verifier auto-classified the finding as Medium (correct for the class) but the realism filter (parked as Pass 1 LEAD-D for admin-trigger) was forgotten
- The orchestrator had to manually downgrade it to QA-L05

By making the filter first-class:
- Every agent prompt receives the filter as input (not buried in CLAUDE.md)
- Every finding output carries the filter tag (mechanically enforceable)
- Phase 5d can reject/route based on the tag without re-reading source

---

## Validated Audits

- **K2 Code4rena (2026-04)**: Realism filter reclassified ~40% of candidate findings. Without it, the audit would have shipped 4-5 contested Mediums (all admin-trust) that judges would have rejected, diluting the 1 valid Medium.
- **DRE Sherlock (2026-07)** — origin of `uneconomic-grief`: a **real** defect (wrong-list compliance check + no `try/catch`, permanently bricking the keeper withdrawal queue) was tagged `permissionless` — correctly, by the then-current filter — and shipped as Medium with a passing end-to-end fork PoC. Rejected: *"attacker will lose way more than the party being affected."* The attacker's dust was unrecoverable; victims suffered only delay the TREASURY could clear. The filter had six tags, all about **reachability and consent**, and none about **economic rationality** — it asked "is there an involuntary victim?" (yes) but never "does the attacker pay more than the victim loses?" (yes). The gap was that the attacker-cost dimension already existed in `rules/l1-severity-matrix.md`, `references/criteria/immunefi.md` and `M16`, and had never been generalized to the smart-contract path.

---

## Integration Points

- **Phase 1 (recon)**: Read `CLAUDE.md` realism-filter section, write to `{SCRATCHPAD}/realism-filter.md` for downstream agents
- **Phase 3 (breadth) + Phase 4b (depth)**: Pass `realism-filter.md` as required input to every agent prompt
- **Phase 5d (bug validator)**: Apply the filter before severity-decision-tree
- **Phase 6 (report)**: Findings tagged `admin-trust` go to ADDITIONAL_LEADS; `design-choice` go to /dev/null; `permissionless` go to main report; `semi-trusted-role` go to main report at -1 severity
