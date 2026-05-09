# Finding Output Format

> **All agents MUST use this format for findings.**
> **Plain-English requirement (HARD)**: Description, Impact, Attack Sequence, PoC Result, and Recommendation must follow `rules/plain-english-style.md`. The validator deducts 5 points if the Description does not follow the four-sentence shape (what is wrong → why it matters → who triggers it → what the user sees) or if banned jargon survives without a one-sentence definition.

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
  L44:        // no auth check — anyone can call this and become the admin
  L45:        storage::set_admin(env, &new_admin);
  L46:    }

**Description**:
Four short sentences in this order:
1. What is wrong — function name + the missing check or wrong logic.
2. Why that matters — what the missing check would have prevented.
3. Who can trigger it — name the actor in plain words.
4. What the user sees — money loss, locked funds, blocked action.

Example:
> `set_admin` does not check who is calling it. The function is supposed to only
> let the current admin choose a new admin, but it skips that check entirely.
> Any wallet on the network can call this function. The caller becomes the new
> admin and can drain every token the contract holds.

**Impact**: One or two sentences in user terms. Numbers preferred.
> All assets controlled by the admin role are at risk — at the fork block this is $1.2M of pooled USDC.

**Attack Sequence**:
1. Attacker calls `set_admin(attackerAddress)` with no signature, no payment.
2. The contract overwrites the admin slot with `attackerAddress`.
3. Attacker calls `withdraw_all` (admin-only) and pulls every token to their wallet.

**PoC Result**: Test name, command, and the key assertion line. Comments inside the PoC follow the comment dictionary in `rules/plain-english-style.md`.

**Recommendation**:
One sentence stating the fix, a code diff, then one sentence stating what the fix prevents.
> Add an `admin.require_auth()` call at the top of `set_admin`.
> ```diff
>  pub fn set_admin(env: &Env, new_admin: Address) {
> +    storage::get_admin(env).require_auth();
>      storage::set_admin(env, &new_admin);
>  }
> ```
> After this change, only a transaction signed by the current admin can change the admin.

### Precondition Analysis (if PARTIAL or REFUTED)
**Missing Precondition**: What blocks this attack today, in plain words.
**Precondition Type**: STATE / ACCESS / TIMING / EXTERNAL / BALANCE

### Postcondition Analysis (if CONFIRMED or PARTIAL)
**Postconditions Created**: What is now true that was not true before, in plain words.
**Who Benefits**: Name the actor (any user, the admin, a flash-loan-funded attacker, etc.).

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
5. **Plain-English check** — Description must follow the four-sentence shape; banned jargon (per `rules/plain-english-style.md`) must be replaced or defined on first use. Validator deducts 5 points per violation.
