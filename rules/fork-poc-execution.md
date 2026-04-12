# Phase 5c: Mainnet Fork PoC Execution Rules

> **Purpose**: Mechanically prove findings on real deployed contracts. [FORK-PASS] is the strongest evidence.
> **Trigger**: All findings with severity >= Medium
> **Fallback**: If fork unavailable, use [POC-PASS] (unit test) or [CODE-TRACE] (manual)

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

**Foundry Cheatcodes for PoC**:
```solidity
vm.prank(attacker)           // Impersonate caller
vm.deal(addr, amount)        // Set ETH balance
vm.store(addr, slot, value)  // Set storage slot (simulate state)
vm.warp(timestamp)           // Set block.timestamp
vm.roll(blockNumber)         // Set block.number
vm.startPrank(addr)          // Persistent impersonation
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
```solidity
// BAD: just shows the function can be called
attacker.exploit();

// GOOD: proves the financial impact
uint256 balBefore = token.balanceOf(attacker);
attacker.exploit();
uint256 balAfter = token.balanceOf(attacker);
assertGt(balAfter, balBefore, "Attacker gained tokens");
```

### 4. Variant Testing
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

**Test Command**:
```bash
{exact command to reproduce}
```

**Test Code**:
```{language}
{minimal PoC code}
```

**Output**:
```
{test output showing PASS}
```

**Evidence Tag**: [FORK-PASS]
**Financial Impact**: {concrete numbers from the test}
```
