# Phase: Verification (v1.13.2 driver)

> Fresh `claude -p` subprocess. No prior context. Treat this prompt as your entire task.
> Verification is where hypotheses become evidence. A finding without an executed PoC has minimal weight in the report — your job is to convert as many findings as possible into `[FORK-PASS]` / `[POC-PASS]` evidence tags.
>
> **Model tier: worker (`sonnet`).** Per `rules/model-tiering.md`, this phase runs on a cheaper model because PoC/code-trace work is high-token and low-judgment — you are executing tests against findings the premium finding agents already produced, not deciding whether a bug exists. Do all work in this subprocess; do not spawn sub-agents.

## Audit context

- **Audit ID**: `{{AUDIT_ID}}`
- **Mode**: `{{MODE}}` (this phase runs in `core` and `thorough`; `light` mode skips)
- **Source path**: `{{SRC_PATH}}`
- **Project root**: `{{PROJECT_ROOT}}`
- **Scratchpad**: `{{SCRATCHPAD}}`
- **Skill root**: `{{SKILL_ROOT}}`
- **Phase budget**: `{{TIMEOUT_SECONDS}}` seconds

## Pre-requisites

- `{{SCRATCHPAD}}/findings_routed.json` (inventory output)
- `{{SCRATCHPAD}}/chain_hypotheses.md` (chain analysis output — chains get priority verification)
- `{{SCRATCHPAD}}/depth_*_findings.md` (depth phase output — confirmed/partial verdicts feed PoC writing)
- `{{SCRATCHPAD}}/build_status.md` (compile status; if FAILED, fork PoCs fall back to CODE-TRACE)

If `findings_routed.json` is missing, write `{{SCRATCHPAD}}/verify_failed.md` and exit.

---

## STEP 1 — Build verification queue

Read `findings_routed.json`. Filter to canonical findings (where `canonical_id is null`) that need verification.

### Mode-dependent verification scope

| Mode | Scope | Fuzz variants |
|------|-------|---------------|
| `light` | (skipped — this phase doesn't run) | N/A |
| `core` | ALL canonical findings severity ≥ Medium + ALL chain hypotheses (CH-N) | NO |
| `thorough` | ALL canonical findings of ANY severity + ALL chain hypotheses | YES for Medium+ |

Chain hypotheses (CH-N from `chain_hypotheses.md`) get **priority** — verify them first. Chains that compose multiple findings produce the strongest PoCs.

### Build the queue

```
Queue order:
  1. Chain hypotheses (CH-1, CH-2, ...) — highest priority
  2. CONFIRMED findings severity >= Critical
  3. CONFIRMED findings severity == High
  4. CONFIRMED findings severity == Medium
  5. PARTIAL findings severity >= Medium (may produce FORK-FAIL → finding becomes FALSE_POSITIVE)
  6. (thorough only) ALL remaining findings: Low, Informational
```

---

## STEP 2 — Per-finding verification

For each queued finding, follow this procedure:

### 2a — Read the finding's full body

Read the relevant `verify_<id>.md` or extract from `findings_routed.json` + the matching depth/chain output file. You need:
- Title, severity, location (file:line)
- Description (what's wrong)
- Proof (what concrete sequence triggers it)
- Verified quote (±2 lines from source)
- Preconditions (state/access/timing/external/balance)
- For chains: the enabler + blocked finding pair + combined attack sequence

### 2b — Re-read source at the cited location

Use the Read tool to fetch `location.file:location.line_start - location.line_end`. If the cited code has changed since the finding was written, or if the bug is no longer present (e.g., refactor), mark `verify_<id>: REFUTED` and skip PoC writing.

### 2c — Pick the right PoC strategy per language

Read `{{SCRATCHPAD}}/build_status.md` for `LANGUAGE` and build status. Pick strategy by language:

#### EVM (Foundry preferred)

```bash
# 1. Set up Foundry project at {{PROJECT_ROOT}}/audit-poc/ if it doesn't exist
forge init --no-git audit-poc
cd audit-poc

# 2. Configure foundry.toml with the fork-url
echo "[profile.default]
src = 'src'
test = 'test'
fork_block_number = 12345678
[rpc_endpoints]
mainnet = '\${ETH_RPC_URL}'" > foundry.toml

# 3. Write the test at test/Exploit_<finding_id>.t.sol
# 4. Run: forge test --match-test test_<finding_id> --fork-url $ETH_RPC_URL -vvv
```

| Network | RPC URL |
|---------|---------|
| Ethereum | `https://eth.llamarpc.com` |
| Arbitrum | `https://arb1.arbitrum.io/rpc` |
| Optimism | `https://mainnet.optimism.io` |
| Base | `https://mainnet.base.org` |
| Polygon | `https://polygon-rpc.com` |
| BSC | `https://bsc-dataseed1.binance.org` |

#### Solana (LiteSVM preferred for in-process, solana-test-validator for full fork)

```bash
# LiteSVM (in-process simulation)
cargo test --test exploit_<finding_id> -- --nocapture

# Or fork:
solana-test-validator \
    --bpf-program <PROGRAM_ID> target/deploy/<PROGRAM>.so \
    --url https://api.mainnet-beta.solana.com \
    --reset
```

#### Stellar / Soroban

```bash
# Local invocation with mock host
soroban contract test --filter test_exploit_<finding_id>
```

#### Aptos

```bash
# Local Move test
aptos move test --filter test_exploit_<finding_id>
```

#### Sui

```bash
# Local Move test
sui move test --filter test_exploit_<finding_id>
```

#### C/C++ (rippled, Bitcoin Core)

```bash
# Local unit test in project's existing harness — fork is not feasible
cmake --build build --target unittests
./build/unittests --filter Exploit_<finding_id>
```

If the build is broken or fork is unavailable: fall back to `[CODE-TRACE]` (manual walkthrough with concrete numbers). This caps severity at CONTESTED per `rules/severity-decision-tree.md`.

### 2d — Write the PoC test

**Plain English requirement (HARD)**: every comment inside the PoC MUST follow `{{SKILL_ROOT}}/rules/plain-english-style.md`. The cheatcode itself stays as code (e.g. `vm.prank(attacker)`) but the comment beside it is plain English (`// next call comes from the attacker`).

#### Foundry cheatcode comment dictionary (EVM)

| Code | Plain-English comment |
|------|----------------------|
| `vm.prank(attacker)` | `// next call comes from the attacker` |
| `vm.startPrank(addr)` | `// every call below is signed by addr until vm.stopPrank` |
| `vm.deal(addr, n)` | `// give addr this much ETH so it can pay gas` |
| `vm.store(addr, slot, value)` | `// force the contract's storage to a state we want to test` |
| `vm.warp(timestamp)` | `// jump the block time forward to this timestamp` |
| `vm.roll(blockNumber)` | `// jump to this block number` |
| `vm.expectRevert(...)` | `// the next call should fail with this revert reason` |
| `assertEq(a, b, "msg")` | (the assertion message itself in plain English) |
| `assertGt(a, b, "msg")` | (assertion msg explains the expected number relation in plain English) |

#### Test structure

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/<contract>.sol";

contract Exploit_<FindingId> is Test {
    address attacker = makeAddr("attacker");
    address victim   = makeAddr("victim");
    <ContractType> target;

    function setUp() public {
        // forked from mainnet at block N; target is the live deployment
        target = <ContractType>(<deployed_address>);
        vm.deal(attacker, 1 ether);     // attacker has 1 ETH for gas
        vm.deal(victim, 100 ether);     // victim has funds to lose
    }

    function test_<finding_id>_drain() public {
        // === before ===
        uint256 attackerBalBefore = address(attacker).balance;
        uint256 victimDepositBefore = target.depositOf(victim);

        // === attack sequence (per finding's attack_sequence) ===
        vm.startPrank(victim);
        target.deposit{value: 100 ether}();  // victim deposits 100 ETH
        vm.stopPrank();

        vm.prank(attacker);
        target.exploitFunction(victim);      // run the attack on victim's deposit

        // === after ===
        uint256 attackerBalAfter = address(attacker).balance;
        uint256 victimDepositAfter = target.depositOf(victim);

        // === assertions ===
        assertGt(attackerBalAfter, attackerBalBefore + 99 ether,
            "attacker should have drained > 99 ETH from victim but did not");
        assertEq(victimDepositAfter, 0,
            "victim's deposit should be zero after drain but was not");
    }
}
```

#### Solana / Anchor test structure

```rust
use anchor_client::solana_sdk::signature::Keypair;
use litesvm::LiteSVM;

#[test]
fn test_<finding_id>_drain() {
    let mut svm = LiteSVM::new();
    let attacker = Keypair::new();
    let victim   = Keypair::new();

    // give actors lamports for fees
    svm.airdrop(&attacker.pubkey(), 1_000_000_000).unwrap();
    svm.airdrop(&victim.pubkey(), 100_000_000_000).unwrap();

    // === before ===
    let attacker_bal_before = svm.get_balance(&attacker.pubkey()).unwrap();

    // === attack sequence ===
    // (build and submit the malicious instruction sequence)

    // === after ===
    let attacker_bal_after = svm.get_balance(&attacker.pubkey()).unwrap();

    // === assertion ===
    assert!(attacker_bal_after > attacker_bal_before + 99_000_000_000,
        "attacker should have drained victim but did not");
}
```

### 2e — Variant exploration BEFORE marking FALSE_POSITIVE

If the first PoC fails (compiles but assertions don't hit), do NOT immediately mark FALSE_POSITIVE. Try at least one variant:

| Failure mode | Variant to try |
|--------------|----------------|
| Same-block attack didn't work | Multi-block sequence: warp time forward between calls |
| Specific amount didn't drain | Range — try 0, 1, MAX, typical values |
| A-then-B ordering failed | B-then-A ordering |
| Empty initial state failed | Post-loss / post-pause / post-deposit state |
| Direct call failed | Wrapped: Batch / Multicall / Delegate / Sponsor |

After 2+ variant failures with concrete numbers, `[FORK-FAIL]` is justified — mark the finding FALSE_POSITIVE and explain WHICH variants you tried.

### 2f — Fuzz variant (thorough mode, Medium+ findings only)

After the specific PoC passes, write a SECOND test with the key parameters fuzzed. Catches attack variants the agent didn't manually consider.

| Language | Fuzz invocation |
|----------|-----------------|
| EVM Foundry | `forge test --match-test testFuzz_<finding_id> -vvv` (use `bound(input, min, max)`) |
| Solana | proptest with bounded inputs OR Trident if available (see `{{SCRATCHPAD}}/build_status.md` for `TRIDENT_AVAILABLE`) |
| Aptos/Sui | 3-5 parameterized `#[test]` functions covering min / mid / max |
| C/C++ | rippled-style parameterized test cases |

If the specific PoC passed but fuzz finds an EARLIER violation (smaller amount, simpler sequence) → update the verification to use the fuzz-found inputs and report the simpler attack.

---

## STEP 3 — Write per-finding verification file

For EACH verified finding, write `{{SCRATCHPAD}}/verify_<finding_id>.md` using the markdown finding format from `{{SKILL_ROOT}}/rules/finding-output-format.md`:

```markdown
## Finding [<finding_id>]: <title> [VERIFIED|UNVERIFIED|CONTESTED]

**Verdict**: CONFIRMED | PARTIAL | REFUTED | CONTESTED | FALSE_POSITIVE
**Severity**: Critical | High | Medium | Low | Informational
**Location**: `<file>:L<start>-L<end>`
**Evidence**: [FORK-PASS] / [POC-PASS] / [CODE-TRACE] / [FORK-FAIL]

**verified**: |
  L<n>:   <pasted source line>
  L<n+1>: <pasted source line>
  L<n+2>: <pasted source line>

**Description**:
(Four sentences, plain English per rules/plain-english-style.md:
 1. What is wrong
 2. Why that matters
 3. Who can trigger it
 4. What the user sees)

**Impact**: <one-two sentences in user terms; dollar / percent numbers preferred>

**Attack Sequence**:
1. <step 1 in plain English>
2. <step 2>
3. <step 3>
...

**PoC Result**:
- Test file: <path>
- Test command: <exact command>
- Result: PASS | FAIL | REVERT
- Key assertion output: <paste the assertion line that proves the attack>
- Variants tried (if any): <list>
- Fuzz variant (thorough only): PASS (N runs) | VIOLATION_FOUND (input=X) | SKIPPED | NOT_APPLICABLE

**Recommendation**:
<one sentence stating the fix>

```diff
- <existing broken line>
+ <fixed line>
```

<one sentence stating what the fix prevents>

### Precondition Analysis (if PARTIAL or REFUTED)
**Missing Precondition**: <what blocks the attack today>
**Precondition Type**: STATE / ACCESS / TIMING / EXTERNAL / BALANCE

### Postcondition Analysis (if CONFIRMED or PARTIAL)
**Postconditions Created**: <what is now true that was not true before>
**Who Benefits**: <name the actor: permissionless attacker / role X / etc>
```

### Status header convention

- `[VERIFIED]` — Verdict is CONFIRMED and evidence is FORK-PASS or POC-PASS
- `[UNVERIFIED]` — Verdict is CONFIRMED but evidence is CODE-TRACE only (no execution)
- `[CONTESTED]` — Verdict was previously CONFIRMED but PoC produced FORK-FAIL after variant exploration; or verifier and depth agent disagree
- `[FALSE_POSITIVE]` — PoC failed across multiple variants; finding moved to Appendix A

---

## STEP 4 — Update findings_routed.json (in-place)

After all verify_*.md files are written, update `{{SCRATCHPAD}}/findings_routed.json` in-place:

For each finding, set:
- `verdict` field (`CONFIRMED` / `PARTIAL` / `REFUTED` / `CONTESTED` / `FALSE_POSITIVE`)
- `verifier_notes` field — short summary of PoC command + result
- `evidence_tags` field — append the PoC-derived tags ([FORK-PASS], [POC-PASS], [CODE-TRACE], [FORK-FAIL])
- For PARTIAL findings: populate `preconditions` array
- For CONFIRMED findings: populate `postconditions` array

This is a JSON edit — do it cleanly to keep the file schema-valid (v1.0).

---

## Required outputs (driver gate checks for these)

- `{{SCRATCHPAD}}/verify_*.md` (glob; ≥ 1 file required)

Each file must use the `## Finding [X-NN]: Title [<STATUS>]` header format. Content gate parses these.

## Retry hint (if any)

{{RETRY_HINT}}

When every queued finding has a verify_ file with a verdict (CONFIRMED / PARTIAL / REFUTED / CONTESTED / FALSE_POSITIVE) and findings_routed.json is updated in-place, exit cleanly. Do not write the final report — Phase 5d (validator) and Phase 6 (report) run separately.
