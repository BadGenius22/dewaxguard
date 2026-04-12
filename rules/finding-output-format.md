# Finding Output Format

> **All agents MUST use this format for findings.**

```markdown
## Finding [{PREFIX}-N]: Title

**Verdict**: CONFIRMED / PARTIAL / REFUTED / CONTESTED
**Severity**: Critical/High/Medium/Low/Informational
**Location**: `File:LineN`
**Evidence**: [FORK-PASS] / [POC-PASS] / [CODE-TRACE]

**Description**: What's wrong — 2-3 sentences with code snippet.

**Impact**: What can happen — quantify where possible.

**Attack Sequence**:
1. Attacker does X
2. State changes to Y
3. Attacker extracts Z

**PoC Result**: [test output or trace summary]

**Recommendation**: How to fix — include code diff where helpful.

### Precondition Analysis (if PARTIAL or REFUTED)
**Missing Precondition**: [What blocks this attack]
**Precondition Type**: STATE / ACCESS / TIMING / EXTERNAL / BALANCE

### Postcondition Analysis (if CONFIRMED or PARTIAL)
**Postconditions Created**: [What conditions this creates]
**Who Benefits**: [Who can use these]
```
