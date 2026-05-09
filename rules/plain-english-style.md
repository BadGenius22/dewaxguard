# Plain-English Style Rule

> **Applies to**: every finding written into a report (`AUDIT_REPORT.md`, `assets/findings/*.md`, QA-Bundle entries), every PoC comment, every recommendation diff, every Validator output shown to the user.
> **Read by**: Phase 5c PoC agents, Phase 5d validator, Phase 6 report writers, Phase 6 Pashov-style formatter.
> **Hard rule**: Findings that violate this rule are sent back to the writer agent for one rewrite pass before submission.

---

## Who is the reader?

A smart-contract-savvy person who has been writing Solidity / Rust / Move for ~6 months. They know what `transfer`, `storage`, and `block.timestamp` mean. They do **not** speak fluent auditor.

If a sentence needs a glossary lookup before the reader can decide whether to merge a fix, the sentence is too jargon-heavy. Rewrite it.

---

## Five rules

1. **One idea per sentence.** Max ~25 words. Break long sentences with periods, not commas or semicolons.
2. **Subject before verb, in that order.** "The function lets anyone…" beats "Anyone is allowed by the function to…".
3. **Name the actor.** Say *who* does the bad thing. "An attacker calls…", "Any user can…", "The owner can…". Don't write "the attack is possible" without naming the actor.
4. **Show the harm in money or user terms.** "User loses their deposit", "Attacker gets free tokens", "Pool stops accepting withdrawals". Avoid abstract harm like "state inconsistency" or "invariant violation" unless followed by a concrete user-level consequence.
5. **No Latin, no "aforementioned", no nested parentheticals.** If you need a parenthetical to explain a parenthetical, you have already lost the reader.

---

## Banned auditor jargon → plain replacement

Use the replacement when writing user-facing text. Source code comments inside the PoC keep the technical word **only** if the cheat-code or function name forces it (e.g. `vm.store` keeps its name, but the comment next to it must be plain).

| Don't write | Write instead |
|-------------|---------------|
| reentrancy / reenter | call back into the contract before the first call finishes |
| invariant violation | a rule the contract should always follow gets broken |
| monotonic / monotonicity | the value is supposed to only go up (or only go down), but here it can go backwards |
| fungible / non-fungible | regular token / unique token (NFT) |
| atomic / atomicity | the steps either all happen or none happen — here some happen and some don't |
| consistency class | findings that share the same root cause |
| precondition / postcondition | what must be true before / what is true after |
| TOCTOU | the value is checked, then used, but it can change in between |
| griefing | an attacker spends gas just to hurt other users, even if they don't profit |
| frontrun / sandwich | another transaction sneaks in before yours and changes the result |
| MEV | a bot reorders or inserts transactions to extract value from regular users |
| oracle staleness | the price feed is too old to trust |
| permissioned / permissionless | needs admin / anyone can call |
| privilege escalation | a low-trust actor gains admin powers |
| arbitrary code execution | the attacker can run any code they want |
| underflow / overflow | the number wraps around because it went below 0 / above its max |
| dust | very small leftover amounts |
| economic exploit | the math lets an attacker profit |
| griefable / DoS | a user can block the contract from working |
| race condition | two transactions in the same block can hit each other in the wrong order |
| state inconsistency | one variable was updated, the related variable was not — they now disagree |
| compose / composability | other contracts that call this one |
| trust assumption | something the protocol expects to be true about the admin / user / external service |
| out-of-band | happens outside the contract (e.g. a Discord vote, a multisig signing) |
| canonical | the official / agreed version |
| idempotent | safe to call twice |
| nonce reuse | a one-time number gets used twice |
| signature replay | the same signed message gets accepted again |
| slippage | the user receives less than they expected because the price moved |
| liveness | the system can keep making progress |
| safety | the system never enters a bad state |

If you absolutely need a banned term (because the protocol's own docs use it), define it on first use in one sentence: *"reentrancy — when a contract calls another contract that calls back into the first contract before the first call finishes"*.

---

## Sentence-pattern checklist

Each finding's **Description** must contain at least these four sentences, in this order:

1. **What is wrong.** "Function `X` does not check `Y`."
2. **Why that matters.** "Without that check, the value of `Z` can be set to anything."
3. **Who can trigger it.** "Any external caller can do this."
4. **What the user sees.** "The user's deposit is locked forever." / "The attacker walks away with the entire pool."

The **Recommendation** must contain:

1. **The fix in one sentence.** "Add a check that `Y` is greater than zero."
2. **A code diff** if the file is small enough to show. Otherwise a function-level pseudo-diff.
3. **One sentence on what the fix prevents.** "After this change, the function reverts when `Y` is zero, so the bug cannot happen."

---

## PoC comments — plain English contract

Solidity / Rust / Move PoC files are read by humans as well as agents. Every comment in a PoC file must follow these rules.

1. **Comment why, not what.** The code already says *what*. Comments explain the attack story.
2. **One comment per logical step.** Don't comment every line.
3. **Use the actor's name.** Variable names like `attacker`, `victim`, `owner` are required. Don't use `addr1`, `addr2`.
4. **Round numbers.** Show `1_000_000e6` (1M USDC) not `983_452_119`. Use the round number unless the exact number is the point of the bug.
5. **No Foundry / Anchor / Move slang in comments.** Inside a comment, write "pretend the call comes from the attacker" not "vm.prank as attacker".

### Foundry cheatcode comment dictionary

| Cheatcode | Plain comment to put on the SAME line |
|-----------|---------------------------------------|
| `vm.prank(attacker)` | `// next call comes from the attacker` |
| `vm.startPrank(attacker)` | `// every call below comes from the attacker until vm.stopPrank` |
| `vm.deal(addr, 100 ether)` | `// give addr 100 ETH so it can pay gas` |
| `vm.store(addr, slot, value)` | `// force the contract's storage to a state we want to test` |
| `vm.warp(t)` | `// jump the block time forward to t` |
| `vm.roll(n)` | `// jump to block number n` |
| `vm.expectRevert(...)` | `// the next call should fail with this error` |
| `assertEq(a, b)` | `// a and b must be equal — fail the test if not` |
| `assertGt(a, b)` | `// a must be greater than b — fail the test if not` |

### Solana / Anchor / Move equivalents

| Construct | Plain comment |
|-----------|---------------|
| `Context<T>` setup | `// build the accounts the instruction needs` |
| `signer = attacker` | `// pretend the attacker signed the tx` |
| `program.methods.foo().accounts({...}).rpc()` | `// call foo with these accounts and submit it on-chain` |
| `assert_eq!(a, b)` | `// a and b must be equal — fail the test if not` |
| `let _ = ...; // expect Err` | `// this call should fail` |
| `tx_context::sender(ctx)` | `// who sent this transaction` |
| Move `transfer::public_transfer` | `// move the object to a new owner` |

---

## Two side-by-side examples

### Bad (jargon)

> The `withdraw` function exhibits a TOCTOU race condition wherein the post-condition on `userBalance` is non-monotonic, permitting reentrant invariant violation. An adversary may exploit the composability of the callback to perform privilege escalation against the canonical accounting state, with permissionless trigger and dust-level economic griefing potential.

### Good (plain English)

> `withdraw` reads the user's balance, sends them ETH, and then sets their balance to zero. While the ETH is being sent, the user's contract can call `withdraw` again. The balance has not been zeroed yet, so the second call also succeeds and pays them again. Any user can do this. The attacker drains every token the contract holds.

---

## How agents enforce this

- **Phase 6 report writers** (the three tier writers and the assembler) MUST add this file to their input list and apply the checklist before declaring DONE.
- **Phase 5c PoC agents** MUST run the comment dictionary over the PoC file before saving it.
- **Phase 5d validator** treats a finding that fails the *4-sentence Description* check as a -5 point deduction under "presentation quality".
- **Pashov-style formatter** (per `references/report-formatting.md`) keeps each finding's `Description` line to a single plain-English sentence; if the writer produces auditor jargon, rewrite before saving.

---

## Self-check before saving any finding

- [ ] Could a developer who has never read this codebase before understand the bug from just the Description?
- [ ] Does the Impact line say what the user loses, in money or in lost access?
- [ ] Does every PoC comment explain *why*, not *what*?
- [ ] Are there zero banned-jargon words from the table above (or all flagged ones are defined in one sentence)?
- [ ] Are all sentences ≤ 25 words?

If any answer is "no", rewrite once. If still "no" after the rewrite, escalate to the orchestrator with a note and ship the best version.
