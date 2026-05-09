# Report Formatting

> **Plain-English requirement (HARD)**: every Description and Fix paragraph in this format MUST follow `rules/plain-english-style.md`. The single Description sentence is the highest-leverage line in the whole report — it is what triage readers see first. Spend the time to make it land for a smart-contract-savvy reader who does not speak auditor jargon.

## Report Path

Save the report to `assets/findings/{project-name}-pashov-ai-audit-report-{timestamp}.md` where `{project-name}` is the repo root basename and `{timestamp}` is `YYYYMMDD-HHMMSS` at scan time.

## Output Format

````
# 🔐 Security Review — <ContractName or repo name>

---

## Scope

|                                  |                                                        |
| -------------------------------- | ------------------------------------------------------ |
| **Mode**                         | ALL / default / filename                               |
| **Files reviewed**               | `File1.sol` · `File2.sol`<br>`File3.sol` · `File4.sol` | <!-- list every file, 3 per line -->
| **Confidence threshold (1-100)** | N                                                      |

---

## Findings

[95] **1. <Title>**

`ContractName.functionName` · Confidence: 95

**Description**
<One short sentence in plain English: name the function, say what is missing or wrong, say who can abuse it, and say what the user loses. Example: "`withdraw` sends ETH before zeroing the balance, so any user with an attacker contract can call it recursively and drain the entire vault.">

**Fix**

```diff
- vulnerable line(s)
+ fixed line(s)
```
---

[82] **2. <Title>**

`ContractName.functionName` · Confidence: 82

**Description**
<One short sentence in plain English: name the function, say what is missing or wrong, say who can abuse it, and say what the user loses. Example: "`withdraw` sends ETH before zeroing the balance, so any user with an attacker contract can call it recursively and drain the entire vault.">

**Fix**

```diff
- vulnerable line(s)
+ fixed line(s)
```
---

< ... all above-threshold findings >

---

[75] **3. <Title>**

`ContractName.functionName` · Confidence: 75

**Description**
<One short sentence in plain English: name the function, say what is missing or wrong, say who can abuse it, and say what the user loses. Example: "`withdraw` sends ETH before zeroing the balance, so any user with an attacker contract can call it recursively and drain the entire vault.">

---

< ... all below-threshold findings (description only, no Fix block) >

---

Findings List

| # | Confidence | Title |
|---|---|---|
| 1 | [95] | <title> |
| 2 | [82] | <title> |
| 3 | [75] | <title> |

---

## Leads

_Vulnerability trails with concrete code smells where the full exploit path could not be completed in one analysis pass. These are not false positives — they are high-signal leads for manual review. Not scored._

- **<Title>** — `Contract.function` — Code smells: <missing guard, unsafe arithmetic, etc.> — <1-2 sentence description of the trail and what remains unverified>
- **<Title>** — `Contract.function` — Code smells: <...> — <1-2 sentence description>

---

> ⚠️ This review was performed by an AI assistant. AI analysis can never verify the complete absence of vulnerabilities and no guarantee of security is given. Team security reviews, bug bounty programs, and on-chain monitoring are strongly recommended. For a consultation regarding your projects' security, visit [https://www.pashov.com](https://www.pashov.com)

````

**Rules:** Follow the template above exactly. Sort findings by confidence (highest first). Findings below the threshold get a description but no **Fix** block. Draft findings directly in report format — do not re-generate.

**Plain-English self-check** (apply to each Description before saving):
- [ ] Names the function and the missing check or wrong logic.
- [ ] Names the actor (any user, attacker, owner, etc.).
- [ ] States the user-level harm in money or lost access.
- [ ] One sentence, ≤ 25 words, no banned jargon from `rules/plain-english-style.md`.

