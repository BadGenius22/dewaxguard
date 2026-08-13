# Rust Quirks — Critical Reference

> **READ THIS BEFORE ANY RUST AUDIT.** Captures Rust-language semantics that produce **invalid findings**
> (look sound in theory, can't occur in production) or **missed bugs** when misunderstood. Spans two very
> different threat models that share the language:
> - **Smart contracts**: Solana/Anchor & Pinocchio, Soroban, CosmWasm, Substrate `pallet`/`ink!`, NEAR.
> - **Node clients / consensus**: Agave (Solana), Substrate/Polkadot node, reth, and other L1/L2 infra
>   (audited via `dewaxdlt`).
>
> The single most important habit: **read `Cargo.toml` profiles and the runtime model BEFORE writing any
> arithmetic / panic / determinism finding.** Half of all invalid Rust findings die on those two checks.

---

## 🚨 #0 — Cargo.toml & runtime preflight (DO THIS FIRST)

Before any finding, record these — they decide whether a whole class of findings is valid:

- [ ] **`[profile.release] overflow-checks`** — is it `true`? (Solana/Substrate/CosmWasm projects very often
  set it.) If `true`, arithmetic overflow **panics**, it does NOT silently wrap. A "silent overflow corrupts
  accounting" finding is then **INVALID** — the real behavior is a panic/abort (see #1).
- [ ] **`panic = "abort"` vs `"unwind"`**, and **`#![no_std]`** (contracts are usually `no_std`).
- [ ] **Runtime panic semantics** for the target (see #2): does a panic *revert one tx atomically* (Solana
  instruction, CosmWasm execute) or *brick consensus* (Substrate runtime `on_initialize`/`on_finalize`)?
- [ ] **Determinism domain**: is this code re-executed by every validator/replayer (consensus-critical) or
  run once off-chain? Decides whether #3/#4 (HashMap order, floats) are splits or non-issues.
- [ ] **Dependency versions** (`Cargo.lock`) — known-vuln crates (`RUSTSEC`), and for contracts the framework
  version (Anchor, cosmwasm-std, frame) gates which built-in checks exist.

---

## 🚨 #1 — Integer overflow: debug panics, release wraps (UNLESS overflow-checks)

### The Misconception
> "`a + b` overflows and silently wraps, corrupting the balance."

### The Reality
- **Debug builds**: overflow **panics**.
- **Release builds (default)**: overflow **wraps silently** (two's complement) — *unless* `overflow-checks =
  true`, in which case release **also panics**.

So the finding's validity depends entirely on the build profile (#0) AND the panic semantics (#2):
- `overflow-checks = true` (common in deployed contracts) → overflow **panics** → on Solana/CosmWasm that's a
  safe **tx revert**, not corruption. "Silent wrap drains funds" is **INVALID**.
- `overflow-checks` absent/false → it really does wrap → valid silent-corruption candidate.

### The Fix Pattern
```rust
// Auditing intent matters — which is correct here?
let x = a.checked_add(b).ok_or(Error::Overflow)?;  // explicit, profile-independent  ✅
let y = a.saturating_add(b);   // clamps at MAX — can be a BUG (wrong accounting, see #5)
let z = a.wrapping_add(b);     // wraps on purpose — almost always a BUG in value code
let w = a + b;                 // behavior depends on profile — flag it, check Cargo.toml
```

### Checklist
- [ ] Read `overflow-checks` first. State it in the finding.
- [ ] Bare `+ - * <<` on value/accounting types with `overflow-checks=false` → real wrap candidate.
- [ ] `wrapping_*` in financial math → almost always a bug. `saturating_*` → check it's not silently clamping.

---

## 🚨 #2 — `panic!` / `unwrap` / `expect` / `v[i]` / `unreachable!` — impact is context-dependent

### The Misconception
> "There's an `.unwrap()` on user input — instant fund loss." (or, conversely) "It's just a panic, harmless."

### The Reality
A panic's impact is entirely set by **where it runs**:

| Context | A panic means | Typical severity |
|---|---|---|
| **Solana instruction** (Agave runtime) | the instruction aborts; tx reverts **atomically** | usually safe (DoS of *that* tx); High only if it **bricks a required path** (e.g. can't ever close/withdraw) |
| **CosmWasm `execute`/`query`** | message reverts; `query` panic can break clients | DoS-of-tx; griefing if on a shared path |
| **Substrate runtime** (`on_initialize`, `on_finalize`, dispatchables) | **NO revert** — a panic in block execution can **halt/brick the chain** | **Critical** (consensus) |
| **Node client** (Agave, Substrate node, reth) on untrusted input | process **crash** → if on block path, **chain halt** | **Critical** (see dewaxdlt `parser-panic`) |
| **ink!** message | reverts the message | DoS-of-call |

### Checklist
- [ ] Identify the execution context before rating ANY panic finding.
- [ ] Solana: a panic that only reverts a tx is **not** "fund loss" — unless it makes a needed action
  **permanently impossible** (then it's a freeze). Don't over-rate; don't under-rate the brick case.
- [ ] Substrate runtime / node block path: panic on reachable input → escalate (no atomic revert exists).
- [ ] Watch the silent panickers: `v[i]` indexing (use `.get`), slicing `s[a..b]`, `.unwrap()`,
  `.expect()`, integer `as` in some paths, `array[const]`, `unreachable!()`, `assert!`, division by zero,
  `[T; N]` with bad N.

---

## 🚨 #3 — `HashMap` iteration order is non-deterministic (consensus split)

### The Misconception
> "Iterating this map to compute a value — order doesn't change the result."

### The Reality
`std::collections::HashMap` uses a **randomized** hasher (`RandomState`) → iteration order differs per
process/run. If the iteration result feeds **consensus-critical** state (a hash, a block, a state root, a
reward/slash distribution) and the code is **re-executed by every validator/replayer**, different orders →
**different results → chain split**. (Same failure class as Go map iteration.)

Even within a single contract: a Solana program that ranges a `HashMap` and whose output lands in chain
state will diverge when replayers iterate differently.

### The Fix Pattern
```rust
use std::collections::BTreeMap;          // deterministic key order  ✅
// or collect + sort before use:
let mut keys: Vec<_> = map.keys().copied().collect();
keys.sort();
for k in keys { /* deterministic */ }
```

### Checklist
- [ ] Any `HashMap`/`HashSet` iteration whose result touches consensus state → split candidate; expect `BTreeMap`.
- [ ] Also a **HashDoS** angle: custom/weak hashers (or `FxHashMap`) on attacker-controlled keys → O(n²)
  collisions (resource-exhaustion). `std` SipHash mitigates this; custom hashers may not.

---

## 🚨 #4 — Floating point = non-determinism + banned in many runtimes

### The Reality
`f32`/`f64` results can differ across architectures/compilers (rounding, FMA, NaN payloads, `to_string`).
In **consensus-critical** code → **split**. Solana's SBF and Substrate Wasm strongly discourage/forbid
floats in on-chain math; many frameworks reject them. A finding "uses float, will fork" is valid **only** if
the float result actually lands in replayed state — confirm it's not an off-chain/metric/log value.

### Checklist
- [ ] Any `f32/f64` on a state-transition path → split candidate (confirm it's consensus-critical, #0).
- [ ] `NaN`: `NaN != NaN`, `partial_cmp` returns `None`; sorting/`Ord` on floats panics or misorders.

---

## 🚨 #5 — `saturating_*` and `as` casts: silent wrong values (no panic, no error)

### The Reality
These never panic and never return `Err` — they silently produce a **wrong number**:
- `saturating_sub`: `3u64.saturating_sub(5) == 0` — underflow becomes 0. In accounting this silently erases
  debt/clamps balances → a real, easy-to-miss logic bug (not a panic, not a wrap).
- `as` casts **truncate / reinterpret silently**: `300u32 as u8 == 44`; `(-1i64) as u64 == u64::MAX`;
  `u64 as usize` differs on 32-bit; `f64 as u64` saturates/zeros on NaN. No overflow check applies to `as`.

### Checklist
- [ ] `saturating_sub` on balances/debt → is clamping-to-0 the intended semantic, or hidden underflow?
- [ ] Every `as` on a value/length/index → check for truncation & sign change. Prefer `try_into()? `.
- [ ] `overflow-checks` does **NOT** catch `as` truncation or `saturating_*`/`wrapping_*` — they're explicit.

---

## 🚨 #6 — Reentrancy: do NOT assume the EVM model

### The Reality
The reentrancy surface is framework-specific, not EVM-style:
- **Solana**: the runtime **forbids** a program from being reentered via CPI (except trivial self-recursion
  rules); CPI depth is capped. Classic EVM reentrancy "drain via callback" usually **does not port** —
  flagging it blindly is an invalid finding. The real Solana analogues are CPI to an **attacker-controlled
  program**, account-reload-after-CPI staleness, and missing reload of mutated accounts.
- **CosmWasm**: reentrancy **is** possible via **submessages / `reply`** — state mutated between dispatch and
  reply, or a malicious callback contract, is a genuine surface.
- **ink! / Substrate contracts**: cross-contract calls **can** reenter (historically demonstrated) — check.
- **Substrate runtime (pallets)**: no external calls mid-dispatch in the EVM sense, but **`ensure!`-after-
  mutation** and storage-write ordering bugs play a similar role.

### Checklist
- [ ] Name the framework before rating reentrancy. Solana EVM-style reentrancy → likely invalid.
- [ ] CosmWasm: trace `SubMsg`/`reply` state assumptions. ink!/Substrate-contracts: trace cross-contract calls.
- [ ] Solana: focus on **account reload after CPI** and CPI to untrusted programs, not callback reentry.

---

## 🚨 #7 — `unsafe`, `transmute`, raw pointers, FFI (node clients & perf paths)

### The Reality
Memory safety bugs live in `unsafe` blocks, `std::mem::transmute`, raw pointer arithmetic, `from_raw_parts`,
and **FFI** (e.g. Firedancer C ↔ Rust glue, reth perf paths, zero-copy deserialization). Attacker-controlled
input reaching an `unsafe` region → OOB read/write, UB, type confusion → crash or worse. Rare in contracts
(SBF/Wasm sandbox), common and high-impact in **node clients**.

### Checklist
- [ ] Grep `unsafe`, `transmute`, `from_raw_parts`, `get_unchecked`, `set_len`, `MaybeUninit`, `extern "C"`.
- [ ] For each: is the safety invariant actually upheld for **attacker-controlled** sizes/offsets/lifetimes?
- [ ] `get_unchecked`/`get_unchecked_mut` with an attacker index = OOB (no bounds check) — node-client crash.

---

## 🚨 #8 — Serialization: non-canonical encodings & trailing bytes (malleability / split)

### The Reality
On-chain Rust uses Borsh, bincode, SCALE (Substrate), protobuf, or `serde`. Pitfalls:
- **Non-canonical encodings**: two byte strings decode to the same value (or one decoder accepts trailing
  bytes another rejects) → **id malleability** or **cross-client split**. Borsh & SCALE are designed
  canonical; **bincode** and loose `serde` configs are not necessarily.
- **`#[serde(untagged)]` / enum discriminant ambiguity** → a payload parses as two variants.
- **Length-prefix without cap** → giant `Vec::with_capacity(n)` → OOM (resource-exhaustion).
- **Borsh/`BorshDeserialize` on enums**: an out-of-range discriminant must error, not panic — check the path.

### Checklist
- [ ] Does the decoder reject **trailing bytes**? Are encodings **canonical**? (split/malleability)
- [ ] Attacker-controlled length → bounded allocation? (OOM)
- [ ] Solana zero-copy (`bytemuck`, `Pod`/`Zeroable`) — alignment/size assumptions on untrusted data.

---

## 🚨 #9 — Ignored `Result`, swallowed errors, `?` on the wrong type

### The Reality
- `let _ = fallible();` and unused `Result` (sometimes only a warning) silently drop failures — a missing
  CPI/transfer/validation result that "succeeds" because nobody checked it.
- `?` early-returns — make sure it doesn't bypass a needed cleanup / state-consistency step (partial mutation
  then `?` → inconsistent state, esp. where there's no atomic revert like Substrate runtime).
- `ok()` converting `Result`→`Option` then `unwrap_or(default)` masks a real failure as a default value.

### Checklist
- [ ] Grep `let _ =`, `.ok();`, `unwrap_or(`, `#[must_use]` ignores on transfer/CPI/verify calls.
- [ ] `?` between a state mutation and its invariant restore → inconsistent-state candidate.

---

## 🚨 #10 — `Default`/zeroed state, `Option` defaulting, and account "init" assumptions

### The Reality
- `T::default()` zero-values can be a **valid-looking but unauthorized** state (e.g. a zeroed `Pubkey` =
  system program / a "null" authority that some check treats as match-anything).
- `unwrap_or_default()` on a missing value can grant default privileges/zero fees.
- Solana/Anchor: distinguish `init`, `init_if_needed` (reinit attacks), and account discriminator checks —
  but that's account-model detail (see `solana.md`); at the language level, watch zero/default coercion.

### Checklist
- [ ] Zeroed/`default()` `Pubkey`/`AccountId`/address compared in an auth check → privilege/bypass candidate.
- [ ] `unwrap_or_default()` on amounts/fees/authorities → does default grant something?

---

## Invalid Finding Patterns (withdraw before verification)

| Pattern | Why it's usually INVALID |
|---|---|
| "Integer overflow silently drains funds" **without checking `overflow-checks`** | If `overflow-checks=true` (common), it **panics** → on Solana/CosmWasm that's a safe revert, not corruption. Check `Cargo.toml` first (#0/#1). |
| "`.unwrap()` panic = fund loss" on a **Solana instruction** | A panic reverts the tx **atomically**; no partial state. Only valid if it permanently **bricks** a required action (freeze). Not generic "loss" (#2). |
| "EVM-style reentrancy drains the vault" on **Solana** | Runtime forbids program reentrancy via CPI; the EVM model doesn't port. Real surface is account-reload-after-CPI / untrusted CPI target (#6). |
| "Uses `f64`, will fork" on an **off-chain / metric / log** value | Determinism only matters for **replayed consensus state**. Confirm the float lands in chain state (#4). |
| "`HashMap` iteration is a bug" in code that **runs once off-chain** | Only a split if re-executed by validators/replayers. Off-chain ordering is harmless (#3). |
| "`saturating_sub` underflows" framed as a panic/overflow | It does neither — it **clamps to 0**. The bug (if any) is the **wrong clamped value**, a logic issue, not memory/panic (#5). |
| "Reentrancy guard missing" on a **Substrate pallet** dispatch with no external call | No mid-dispatch external call exists in the EVM sense; check `ensure!` ordering instead (#6). |

---

## History of Lessons

- *(seed)* **Rust audits, general**: The #1 source of rejected Rust findings is asserting silent integer
  overflow without reading `[profile.release] overflow-checks`. Always record it in finding #0.
- Add new entries here when a Rust finding is rejected due to a language/runtime quirk — this file only
  improves by accumulating pain.
