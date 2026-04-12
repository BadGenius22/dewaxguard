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
**Impact**: [Quantified where possible]
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
