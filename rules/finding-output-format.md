# Finding Output Format

> **All agents MUST use this format for findings.**

```markdown
## Finding [{PREFIX}-N]: Title

**Verdict**: CONFIRMED / PARTIAL / REFUTED / CONTESTED
**Severity**: Critical/High/Medium/Low/Informational
**Location**: `File:LineN`
**Evidence**: [FORK-PASS] / [POC-PASS] / [CODE-TRACE]

**verified**: |
  // Quoted ±2 lines from File around LineN — pasted verbatim. Required for every
  // FINDING (not LEAD). A FINDING without `verified:` is auto-rejected by the
  // validator harness. See rules/agent-tool-budgets.md for the Read-call cost.
  L43:    pub fn set_admin(env: &Env, new_admin: Address) {
  L44:        // require_auth missing — anyone can rotate the admin
  L45:        storage::set_admin(env, &new_admin);
  L46:    }

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

### Validator-populated fields (Phase 5d adds these; agents leave blank)
**docs_intent_check**: NO_MATCH | REJECT — {file:line} marks {class} | DOWNGRADE — ... | ESCALATE — ...
**severity_check**: a=Y/N, b=Y/N → SEV[; modifier: ... → final SEV]
**auth_check** (only when finding alleges missing auth): SAW_FULL_BODY:{file:line} | SAW_GUARD:{file:line} | SKELETON_ONLY
```

## Hard rules (validator auto-fails on violation)

1. **`verified:` is mandatory for every FINDING** — paste the actual ±2 lines from the source. No paste = auto-reject. (LEADs do not require `verified:`.)
2. **`docs_intent_check:` is mandatory for every PASS finding** — see `rules/docs-intent-map.md`.
3. **`severity_check:` is mandatory for every PASS finding** — see `rules/severity-decision-tree.md`.
4. **`auth_check:` is mandatory whenever the finding alleges missing auth/access-control** — see `rules/auth-critical-files.md`.
