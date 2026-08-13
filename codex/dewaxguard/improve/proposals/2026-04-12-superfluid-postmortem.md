# Post-Audit Improvement Proposals — Superfluid ClearMacro (2026-04-12)

> First audit using DewaxGuard v1.2.0. EVM/Solidity, meta-tx forwarder protocol.
> Findings: 2 Medium (both LIKELY VALID after 3 manual improvement rounds).
> Key lesson: The pipeline FOUND the bugs but produced weak SUBMISSIONS. The gap is in
> report hardening, not in vulnerability detection.

---

## Proposal 1: Inconsistency Scanner (depth agent directive)

**Root cause**: RC-DEPTH — M-02 scored 52/100 until we manually found `SuperUpgrader.sol:63`
using `forceApprove` for the identical pattern. This evidence was the difference between
AI-21 INVALID and 91/100 LIKELY VALID.

**Gap**: No agent systematically searches for "does the correct pattern exist elsewhere in the codebase?"
When a finding identifies a missing safe wrapper/pattern, the pipeline should grep the codebase for
the correct version of that pattern. If found, the finding becomes an "inconsistency bug" — much
stronger than a "missing feature" complaint.

**Change type**: extend (add directive to depth agents + report template)
**Files modified**:
- `agents/depth-edge-case.md` (+5 lines): Add "Inconsistency Check" step
- `agents/depth-external.md` (+5 lines): Same directive
- `rules/report-template.md` (+3 lines): Finding format includes "Codebase Precedent" field

**Directive to add** (to depth-edge-case.md and depth-external.md):
```
## Inconsistency Check (MANDATORY for every finding)
For each finding, grep the full codebase for the CORRECT version of the pattern:
- Missing SafeERC20 → grep for `forceApprove|safeApprove|safeTransfer`
- Missing access control → grep for the same modifier used on similar functions
- Missing validation → grep for the same validation in paired/sibling functions
If the correct pattern exists elsewhere, cite it: "{File}:{Line} uses {correct pattern}."
This transforms "missing feature" into "inconsistency bug" — much harder to invalidate.
```

**Anti-bloat gates**: All pass. +13 lines across 3 files. No duplication. Methodology (HOW).
**FP risk**: Zero — this is evidence gathering, not finding generation.

---

## Proposal 2: Platform Threshold Enforcement (report phase)

**Root cause**: RC-METHOD — M-01 initially said "fund loss" without quantifying against
Sherlock's >0.01% AND >$10 threshold. Judges enforce thresholds strictly.

**Gap**: The pipeline generates findings with impact descriptions but doesn't enforce
platform-specific quantification. A Sherlock finding MUST include dollar amounts and
percentage calculations. A Code4rena finding needs different framing.

**Change type**: extend (add to report-template.md)
**Files modified**:
- `rules/report-template.md` (+15 lines): Platform-specific impact quantification rules

**Section to add**:
```
## Platform Impact Quantification (MANDATORY)

### Sherlock
Every Medium+ finding MUST include:
- Concrete dollar amount of loss (e.g., "signer loses $10,000")
- Percentage of principal/yield/fees affected (e.g., "100% of principal")
- Explicit threshold citation: "Exceeds Sherlock Medium threshold of >0.01% AND >$10"
- For DoS: duration classification (permanent/temporary) and whether core functionality

### Code4rena
- High: quantify "direct loss of funds" with realistic scenario
- Medium: state conditions required and their likelihood

### Cantina
- Map to Impact x Likelihood matrix explicitly
```

**Anti-bloat gates**: All pass. +15 lines in 1 file. Methodology (HOW to write impact).
**FP risk**: Zero — improves report quality, not detection.

---

## Proposal 3: Trust Boundary Mapping (breadth agent directive)

**Root cause**: RC-DEPTH — M-01 required 3 rounds to properly frame the provider trust
model. The access-control agent maps "who has what role" but doesn't map "what is the
trust boundary between the signer and the relayer in a meta-tx system."

**Gap**: For meta-transaction and relay-based protocols, the pipeline doesn't systematically
identify: (a) which roles are trust-boundaries vs admin-roles, (b) which code paths are
immune to role compromise (e.g., self-relay), (c) where the signature is the last defense.

**Change type**: extend (add to access-control-agent.md)
**Files modified**:
- `agents/hacking-agents/access-control-agent.md` (+8 lines): Trust boundary analysis

**Directive to add**:
```
## Trust Boundary Analysis (meta-tx / relay protocols)
When the protocol uses EIP-712 signatures with relay/provider roles:
1. Map each role: Is it admin (governance), infrastructure (relay), or user (signer)?
2. For each role: What happens if their key is compromised? What can the attacker do?
3. Identify immune paths: Does a self-relay/direct-call path exist that bypasses the role?
4. Check signature binding: Does the EIP-712 digest bind ALL parameters that control
   execution? (target contract address, function selector, all arguments). Any unbound
   parameter is a substitution vector.
```

**Anti-bloat gates**: All pass. +8 lines in 1 file. Methodology (HOW to analyze trust).
**FP risk**: Low — meta-tx analysis applies to ~15% of protocols. Directive is conditional.

---

## Proposal 4: Attacker-Controlled Callback Tracing (execution-trace agent)

**Root cause**: RC-DEPTH — M-01 needed explicit step about `postCheck` being called on
the attacker-supplied macro. The execution-trace agent handles reentrancy callbacks but
doesn't systematically trace "when the caller controls which contract is called, the
callback belongs to the attacker."

**Gap**: In meta-tx systems, the relayer chooses the target contract. Any callback on
that contract (postCheck, fallback, hooks) is attacker-controlled. The execution-trace
agent should flag this.

**Change type**: extend (add to execution-trace-agent.md)
**Files modified**:
- `agents/hacking-agents/execution-trace-agent.md` (+5 lines)

**Directive to add**:
```
## Caller-Controlled Target Tracing
When msg.sender or a function parameter determines WHICH contract is called:
- All callbacks on that contract (hooks, checks, view calls) are attacker-controlled
- An attacker-controlled callback that is a no-op provides ZERO protection
- Trace: who supplies the target address? Can they substitute a different contract?
  If yes → every callback on that target is suspect
```

**Anti-bloat gates**: All pass. +5 lines in 1 file. Methodology (HOW to trace).
**FP risk**: Low — callback tracing is universally applicable.

---

## Proposal 5: Submission Hardening Pass (new Phase 5e directive)

**Root cause**: RC-METHOD — Both findings needed 3 rounds of manual improvement to
reach >90 scores. The pipeline generates findings and validates them, but doesn't
HARDEN them for submission. The gap between "technically correct finding" and
"judge-proof submission" was 30+ points.

**Gap**: After bug-validator scores a finding, there's no feedback loop that improves
the finding's writing based on the score. The validator identifies weaknesses (e.g.,
"AI-21 risk: -40") but the report writer doesn't receive this feedback.

**Change type**: extend (add feedback loop in SKILL.md pipeline)
**Files modified**:
- `SKILL.md` (+10 lines): Add Phase 5d→6 feedback loop description

**Pipeline addition** (between Phase 5d and Phase 6):
```
Phase 5d.1: SUBMISSION HARDENING (per finding scored <85 by bug validator)

For each finding with score < 85:
1. Read the validator's deduction breakdown
2. For each deduction > 5 points, apply the corresponding fix:
   - "AI-21 risk" → Run Inconsistency Check (Proposal 1) and add evidence
   - "Trust debate risk" → Add Trust Boundary section from access-control analysis
   - "Loss not quantified" → Add Platform Threshold math (Proposal 2)
   - "Likely dup" → Ensure finding has differentiating evidence (fork PoC, unique angle)
   - "Missing PoC" → Escalate to Phase 5c fork PoC queue
3. Re-score after hardening. If still <70, downgrade to LEAD.
```

**Anti-bloat gates**: All pass. +10 lines in 1 file. Methodology (HOW to improve submissions).
**FP risk**: Zero — this only improves existing findings, never generates new ones.

---

## Summary

| # | Proposal | Type | Lines | Impact |
|---|----------|------|-------|--------|
| 1 | Inconsistency Scanner | extend | +13 | M-02: 52→91 (killed AI-21) |
| 2 | Platform Threshold Enforcement | extend | +15 | M-01: missing quantification |
| 3 | Trust Boundary Mapping | extend | +8 | M-01: trust model framing |
| 4 | Attacker-Controlled Callback | extend | +5 | M-01: postCheck analysis |
| 5 | Submission Hardening Pass | extend | +10 | Both: 3 manual rounds → 0 |
| **Total** | | | **+51 lines** | |

All proposals are methodology (HOW), not patterns (WHAT). Total +51 lines across 6 files.
No new files created. No duplication across language trees (all changes are in shared files).
