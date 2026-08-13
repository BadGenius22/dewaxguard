# Sui Move Platform Quirks — Critical Reference

> **READ THIS BEFORE ANY SUI AUDIT.** This document corrects misconceptions that produce invalid findings — things that look like bugs in EVM/database mental models but cannot occur under Sui's object + consensus model. Every Sui recon, breadth, depth, and verification agent should have this in context.
>
> **Origin**: v1.21.0 blind-benchmark run surfaced the #1 quirk below — an agent was about to mis-frame (and the `sui-shared-object-race` benchmark's own ground truth *does* mis-frame) an EVM-style lost-update race on a Sui shared object. Sui's consensus prevents exactly that.

---

## 🚨 #1 — Shared-object access is consensus-serialized (no EVM-style read-then-write race)

### What auditors often assume (WRONG)

> "Two transactions call `deposit(&mut Pool, ...)` concurrently. Both read the old `total_depositors`, both increment by 1, so the counter ends up +1 instead of +2 — a lost-update race."

### What actually happens (CORRECT)

A transaction that takes a **shared object** as a `&mut` (or owned-value) input acquires exclusive access to that object for the duration of the transaction. Sui sequences all transactions touching a given shared object through **consensus (Mysticeti/Bullshark)** into a total order, then executes them one at a time against that object. There is no interleaving of two transactions' read-modify-write on the same shared object. The "both read the old value" interleaving is an EVM/multithreaded-database mental model that does **not** apply.

**Consequences for findings:**
- A "lost update / TOCTOU race on a shared object counter" claim is **invalid** unless the read and the write happen in **different transactions** with an attacker action in between (that is staleness, not a race — frame it as staleness and prove the cross-transaction window).
- Owned objects (single-owner, address-owned) are even stronger: they use the fast path (no consensus) and only the owner can mutate them — concurrency races across owners are impossible by construction.
- A real Sui concurrency concern is **equivocation / object-version contention** (a sender submitting two txns spending the same owned-object version, causing one to be locked out until end of epoch) — that is a *liveness/grief* angle, not a state-corruption race. Frame it precisely.

### Before writing any "race condition" finding on Sui
1. Are the conflicting read and write in the **same** transaction? → No race (atomic). Look elsewhere.
2. Different transactions on a **shared** object? → Consensus orders them; analyze it as **stale-cache-across-transactions**, prove the attacker-controlled window, and check whether the cached value gates value movement.
3. Different transactions on **owned** objects? → Only the owner mutates; cross-user race impossible. Consider equivocation/liveness only.

> The committed `benchmarks/sui/shared-object-race` ground truth describes the WRONG (item-1/EVM) framing; it is annotated `disputed` for this reason. Do not learn the race pattern from it.

---

## #2 — Object ownership is enforced by the runtime, not by in-Move checks

A function parameter typed `&mut Pool` can only be supplied by a transaction that legitimately has access to that `Pool` (shared, or owned by the sender). You do **not** need an in-body `assert!(owner == sender)` for an owned object — the runtime rejects the transaction otherwise. Flagging "missing owner check" on an owned-object parameter is usually invalid. The real authorization surface is **capabilities** (a `&AdminCap` parameter) and **shared-object** functions (anyone can pass a shared object, so those DO need in-body auth/capability checks).

## #3 — `key`-only vs `key + store`, and the transfer surface

- `key` ability alone: the object can be an owned/shared object but **cannot** be freely `public_transfer`'d by arbitrary code — only the defining module's transfer functions move it.
- `key + store`: the object is transferable by anyone via `transfer::public_transfer`, can be wrapped, and can flow through `Kiosk`/marketplaces. Adding `store` to a capability or position object is a real privilege-escalation surface — check whether a `key+store` object grants authority it shouldn't be freely transferable with.

## #4 — Hot-potato (no-ability struct) forces a call to complete

A struct with **no abilities** (no `drop`, `store`, `key`, `copy`) cannot be stored, dropped, or ignored — it must be consumed by another function in the same transaction (the flash-loan / "must repay" pattern). When you see a returned no-ability struct, the obligation is **structurally enforced by the type system**; "user forgets to repay" is not a valid finding. The real questions: can the consuming function be satisfied with attacker-favorable arguments, and is the value checked at consumption?

## #5 — One-Time Witness (OTW) genuinely guarantees init-once

A type passed to `init` that satisfies the OTW rules (name == module name uppercased, only `drop`, no fields, produced solely by the runtime at publish) can be obtained **exactly once**, at publish. "Attacker forges the OTW to re-run init / mint a second `TreasuryCap`" is invalid if the witness is a true OTW. Verify the OTW shape before relying on this; a struct that merely *looks* like a witness but is constructable in user code is NOT protected.

## #6 — Move integer semantics: abort, not wrap

Move arithmetic **aborts** on overflow/underflow and on divide-by-zero (it does not wrap like unchecked Solidity, and there is no `unchecked` block). So:
- "u64 addition overflows and wraps" → invalid; it aborts (the bug, if any, is the **DoS/abort**, not a silent wrap).
- Division-by-zero → aborts. A `/ count` where `count` was just incremented from 0 to ≥1 in the same function before the divide is safe.
- The real numeric bugs are **truncation in integer division** (rounding direction / dust) and **abort-based griefing/DoS**, not silent wraparound.

---

## Invalid Finding Patterns (withdraw before verification)

| Pattern | Why invalid on Sui | Reframe as (if anything) |
|---------|--------------------|--------------------------|
| EVM-style lost-update race on a shared-object field | Consensus serializes shared-object txns | Cross-tx staleness (prove the window) |
| "Missing owner check" on an owned-object param | Runtime enforces ownership for owned objects | Capability/shared-object auth gaps only |
| "User forgets to repay" a hot-potato | No-ability type must be consumed in-tx | Mis-checked consumption arguments |
| "Forge the OTW to re-init" (true OTW) | OTW obtainable once at publish | Non-OTW witnesses constructable in user code |
| "u64 overflow wraps to 0" | Move aborts on overflow | Abort-based DoS / griefing |
| Division-by-zero after a guaranteed `+1` | Denominator ≥ 1 at the divide | Truncation/dust rounding |

## History of Lessons
- **2026-06 (v1.21.0) blind benchmark** — `sui-shared-object-race`: an agent correctly refused to report the seeded "race" (Sui serializes shared-object access) and instead found the real bug (deposited funds permanently locked — no withdraw path). The benchmark ground truth encodes the EVM-race misconception and is now annotated `disputed`. This quirks file was created from that run.
