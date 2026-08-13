# Report Template

> Output: `AUDIT_REPORT.md` in project root
> **Plain-English requirement (HARD)**: every finding written using this template MUST follow `rules/plain-english-style.md`. The Description, Impact, PoC Result, and Recommendation fields are read by smart-contract-savvy users who do not speak auditor jargon. Tier writers fail the post-write self-check if banned jargon survives without a one-sentence definition.

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

**Description**:
Four short sentences, in this order (per `rules/plain-english-style.md`):
1. What is wrong — one sentence naming the function and the missing check.
2. Why that matters — one sentence on what the missing check would have prevented.
3. Who can trigger it — name the actor (any user, attacker, owner, etc.).
4. What the user sees — money loss, locked funds, blocked withdrawal.
Include the smallest code snippet that proves point 1.

**Impact**:
Concrete user-level harm. Numbers preferred. Examples:
- "User loses 100% of their deposit (e.g. $10k from a 10k USDC deposit)."
- "Pool stops accepting withdrawals for everyone until the admin pauses and migrates."
- "Attacker mints 1 token at the price of 0.001 tokens — a 1000x discount."

**PoC Result**: Fork test output, unit test output, or a numbered code trace. Comments inside the PoC must follow the comment dictionary in `rules/plain-english-style.md`.

**Recommendation**:
1. One sentence stating the fix.
2. A code diff (or function-level pseudo-diff) showing the change.
3. One sentence stating what the fix prevents.
```

### Worked example (use as the style reference)

```markdown
### [H-01] withdraw() pays the user twice when called recursively [VERIFIED]

**Severity**: High
**Location**: `Vault.sol:L142-L160`
**Evidence**: [FORK-PASS]
**Confidence**: HIGH
**Validation Score**: 92/100 (platform: Sherlock)

**Description**:
`withdraw` sends ETH to the caller before setting their balance to zero. While the ETH is in flight, the caller's contract can call `withdraw` again. The user's balance is still its old value at that moment, so the second call also succeeds. Any user can do this with a small attacker contract; the attacker drains every token the vault holds.

```solidity
function withdraw() external {
    uint256 bal = balances[msg.sender];
    (bool ok,) = msg.sender.call{value: bal}("");   // ETH leaves first
    require(ok);
    balances[msg.sender] = 0;                       // balance zeroed last
}
```

**Impact**:
- Attacker drains the entire vault. With $2.4M of ETH in the vault at the fork block, that is the full $2.4M.
- All other users lose 100% of their deposits.

**PoC Result**:
```
forge test --match-test test_H01_drainViaReentrancy --fork-url $ETH_RPC -vvv
[PASS] test_H01_drainViaReentrancy
  Logs:
    attacker balance before:    0 ETH
    vault balance before:      800 ETH
    attacker balance after:    800 ETH
    vault balance after:         0 ETH
```

**Recommendation**:
Set the user's balance to zero **before** sending ETH, or wrap the function with a reentrancy lock.

```diff
 function withdraw() external {
     uint256 bal = balances[msg.sender];
+    balances[msg.sender] = 0;
     (bool ok,) = msg.sender.call{value: bal}("");
     require(ok);
-    balances[msg.sender] = 0;
 }
```

After this change, the second call sees a balance of zero and the recursive call sends nothing.
```

## Report Structure

```markdown
# Security Audit Report — [Project]

**Date**: YYYY-MM-DD
**Auditor**: DewaxGuard v1.0.0
**Scope**: [description]
**Platform**: [C4/Sherlock/Cantina/Immunefi]

## Executive Summary
A 3-paragraph summary written for a project lead, not an auditor. Paragraph 1: what the protocol does, in one or two sentences. Paragraph 2: how many issues were found and how bad the worst one is, in user terms. Paragraph 3: top three recommendations as a bulleted list. No jargon — see `rules/plain-english-style.md`.

## Summary Table
## Critical Findings
## High Findings
## Medium Findings
## Low Findings
## Informational
## Priority Remediation Order
```

## Platform Impact Quantification (MANDATORY for every Medium+ finding)

Write the impact number in dollars or percent first, then in one plain sentence say what the user feels. Example: "Loss: 100% of principal — every user who deposited would get back zero ETH."

### Sherlock
- Concrete dollar amount of loss (e.g. "signer loses $10,000").
- Percentage of principal / yield / fees (e.g. "100% of principal").
- State the threshold in plain words: "this is above Sherlock's Medium bar of >0.01% of TVL AND >$10".
- For a contract that stops working: say whether it is permanent or temporary, and what the user can no longer do.

### Code4rena
- High: explain the direct loss of funds in one sentence with a realistic scenario.
- Medium: list the conditions required and how likely each is in plain language ("the admin must call X first — they do this once a week per their docs").

### Cantina
- State the Impact axis (High / Medium / Low) and what user harm it represents.
- State the Likelihood axis (High / Medium / Low) and which user actions trigger it.
- State the resulting cell from the matrix.

### Immunefi
- Map to a specific impact category from their severity table — name the category, do not just cite a number.
- State a realistic attack cost (gas, capital, time) and the value extracted, both in dollars.

---

## Self-check before saving the report

- [ ] Every finding has the four-sentence Description shape.
- [ ] Every Impact line uses dollars, percent, or a clear user-action verb ("user can no longer withdraw").
- [ ] Every Recommendation has a fix sentence + diff + result sentence.
- [ ] Zero banned-jargon words from `rules/plain-english-style.md` survive without a one-sentence definition.
- [ ] No sentence is longer than 25 words.
