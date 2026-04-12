# Phase 4b: Runtime/VM-Specific Attacks — EVM

> **Runtime**: Ethereum Virtual Machine (Ethereum, L2s, EVM-compatible chains)
> **Agent**: depth-runtime
> **Focus**: EVM execution model exploits, gas mechanics, cross-contract attacks

---

## SYSTEMATIC CHECKS

### A) Reentrancy (Cross-Contract)
```bash
grep -rn "\.call{value\|\.transfer(\|\.send(\|safeTransfer\|IERC721.*safeTransfer\|onERC721Received\|onERC1155Received\|tokensReceived" --include="*.sol" | grep -v test
```
1. **Classic**: ETH transfer via `.call{value}` before state update
2. **ERC-777 hooks**: `tokensReceived` callback on transfer
3. **ERC-721/1155 safe transfers**: `onERC721Received` / `onERC1155Received` callbacks
4. **Read-only reentrancy**: View function reads stale state during callback (affects other protocols reading this contract)
5. **Cross-contract**: Contract A calls B, B calls C, C re-enters A via different function

### B) Gas/Compute Attacks
1. **1/64th rule**: External calls forward at most 63/64 of remaining gas. Can insufficient gas cause silent failure?
2. **Returnbomb**: Malicious contract returns huge bytes, consuming caller's gas on memory expansion
3. **Gas griefing**: Relayer/keeper pays gas but attacker makes it expensive via loops/storage
4. **Block gas limit DoS**: Operation processes unbounded array, hits block gas limit
5. **gasleft() manipulation**: `gasleft()` used in calculations — manipulable by gas provided

### C) Balance/Value Injection
```bash
grep -rn "address\(this\)\.balance\|balanceOf\(address\(this\)\)" --include="*.sol" | grep -v test
```
1. **selfdestruct/coinbase injection**: Forces ETH into contract without triggering receive/fallback
2. If contract uses `address(this).balance` for accounting → manipulable
3. **ERC-20 donation**: Direct transfer inflates `balanceOf` — affects vault-style contracts

### D) CREATE2 / Deterministic Deployment
```bash
grep -rn "CREATE2\|create2\|new.*salt\|cloneDeterministic" --include="*.sol" | grep -v test
```
1. **Address prediction**: Attacker pre-computes CREATE2 address, interacts before deployment
2. **Redeployment**: After selfdestruct, same address can be redeployed with different code
3. **Front-running deployment**: If deployment tx is public, attacker deploys first with malicious code at the same address

### E) EIP-712 / Signature Attacks
```bash
grep -rn "DOMAIN_SEPARATOR\|_hashTypedDataV4\|ecrecover\|ECDSA\|permit\|nonce\|EIP712" --include="*.sol" | grep -v test
```
1. **Cross-chain replay**: Same contract deployed on multiple chains with same domain separator
2. **Cross-contract replay**: Signature valid for contract A also valid for contract B
3. **Nonce management**: Sequential nonces (ERC-2612) vs bitmap nonces (ERC-4337). Can nonce be skipped/reused?
4. **Signature malleability**: ecrecover returns address(0) for invalid sig — is this checked?
5. **Permit front-running**: Permit tx can be front-run by extracting the signature from mempool
6. **Deadline bypass**: `block.timestamp == deadline` — is boundary inclusive or exclusive?

### F) Proxy/Upgrade Attacks
1. **Uninitialized implementation**: Implementation contract not initialized — attacker calls `initialize()`
2. **Storage layout mismatch after upgrade**: New variable inserted before existing ones
3. **UUPS: missing _authorizeUpgrade guard**: Anyone can upgrade
4. **Transparent proxy: admin calls forwarded to impl**: Admin accidentally calls user function

### G) Token Standard Edge Cases
1. **Fee-on-transfer tokens**: `balanceOf` after transfer less than amount sent
2. **Rebasing tokens**: Balance changes without transfer events
3. **ERC-20 with no return value**: `transfer()` returns nothing (USDT on some chains)
4. **Pausable tokens**: Transfer reverts during pause, blocking time-sensitive operations
5. **Blacklistable tokens**: USDC/USDT can blacklist addresses, freezing funds
6. **ERC-777 hooks**: Transfer triggers callback — reentrancy vector

### H) Multi-Chain Deployment Differences
1. **Block time**: 12s (Ethereum) vs 2s (L2s) — affects timestamp-based logic
2. **PUSH0 opcode**: Not supported on all L2s — deployment may fail
3. **Sequencer downtime (L2)**: Chainlink sequencer uptime feed needed
4. **block.number meaning**: L1 block vs L2 block — different on Arbitrum/Optimism
5. **msg.sender in L2**: Cross-domain messages have different sender semantics
