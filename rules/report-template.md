# Report Template

> Output: `AUDIT_REPORT.md` in project root

## ID System
- Critical: `C-01`, `C-02`
- High: `H-01`, `H-02`
- Medium: `M-01`, `M-02`
- Low: `L-01`, `L-02`
- Informational: `I-01`, `I-02`

## Finding Section Format

```markdown
### [X-NN] Title [VERIFIED/UNVERIFIED]

**Severity**: Critical/High/Medium/Low/Informational
**Location**: `File:L123-L145`
**Evidence**: [FORK-PASS] / [POC-PASS] / [CODE-TRACE]
**Confidence**: HIGH/MEDIUM/LOW
**Validation Score**: XX/100 (platform: {C4/Sherlock/etc})

**Description**: [Clear explanation with code snippet]
**Impact**: [Quantified — see Platform Impact Rules below]
**PoC Result**: [Fork test output or code trace]
**Recommendation**: [Fix with diff]
```

## Report Structure

```markdown
# Security Audit Report — [Project]

**Date**: YYYY-MM-DD
**Auditor**: DewaxGuard v1.0.0
**Scope**: [description]
**Platform**: [C4/Sherlock/Cantina/Immunefi]

## Executive Summary
## Summary Table
## Critical Findings
## High Findings
## Medium Findings
## Low Findings
## Informational
## Priority Remediation Order
```

## Platform Impact Quantification (MANDATORY for every Medium+ finding)

### Sherlock
- Concrete dollar amount of loss (e.g., "signer loses $10,000")
- Percentage of principal/yield/fees (e.g., "100% of principal")
- Explicit threshold: "Exceeds Sherlock Medium threshold of >0.01% AND >$10"
- For DoS: permanent vs temporary, whether core functionality is broken

### Code4rena
- High: quantify "direct loss of funds" with realistic scenario
- Medium: state conditions required and their likelihood

### Cantina
- Map to Impact x Likelihood matrix explicitly
- State both axes and the resulting severity cell

### Immunefi
- Map to specific impact category from their severity table
- Include realistic attack cost vs extracted value
