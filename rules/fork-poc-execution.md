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

### Solana

```bash
# Fork mainnet with program loaded
solana-test-validator \
  --bpf-program {PROGRAM_ID} target/deploy/{PROGRAM}.so \
  --url https://api.mainnet-beta.solana.com \
  --reset

# Run test against local validator
cargo test --test fork_poc -- --nocapture
```

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

---

## Evidence Tags

| Tag | Meaning | Weight |
|-----|---------|--------|
| `[FORK-PASS]` | Exploit confirmed on mainnet fork | **Strongest** — mechanical proof |
| `[POC-PASS]` | Unit test passes against model/library code | Strong |
| `[CODE-TRACE]` | Manual trace with concrete values, no execution | Moderate |
| `[FORK-FAIL]` | Fork test failed — attack doesn't work as described | Negative |

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
