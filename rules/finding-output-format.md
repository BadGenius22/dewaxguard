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

**Impact**: One or two sentences in user terms, followed by the quantification ledger.
> All assets controlled by the admin role are at risk — at the fork block this is $1.2M of pooled USDC.

**Quantification** (HARD above Low — see `rules/severity-decision-tree.md` → Quantification gate):
```
victim:        every depositor in the USDC pool (1,842 addresses at fork block)
loss:          $1.2M, GLOBAL bound (the whole pool drains in one transaction)
attacker_cost: ~$18 gas, UNRECOVERABLE. Zero capital — no flash loan needed.
recoverable:   no. Funds leave to an attacker-controlled EOA; no admin clawback path exists.
```
Write `loss: UNQUANTIFIED — {what blocks measurement}` and cap at Low rather than inventing a figure.

**Attack Sequence**:
1. Attacker calls `set_admin(attackerAddress)` with no signature, no payment.
2. The contract overwrites the admin slot with `attackerAddress`.
3. Attacker calls `withdraw_all` (admin-only) and pulls every token to their wallet.

**PoC Result**: Test name, command, and the key assertion line. Comments inside the PoC follow the comment dictionary in `rules/plain-english-style.md`. Carries the four integrity-gate receipts from `rules/fork-poc-execution.md` §7 — a PoC without them tags `[CODE-TRACE]`, never `[FORK-PASS]`/`[POC-PASS]`:
```
mutation_check:   PASS — test fails when the guard is restored
positive_control: SKIPPED — result was positive
real_path:        0xA0b8...eB48 REAL (USDC), Attacker.sol MOCK (off value path)
assertion:        assertGt(usdc.balanceOf(attacker)) — measured +$812,400
```

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

## Handoff citation discipline (v1.33.0 — global rule A-2)

> Every agent boundary in this pipeline is an instance of "ask a model how something works and accept
> the answer". Recon tells breadth what the protocol does; inventory tells depth what was found;
> chain tells verify what to prove. Each hop launders a guess into a premise, and by the report it
> reads as established fact. `verified:` already enforces this at the *finding* level and M-32 at the
> *final gate*. These rules extend it to the hops in between.

1. **Any claim about what the code does, written into a scratchpad artifact that another agent will
   read, carries `file:line`.** This binds recon summaries, protocol descriptions, attack-surface
   notes, "the guard at X prevents Y", "only role Z can reach this", and every load-bearing sentence
   of a LEAD. Prose without a citation is a hypothesis and must be written as one.
2. **A consuming agent treats an uncited upstream claim as unverified.** Before relying on it, either
   read the source and cite it yourself, or carry the finding's dependence on it forward explicitly
   as `depends_on_unverified: {claim}`. Silently promoting it to a premise is the failure this rule
   exists to stop.
3. **A `depends_on_unverified:` field blocks any tier above Low** until it is resolved. It is
   discharged by a citation, not by a second agent agreeing.
4. **This binds the orchestrator too.** A conclusion reached earlier in the session is a hypothesis
   to re-check once it becomes load-bearing for a verdict, a submission, or a memory write.

---

## Hard rules (validator auto-fails on violation)

1. **`verified:` is mandatory for every FINDING** — paste the actual ±2 lines from the source. No paste = auto-reject. (LEADs do not require `verified:`.)
2. **`docs_intent_check:` is mandatory for every PASS finding** — see `rules/docs-intent-map.md`.
3. **`severity_check:` is mandatory for every PASS finding** — see `rules/severity-decision-tree.md`.
4. **`auth_check:` is mandatory whenever the finding alleges missing auth/access-control** — see `rules/auth-critical-files.md`.
5. **Plain-English check** — Description must follow the four-sentence shape; banned jargon (per `rules/plain-english-style.md`) must be replaced or defined on first use. Validator deducts 5 points per violation.
6. **Quantification ledger is mandatory for every finding claiming a tier above Low** — `victim` / `loss` / `attacker_cost` / `recoverable`, per `rules/severity-decision-tree.md` → Quantification gate. `loss: UNQUANTIFIED — {reason}` is an accepted value and caps the finding at Low; a missing block is an auto-fail. Never invent a figure.
7. **PoC integrity receipts are mandatory for any `[FORK-PASS]` / `[POC-PASS]` tag** — `mutation_check` / `positive_control` / `real_path` / `assertion`, per `rules/fork-poc-execution.md` §7. Missing or failing → the tag drops to `[CODE-TRACE]`.
8. **No uncited mechanism claim crosses an agent boundary** — see Handoff citation discipline above. An unresolved `depends_on_unverified:` caps the finding at Low.
