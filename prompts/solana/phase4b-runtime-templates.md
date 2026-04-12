# Phase 4b: Runtime/VM-Specific Attacks — Solana

> **Runtime**: Solana SVM (Solana Virtual Machine)
> **Agent**: depth-runtime
> **Focus**: Solana account model exploits, CPI trust, compute units, PDAs, tx composition

---

## SYSTEMATIC CHECKS

### A) Account Aliasing / Duplication
```bash
grep -rn "remaining_accounts\|ctx\.remaining_accounts" programs/ --include="*.rs" | grep -v target | grep -v test
```
1. **Same account as two params**: Can attacker pass the same Pubkey for two different account fields?
2. **remaining_accounts dedup**: Is there any check preventing duplicate accounts in remaining_accounts?
3. **Double-counting**: If same account appears twice, are values double-counted in loops?
4. Anchor's `#[account]` constraints prevent some aliasing but NOT for remaining_accounts
5. **Type confusion via remaining_accounts**: Can a market account be passed where an oracle feed is expected?

### B) Compute Unit (CU) Exhaustion
1. **Partial state update**: If CU runs out between two state writes, tx reverts entirely (atomic). BUT:
2. **Revertible patterns**: Does the program use manual revert mechanisms? Do they depend on CU being sufficient?
3. **CU manipulation**: Attacker provides many remaining_accounts (oracle feeds) to consume CU
4. **CU-dependent branching**: Does any code check `sol_remaining_compute_units()` and branch differently?
5. **Large account deserialization**: zero_copy avoids this, but Borsh-deserialized accounts consume CU proportional to size

### C) Stack/Heap Overflow
```bash
grep -rn "Box::new\|Vec::new\|vec!\|String::new\|request_heap_frame" programs/ --include="*.rs" | grep -v target | grep -v test
```
1. **Stack**: 4096 bytes per frame. Deep call chains (instruction → handler → ops → model → utils) can overflow
2. **Heap**: 32KB default (256KB with `request_heap_frame`). Many accounts + large structs = exhaustion
3. **Build warnings**: Check `anchor build` output for stack overflow warnings — these are real
4. **Recursive calls**: Any recursion = potential stack overflow with crafted input

### D) PDA Security
```bash
grep -rn "find_program_address\|Pubkey::create_program_address\|seeds\s*=" programs/ --include="*.rs" | grep -v target | grep -v test
```
1. **Seed collision**: Two different logical entities producing the same PDA?
2. **User-controlled seeds**: Are user-provided seed components length-delimited?
3. **Bump canonicalization**: Is `find_program_address` used (canonical bump) or `create_program_address` (any bump)?
4. **Cross-program PDA**: Can program A create a PDA that collides with program B's PDA?
5. **PDA as signer**: If PDA signs a CPI, can the CPI target do something unexpected?

### E) Instruction Composition (Same TX)
```bash
grep -rn "load_instruction_at\|Sysvar1nstructions\|sysvar::instructions\|get_instruction_relative" programs/ --include="*.rs" | grep -v target | grep -v test
```
1. **Multi-instruction TX**: Can attacker compose create + execute in one TX?
2. **State between instructions**: First instruction modifies state, second reads it — is this expected?
3. **Sysvar introspection**: Does program check what other instructions are in the TX? (If not, composition is unrestricted)
4. **Flash loan via composition**: Borrow in ix1, use in ix2, repay in ix3 — all in one TX

### F) CPI Trust Boundaries
```bash
grep -rn "invoke\(\|invoke_signed\(\|CpiContext::new\b\|CpiContext::new_with_signer" programs/ --include="*.rs" | grep -v target | grep -v test
```
1. **Program ID validation**: Is the CPI target program ID hardcoded or passed as account?
2. **Account forwarding**: Which accounts are passed to the CPI? Can attacker control them?
3. **Signer seed leaking**: Are PDA signer seeds derivable by the CPI target?
4. **Post-CPI reload**: After CPI, are modified accounts reloaded before reading?
5. **Return data**: Does the program use `sol_get_return_data`? Can CPI target return malicious data?
6. **Callback re-entrancy**: If CPI target calls back into this program, what state is it in?

### G) Token Account Security
```bash
grep -rn "token::transfer\|transfer_checked\|TokenAccount\|token::mint_to\|token::burn" programs/ --include="*.rs" | grep -v target | grep -v test
```
1. **Token account ownership**: Is `token_account.owner == expected_owner` verified?
2. **Mint matching**: Is `token_account.mint == expected_mint` verified?
3. **Delegate abuse**: Can `token_account.delegate` be set to attacker's address?
4. **Close account drain**: Closing a token account sends remaining lamports — to whom?
5. **Token-2022 extensions**: TransferFeeConfig, PermanentDelegate, FreezeAuthority — handled?

### H) Clock/Timestamp Manipulation
1. **Slot vs timestamp**: Solana slots are ~400ms but can vary. `Clock::get()?.unix_timestamp` has ~2s drift
2. **Slot-based vs time-based**: If logic uses slots, validator can slightly manipulate slot timing
3. **Stale clock**: In same TX, clock is constant. Between TXs in same block, also constant
4. **Epoch boundaries**: State dependent on epoch number? Epoch transitions can cause unexpected behavior
