# Phase 5c: Mainnet Fork PoC Execution Rules

> **Purpose**: Mechanically prove findings on real deployed contracts. [FORK-PASS] is the strongest evidence.
> **Trigger**: All findings with severity >= Medium
> **Fallback**: If fork unavailable, use [POC-PASS] (unit test) or [CODE-TRACE] (manual)
> **Plain-English requirement (HARD)**: every comment inside a PoC file MUST follow `rules/plain-english-style.md`. Use the cheatcode-comment dictionary in that file. The PoC code uses real cheatcode names (e.g. `vm.prank`), but the comment next to the cheatcode must be plain English.

---

## Chain-Specific Fork Commands

### EVM (Foundry)

```bash
# Start Anvil fork
anvil --fork-url {RPC_URL} --chain-id {CHAIN_ID}

# Run test against fork
forge test --match-test testExploit --fork-url {RPC_URL} -vvv

# Or direct (no separate Anvil)
forge test --match-test testExploit --fork-url {RPC_URL} -vvv
```

**RPC URLs**:
| Network | URL |
|---------|-----|
| Ethereum | `https://eth.llamarpc.com` or `$ETH_RPC_URL` |
| Arbitrum | `https://arb1.arbitrum.io/rpc` |
| Optimism | `https://mainnet.optimism.io` |
| Base | `https://mainnet.base.org` |
| Polygon | `https://polygon-rpc.com` |
| BSC | `https://bsc-dataseed1.binance.org` |

**Foundry Cheatcodes for PoC** — comments use plain English per `rules/plain-english-style.md`:
```solidity
vm.prank(attacker)           // next call comes from the attacker
vm.deal(addr, amount)        // give addr this much ETH so it can pay gas
vm.store(addr, slot, value)  // force the contract's storage to a state we want to test
vm.warp(timestamp)           // jump the block time forward to this timestamp
vm.roll(blockNumber)         // jump to this block number
vm.startPrank(addr)          // every call below comes from addr until vm.stopPrank
```

**Deployed-code provenance (verify BEFORE trusting repo HEAD)** — the audited repo is a hypothesis; the deployed bytecode is ground truth:
```bash
# 1. Resolve the live implementation behind the proxy (EIP-1967 impl slot)
cast implementation <PROXY> --rpc-url $ETH_RPC_URL
#   or: cast storage <PROXY> 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc
# 2. Membership-test each audited function against the DEPLOYED bytecode
cast code <IMPL> --rpc-url $ETH_RPC_URL > /tmp/deployed.hex
cast sig "yourAuditedFn(uint256,address)"   # 4-byte selector → grep it in /tmp/deployed.hex
```
If an audited selector is absent from the deployed bytecode, or the impl address is not what the scope names, STOP: the repo diverges from mainnet. Document "audited source differs from deployed" as a finding and re-scope — do not keep building PoCs against code that isn't live. (Solana equivalent: the mainnet program-ID / IDL-drift check under `### Solana`, point 3.)

### Solana

```bash
# CORRECT: clone the ACTUAL mainnet binary (--clone-upgradeable-program). DO NOT use --bpf-program <local.so> as that loads YOUR LOCAL build under the mainnet program ID — defeating the point of a fork test.
solana-test-validator --reset \
  --url https://api.mainnet-beta.solana.com \
  --clone-upgradeable-program {MAINNET_PROGRAM_ID_1} \
  --clone-upgradeable-program {MAINNET_PROGRAM_ID_2} \
  --ledger /tmp/<project>-fork-ledger

# Airdrop SOL to a fresh disposable keypair (NEVER use ~/mainnet.key)
solana-keygen new --no-bip39-passphrase --silent -o /tmp/<project>-payer.json --force
solana airdrop 5000 $(solana-keygen pubkey /tmp/<project>-payer.json) --url http://127.0.0.1:8899

# Point Anchor at the fork + disposable keypair (override BOTH so config/Anchor.toml defaults can't leak)
ANCHOR_WALLET=/tmp/<project>-payer.json \
ANCHOR_PROVIDER_URL=http://127.0.0.1:8899 \
yarn run ts-mocha -p ./tsconfig.json -t 1000000 tests/<fork-poc>.ts
```

**Important — three classes of gap a fork test catches that a local-build PoC misses** (Atomiq H-01, 2026-05-27):
1. **Anchor field-name camelCase mismatches.** Anchor's JS coder reads struct args by IDL field name (camelCase). A typo (e.g. `prevBlocktimestamps` instead of IDL's `prevBlockTimestamps`) makes the property `undefined` → silently encoded as zeros → the production binary's hash-of-struct check fails on the zeroed field. Mocked / local-build PoCs often don't exercise the encoding path. Mainnet-fork run surfaces this as `Custom:6000`-style errors instead of a clean assertion.
2. **`overflow-checks` profile divergence.** `cargo build --release` defaults to `overflow-checks = OFF`; production deploy profiles (Solana mainnet) typically enable them. Synthetic PoC values that don't represent realistic production state (e.g. `block_height = 1` in a relay that assumes height ≫ a pruning constant) panic in production but wrap silently in local. Choose PoC initial state to match production-scale assumptions, OR rebuild the local target with `[profile.release] overflow-checks = true` if you must use a local binary.
3. **IDL/binary drift.** The audited source's IDL may describe an older or newer interface than the deployed binary. `declare_id!` placeholders are common in Solana repos — verify the real mainnet IDs via the project's published SDK (`@<org>/chain-solana` → `Chains.ts`; see Phase: Recon STEP 4 Agent 1B method note about mainnet program ID verification). If audited-source IDL diverges from deployed binary, document the divergence as a separate finding ("audited source differs from deployed binary") — do NOT silently accept a local `[POC-PASS]`.

**Mainnet-safe by construction**:
- We use `--skip-build --skip-deploy` (or run ts-mocha directly) — no `anchor deploy` ever fires, so even if Anchor.toml is misconfigured the worst case is a localhost-only tx.
- `requestAirdrop` only works on test-validator — fails fast (`MethodNotFound`) if a misconfig accidentally points at mainnet.
- The clone-upgradeable-program flag fetches binaries once at validator startup; subsequent queries are local-only.
- **Do NOT clone state PDAs** (e.g. `--clone <pda>`). Only clone program binaries. State must be fresh so the PoC controls initialization.

**Alternative**: Use LiteSVM for in-process simulation without external validator.

### Aptos

```bash
# Local simulation with mainnet state
aptos move test --filter test_exploit
```

**Note**: Aptos doesn't have a native mainnet fork tool. Use local simulation with manually set state.

### Sui

```bash
# Local simulation
sui move test --filter test_exploit
```

**Note**: Sui doesn't have a native mainnet fork. Use local simulation or testnet deployment.

---

## PoC Writing Rules

### 1. REAL Contracts Only
- Call functions on the ACTUAL deployed contract (via fork)
- Do NOT use mocks for the target contract
- Mocks are OK for helper contracts (attacker contract, token setup)

### 2. Realistic Preconditions
- Use `vm.store` / state manipulation ONLY for conditions that naturally occur
- Document WHY the precondition is realistic
- If precondition requires admin action, note this in the finding

### 3. Concrete Assertions
Every PoC must prove a number changed in the attacker's favour. Use plain comments that explain the attack story.

```solidity
// BAD: just shows the function can be called — proves nothing about harm
attacker.exploit();

// GOOD: proves the attacker walks away with more tokens than they started with
uint256 balBefore = token.balanceOf(attacker);  // attacker's tokens before the attack
attacker.exploit();                             // run the attack
uint256 balAfter  = token.balanceOf(attacker);  // attacker's tokens after the attack
assertGt(balAfter, balBefore, "Attacker should have gained tokens but did not");
```

### 4. Use real names, round numbers, plain comments
```solidity
// Use names like attacker / victim / owner — never addr1, addr2.
address attacker = makeAddr("attacker");
address victim   = makeAddr("victim");

// Round numbers unless the exact number is the bug.
uint256 deposit = 1_000_000e6;  // 1M USDC

vm.deal(attacker, 1 ether);     // give attacker 1 ETH for gas
vm.startPrank(victim);          // every call below is signed by the victim
token.approve(address(vault), deposit);
vault.deposit(deposit);         // victim deposits 1M USDC
vm.stopPrank();
```

### 5. Variant Testing
Before marking `[FORK-FAIL]` → FALSE_POSITIVE:
- Try relaxing the timing (same-block → multi-block)
- Try different amounts (specific → range)
- Try different ordering (A-then-B → B-then-A)
- Try different initial state

After 2+ variant failures → `[FORK-FAIL]` is justified.

### 6. Common false signals — check before trusting a PoC result

- **A failing "should-be-blocked" test is often a test artifact, not a live bug.** A `vm.expectRevert` placed one line too early catches a *harmless setup call* (approve, deal, warp) — the revert fires there and the actual exploit path never runs, yet the test "passes" as if the guard were the finding. Before escalating any expect-revert PoC: trace with `-vvvv` and confirm the revert originates from the exploit call, not from setup. Prefer **arm-then-observe** — perform the setup unguarded, then wrap ONLY the exploit call in `try/catch` (or a raw `.call`) and assert on the observed outcome. (Twyne L-04 was a misplaced `expectRevert`, not a bug.)
- **Test BOTH economic regimes when a clamp/guard can neutralize the attack.** Over-collateralized or price-clamped systems (perps vaults, GMX-style share pricing) can make a share/price-manipulation attack a no-op in the *current* regime while it is live in another. Use `vm.store` to place the protocol in each regime (clamped vs unclamped, over- vs under-collateralized) and run the PoC in both — a `[FORK-FAIL]` in one regime is not a `[FORK-FAIL]` overall.

### 7. PoC Integrity Gate (HARD — a PoC is not evidence until all four pass)

> Global rule A-3 (`~/.claude/audit-method.md`): a test that cannot fail proves nothing. Writing the
> PoC is cheap; reading it is the work. All four checks below are mandatory and their results are
> recorded in the PoC output block. A PoC that skips a check is untagged, not `[FORK-PASS]`.

**7a — Mutation check (the one that catches a test proving nothing).**
Revert the bug and re-run the same test. The test MUST fail.

```solidity
// The finding says `withdraw` sends ETH before zeroing the balance.
// Mutation: patch the local copy to zero the balance FIRST, re-run testExploit.
// Required result: testExploit FAILS. If it still passes, the assertion is not
// measuring the bug — the result is void regardless of what it asserted.
```

How to mutate, in order of preference:
1. Patch the source line in a local fork of the contract and re-deploy it in the test (`deployCode`
   / `vm.etch` the fixed bytecode over the target address).
2. If the target is a live proxy, `vm.etch` a corrected implementation and re-point the impl slot.
3. If neither is possible, `vm.store` the state into the configuration the guard *would* have
   produced, and re-run.

Record: `mutation_check: PASS (test fails when guard restored)` or `FAIL (test still passes — void)`.

**7b — Positive control (mandatory before trusting any negative result).**
Before a `[FORK-FAIL]` or a FALSE_POSITIVE verdict stands, run a **known-good** operation through the
identical harness and confirm it succeeds: an ordinary deposit, a legitimate swap, a real historical
transaction replayed at the fork block. A broken harness and a hardened target both produce `FAIL`,
and they are not distinguishable without this.

This is not hypothetical. On Solana, surfpool substitutes a BPFLoader2 builtin for the SPL Token
program, so every CPI/token PoC dies at `InvalidAccountOwner` before reaching program logic —
including a known-good transaction. Without a positive control that reads as a refuted finding.

Record: `positive_control: PASS (known-good deposit succeeded)` or `SKIPPED (result was positive)`.

**7c — Real-path audit (mock vs real integration).**
Enumerate every address / program ID / account the test touches. For each, state: real deployed
identity (with the address) or explicitly labelled mock. Then assert the structural rule:

> **No mock may sit on the value flow the PoC is proving.**

A mock is acceptable for the attacker contract and for peripheral setup. A mocked oracle, a mocked
token on the drain path, or a mocked callee whose return value is the thing under test proves only
that the mock behaves as the model imagined it.

Record: `real_path: {addr} REAL, {addr} REAL, {name} MOCK (attacker contract, off value path)`.

**7d — Assertion audit.**
The assertion measures a balance or accounting delta in the attacker's favour, at a named address.
`assertTrue(success)`, "did not revert", and a bare `vm.expectRevert` are not assertions about harm.
Cross-check against §6's expect-revert artifact before accepting any negative-shaped assertion.

Record: `assertion: assertGt(token.balanceOf(attacker) after, before) — measured +$X`.

**Downgrade rule**: any of 7a–7d failing or unrecorded drops the evidence tag to `[CODE-TRACE]` at
best. `[FORK-PASS]` and `[POC-PASS]` both require all four.

---

## Evidence Tags

| Tag | Meaning | Weight |
|-----|---------|--------|
| `[FORK-PASS]` | Exploit confirmed on mainnet fork, **integrity gate §7 all-pass** | **Strongest** — mechanical proof |
| `[POC-PASS]` | Unit test passes against model/library code, **integrity gate §7 all-pass** | Strong |
| `[CODE-TRACE]` | Manual trace with concrete values, no execution — also the ceiling for any PoC that fails or skips §7 | Moderate |
| `[FORK-FAIL]` | Fork test failed — attack doesn't work as described. **Requires a passing §7b positive control** before it supports FALSE_POSITIVE | Negative |

---

## Output Format

```markdown
### Fork PoC: Finding X-NN

**Chain**: {Ethereum/Solana/Aptos/Sui}
**Contract**: {address}
**Fork RPC**: {RPC_URL}
**Block**: {block number at fork time}

**Attack story (one paragraph, plain English)**:
The attacker calls `withdraw` once. The function sends ETH before zeroing the
balance, so the attacker's contract calls `withdraw` again from inside the
ETH transfer. The balance is still its old value, so the second call also
pays out. The attacker repeats this until the vault is empty.

**Test Command**:
```bash
{exact command to reproduce}
```

**Test Code** (comments follow `rules/plain-english-style.md`):
```{language}
{minimal PoC code with plain comments}
```

**Output**:
```
{test output showing PASS}
```

**Integrity Gate** (§7 — all four required for a PASS tag):
```
mutation_check:   PASS — testExploit fails when the balance is zeroed before the send
positive_control: SKIPPED — result was positive
real_path:        0xA0b8...eB48 REAL (USDC), 0x1f98...F984 REAL (target), Attacker.sol MOCK (off value path)
assertion:        assertGt(usdc.balanceOf(attacker) 812_400e6 > 0) — measured +$812,400
```

**Evidence Tag**: [FORK-PASS]
**Financial Impact** (in dollars or percent): e.g. "Attacker drained 800 ETH (~$2.4M at fork block) — 100% of the vault."
```

---

## Self-check before saving the PoC

- [ ] Every comment explains *why*, not *what*.
- [ ] No comment uses banned jargon from `rules/plain-english-style.md` without a one-sentence definition.
- [ ] Variable names are role names (`attacker`, `victim`, `owner`) — no `addr1`/`addr2`.
- [ ] Numbers are round unless an exact number is the bug.
- [ ] The test asserts a number changed in the attacker's favour, not just that a function ran.
- [ ] **§7a mutation check ran and the test FAILED with the bug reverted** — recorded in the output block.
- [ ] **§7b positive control ran** if the result is negative (`[FORK-FAIL]` / FALSE_POSITIVE).
- [ ] **§7c every address/program the test touches is labelled REAL or MOCK**, and no MOCK sits on the value flow being proven.
- [ ] **§7d the assertion measures a balance/accounting delta at a named address**, not a revert or a success flag.
