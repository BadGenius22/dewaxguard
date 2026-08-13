# Go / L1 Node Client Quirks — Critical Reference

> **READ THIS BEFORE ANY GO-BASED L1 AUDIT.** This document captures Go semantics and node-client patterns that produce invalid findings or missed bugs when misunderstood. Tuned for Ethereum execution clients (Geth, Erigon), consensus clients (Lighthouse-Go variants, Prysm), Cosmos SDK chains, CometBFT (formerly Tendermint), and similar consensus-node codebases.

**Scope**: Go-based L1 nodes are **not** smart contracts and **not** EVM applications. The attack surface is: consensus state machine transitions, p2p network handling, mempool admission, RPC surface, validator/voter lifecycle, IBC/bridge message routing, fee/gas accounting, and node resource exhaustion. Standard EVM/Solana/Move vulnerability classes rarely port — the threat model is different. Many bugs come from Go-language semantics (slice aliasing, map iteration order, goroutine leaks) rather than business logic.

---

## 🚨 #1 — Map Iteration Order Non-Determinism (Consensus-Critical)

### The Misconception

> "I'm just iterating a map to compute some aggregate value — order doesn't matter, the result is the same."

### The Reality

Go's `map` deliberately randomizes iteration order on every range. Two nodes iterating the same map will see different orders. **If iteration order affects the result, consensus forks.**

Real failure modes:
- Iterating a map of validators to assign committee slots → different nodes assign different slots → different block proposals → fork
- Iterating a map of pending txs to build a block → different nodes pack different txs → divergent block hashes
- Iterating a map to compute a hash → hash is non-deterministic across nodes
- Accumulating signed-amount deltas in floating-point or order-dependent arithmetic order

### The Fix Pattern

```go
// WRONG — order-dependent across nodes
for k, v := range m {
    result = combine(result, v)
}

// RIGHT — sort keys first, deterministic across nodes
keys := make([]K, 0, len(m))
for k := range m {
    keys = append(keys, k)
}
sort.Slice(keys, func(i, j int) bool { return less(keys[i], keys[j]) })
for _, k := range keys {
    result = combine(result, m[k])
}
```

### Checklist

- [ ] Every `range` over a map — does the result depend on iteration order? If yes, sort keys first.
- [ ] Every state-change computation — is the order deterministic across all nodes running the same software version?
- [ ] Cross-version determinism — if validator A runs version X and validator B runs version Y, do they iterate in the same way?
- [ ] Test isolation lies — `go test` may produce stable order because of low map size; consensus nodes hit large maps under load.

### Known Failure Pattern

Cosmos SDK chains have shipped multiple consensus bugs traced to non-deterministic map iteration in keeper code. The pattern: a keeper iterates `k.Validators` to compute rewards or slashing; map iteration order differs across nodes; consensus forks at the block where the iteration result diverges.

---

## 🚨 #2 — Slice Aliasing (Silent Data Corruption)

### The Misconception

> "I'm slicing this byte array, so the slice is independent. Modifying it won't affect the original."

### The Reality

Go slices share underlying array memory. `s[1:5]` and `s` point to the same backing array. Modifying one CAN affect the other. The slice expression `s[a:b]` shares capacity unless capped: `s[a:b:b]`.

```go
data := []byte{1, 2, 3, 4, 5, 6, 7, 8}
header := data[:4]            // shares backing array with data
payload := data[4:]           // shares backing array with data
header = append(header, 9)    // !!! if cap(header) > len(header), this writes to data[4]
// payload[0] is now 9, not 5
```

Real failure modes:
- Decoding a network message: header slice gets reused for the next packet, but a prior call retained a reference; the prior call's data is silently corrupted
- Computing a Merkle root: appending to a slice over-writes a node's hash that was being computed in parallel
- p2p message buffer pool reuse: a goroutine retained a slice reference past return; pool reuses the buffer; goroutine sees corrupted data

### The Fix Patterns

```go
// FIX 1 — copy to break the aliasing
header2 := make([]byte, len(header))
copy(header2, header)

// FIX 2 — full slice expression caps capacity
header := data[:4:4]   // len=4, cap=4 — append always allocates new array

// FIX 3 — bytes.Clone (Go 1.20+)
header := bytes.Clone(data[:4])
```

### Checklist

- [ ] Every slice returned from a function — does the caller know whether it shares backing storage with the function's internal state?
- [ ] Every `append` to a function parameter slice — could this overwrite the caller's data past the slice end?
- [ ] Every concurrent goroutine handling network buffers — are slices passed by value or sharing memory?
- [ ] Cryptographic buffers — are intermediate state slices aliased with output slices? Signature corruption results.

---

## 🚨 #3 — `time.Now()` and Wall-Clock Reads in Consensus

### The Misconception

> "I'm using `time.Now()` to check if a proposal is too old — different nodes see slightly different times, but they're close enough."

### The Reality

`time.Now()` returns the host's wall-clock time. Two nodes never have exactly the same time. **If a consensus decision branches on `time.Now()`, the consensus forks.**

Failure modes:
- Block proposer's validity window check: proposer A sees `now < deadline`, proposer B sees `now > deadline` → A includes a tx, B excludes it → fork
- Slashing condition: validator's evidence "is recent enough" depends on `now` — different validators score the same evidence differently
- Mempool eviction: txs expire on local clock — different mempools, different orderings, different inclusions
- IBC/bridge timeout: timeout decided on wall-clock instead of block height

### The Fix Pattern

Use **block time** (consensus-decided) instead of wall-clock:

```go
// WRONG
if time.Now().After(deadline) { reject() }

// RIGHT
if header.Time.After(deadline) { reject() }
// or
if blockHeight >= deadlineBlock { reject() }
```

The host clock is used ONLY for: gossip rate-limiting, mempool TTL hint (not consensus), local logging.

### Checklist

- [ ] `time.Now()` calls in any consensus-relevant path — list them all (grep `time.Now`)
- [ ] Each call: does the result feed a consensus-relevant decision? If yes, replace with block-time or block-height
- [ ] Slashing / fraud-proof code: every comparison must use canonical time, not wall-clock
- [ ] Mempool tx ordering by submission time: across nodes, submission times differ — consider canonical alternative

---

## 🚨 #4 — Goroutine Leaks and Context Cancellation

### The Misconception

> "I'm starting a goroutine to handle this request. It'll exit when done. No leak."

### The Reality

Goroutines that block on a channel send/receive without a context-aware select leak indefinitely. Common patterns:

```go
// LEAK 1 — channel send blocks forever if receiver is gone
go func() {
    resultCh <- compute()   // if resultCh has no reader and the caller returned, this goroutine blocks forever
}()

// LEAK 2 — channel receive without context cancellation
go func() {
    select {
    case msg := <-incoming:
        process(msg)
    }   // if incoming is never closed AND no ctx.Done is selected, this leaks on shutdown
}()

// LEAK 3 — http client without timeout
resp, _ := http.Get(url)   // if peer never responds, this goroutine and its file descriptor leak
```

### Why It Matters at L1

- A node handling thousands of inbound p2p messages per second leaks one goroutine per malformed peer → memory exhaustion DoS
- A long-running validator process accumulates goroutines from every dropped/timed-out RPC client → progressive memory leak → OOM crash
- An attacker can SPECIFICALLY craft requests that trigger the leak path → cheap DoS

### The Fix Pattern

```go
// always select on ctx.Done()
go func(ctx context.Context) {
    select {
    case <-ctx.Done():
        return
    case resultCh <- compute():
    }
}(ctx)

// always use a context-aware HTTP client
ctx, cancel := context.WithTimeout(parent, 30*time.Second)
defer cancel()
req, _ := http.NewRequestWithContext(ctx, "GET", url, nil)
resp, err := client.Do(req)
```

### Checklist

- [ ] Every `go func()` — what makes it exit? (ctx cancel? channel close? both?)
- [ ] Every channel send — could the receiver be gone? (Use select with `ctx.Done()`.)
- [ ] Every channel receive — could the sender be gone? (Use select; or ensure sender always closes.)
- [ ] Every `http.Get`/`http.Post` — does it have a timeout? `http.DefaultClient` has none.
- [ ] Every `time.Tick` — `time.Tick` leaks if you don't capture the ticker; use `time.NewTicker` + `defer ticker.Stop()`.

---

## 🚨 #5 — `defer` Ordering and Error Path Cleanup

### The Misconception

> "I deferred the cleanup; it runs even on error."

### The Reality

`defer` runs in LIFO order. Defers are evaluated when registered. Subtle bugs:

```go
// BUG 1 — defer of closure captures variable by reference
for i, file := range files {
    f, err := os.Open(file)
    if err != nil { return err }
    defer f.Close()   // !!! if the loop has 1000 files, all 1000 stay open until function returns
}
// FIX: extract to a helper that takes the file as parameter, or close explicitly

// BUG 2 — deferred error is discarded
defer f.Close()   // if Close() returns an error (flush failed, disk full), it's silently dropped
// FIX:
defer func() {
    if cerr := f.Close(); cerr != nil && err == nil {
        err = cerr
    }
}()

// BUG 3 — defer evaluated arg vs deferred call
defer fmt.Println(time.Now())   // !!! time.Now() captured NOW, not at defer time
defer func() { fmt.Println(time.Now()) }()  // correct — Now() runs at defer time
```

### Checklist

- [ ] Every `defer f.Close()` — is the closure capturing the same variable that's being reassigned? If yes, wrap in helper.
- [ ] Every `defer` of a function that can return an error — is the error checked or silently dropped?
- [ ] Every `defer` inside a loop — does it accumulate one defer per iteration? Refactor to per-iteration cleanup.

---

## 🚨 #6 — Integer Overflow Is Silent in Go

### The Misconception

> "Solidity 0.8+ panics on overflow. Rust panics in debug. Go must be similar."

### The Reality

Go silently wraps on integer overflow with NO panic, NO check, NO error. Signed and unsigned both wrap. This is by language design and unchanged across versions.

```go
var x uint64 = math.MaxUint64
x += 1   // x is now 0, no panic, no error

var y int64 = math.MinInt64
y -= 1   // y is now math.MaxInt64, no panic
```

### Why It Matters at L1

- Fee/gas accumulator: enough txs in one block can wrap `totalGasUsed` — node accepts the block as valid; consensus forks if any other node hits an overflow guard
- Stake amount: validator delegation count or stake amount wraps → permission becomes inverted (e.g., "stake > threshold" passes when stake is actually MAX-large)
- Block height arithmetic: `blockNumber + lookback` wraps → "is this evidence within lookback?" returns true for any block
- Reward calculation: token reward overflow → mint absurd amounts

### The Fix Patterns

```go
// Pattern 1 — math/big for amounts
sum := new(big.Int).Add(a, b)

// Pattern 2 — explicit overflow check
if math.MaxUint64-a < b {
    return errOverflow
}
sum := a + b

// Pattern 3 — saturating helpers
func saturatingAdd(a, b uint64) uint64 {
    if math.MaxUint64-a < b {
        return math.MaxUint64
    }
    return a + b
}
```

### Checklist

- [ ] Every arithmetic op on user-influenced values — does overflow change a decision? If yes, use math/big or explicit check.
- [ ] Every counter that can grow without bound (tx count, block height, stake) — what happens at the wrap point?
- [ ] Every `int` / `uint` cast — is the wider value bounded to the narrower range? `int64 → int32` silently truncates.

---

## 🚨 #7 — `nil` Interface vs Typed `nil` (Equality Trap)

### The Misconception

> "I returned a typed `nil`; checking the interface == nil should be true."

### The Reality

A typed nil wrapped in an interface is **not** `nil` when compared to the untyped `nil`:

```go
var err *MyError = nil      // typed nil
var ierr error = err         // interface holding typed nil
if ierr == nil {             // FALSE — ierr has type *MyError, value nil
    // unreachable
}
```

### Why It Matters

- RPC error handlers: `return rpcCallSomething()` where the function signature is `error` but the internal type is `*MyError`; caller's `if err != nil` always sees the error path even on success
- Validator status checks: `Validator()` returns `*Validator` (nil if not found), caller wraps it in `interface{}` for logging; `nil` check passes false; nil deref panics

### Fix Pattern

```go
// WRONG
func GetValidator() error {
    var err *MyError
    if somethingWent { err = &MyError{} }
    return err   // returns typed nil even when intended as nil
}

// RIGHT
func GetValidator() error {
    if somethingWent {
        return &MyError{}
    }
    return nil   // untyped nil
}
```

### Checklist

- [ ] Every function returning an interface — does it return a typed nil that should be the untyped `nil`?
- [ ] Every error-wrapping helper — does it preserve nil-ness across the wrap?

---

## 🚨 #8 — Concurrent Map Access Panics

### The Misconception

> "Reads from a map are safe even if another goroutine writes."

### The Reality

Concurrent reads + writes on a map crash the Go runtime with `fatal error: concurrent map read and map write`. There's no panic recovery — the whole process dies. This is the SINGLE WORST node-client crash pattern.

### Why It Matters at L1

- RPC handler reads validator map while consensus engine updates it → node crash
- Peer score map: gossip handler writes, scorer reads → node crash
- Mempool: admission goroutine writes, block builder reads → node crash mid-block-build

### The Fix Patterns

```go
// Pattern 1 — sync.RWMutex
type SafeMap struct {
    mu sync.RWMutex
    m  map[string]int
}
func (s *SafeMap) Get(k string) int {
    s.mu.RLock(); defer s.mu.RUnlock()
    return s.m[k]
}

// Pattern 2 — sync.Map (better for read-heavy, sparse-write workloads)
var m sync.Map

// Pattern 3 — channels for serialization (Go idiom)
```

### Detector

`go build -race` instruments memory access; `go test -race` catches concurrent map access in test runs. Tests that pass without `-race` may still crash production. **Every L1 node should run `go test -race` in CI.**

### Checklist

- [ ] Every `map[X]Y` field on a long-lived struct — is access serialized? (mutex, sync.Map, or single goroutine owns it)
- [ ] Every `sync.Map` use — are values shared mutable pointers that themselves need protection?
- [ ] Race detector run — `go test -race ./...` over the changed code is mandatory before merge.

---

## 🚨 #9 — JSON/RLP/Borsh Unmarshaling Type Confusion

### The Misconception

> "The struct tags handle it. The decoded value will match what I expected."

### The Reality

Go's `encoding/json` is permissive by default. Loose type contracts allow attacker-controlled inputs to deserialize to surprising types:

- A JSON object's number `"1234567890123456789"` deserializes into `float64` (default for `interface{}`) → loses precision past `2^53` → 1234567890123456800 → consensus divergence
- A JSON `string` field declared as `uint64` in Go is rejected; but a JSON `number` is accepted — attacker can submit either, and the validator who hasn't pinned the field type may accept one but not the other → diverging mempool admission
- Extra/unknown JSON fields are silently ignored by default → attacker uses a known-name field but sets a critical flag via a typo (`"validatos"` vs `"validators"`); validator on the WRONG side processes both, the other rejects both. Use `decoder.DisallowUnknownFields()` for strict input.
- RLP / Borsh / Protobuf canonical encoding: a struct with optional/zero-value fields can encode to multiple equivalent byte representations — non-canonical encoding allows transaction-hash collisions or signature replays.

### Checklist

- [ ] Every external input deserialization (RPC, p2p, IBC, file load) — is the schema strict?
- [ ] Every numeric field — is the source format constrained? (Floating-point vs integer JSON; varint vs fixed-width Borsh.)
- [ ] Every canonical-encoding-dependent identifier (tx hash, block hash, signature payload) — is the encoding canonical and round-trip-stable across all node implementations?
- [ ] Cross-implementation interop — do all client implementations (Geth, Reth; Lighthouse, Prysm; etc.) encode the same struct to the same bytes?

---

## 🚨 #10 — IBC / Bridge / Cross-Chain Message Handling

### The Misconception

> "Cross-chain messages are validated by the IBC light client. If they pass that check, they're trusted."

### The Reality

IBC and bridge handlers have a long history of bugs distinct from light-client cryptography:

- **Timeout race**: same packet acked AND timed-out → state inconsistency
- **Packet replay across channels**: same packet processed on two channels (channel ID confusion)
- **Acknowledgment confusion**: ACK from chain B treated as ACK from chain C
- **Memo / payload injection**: a memo field bypasses validation when re-routed through a third chain
- **Token authority confusion**: deposit/withdraw uses the wrong escrow account
- **Sequence rollback**: receiving a packet older than expected sequence number; whether this is reject or accept differs across implementations
- **Channel closure desync**: chain A thinks channel is closed; chain B keeps sending; chain B's chain halts on next receive

### Checklist for Cosmos SDK chains

- [ ] Every `OnRecvPacket` / `OnAcknowledgementPacket` / `OnTimeoutPacket` — does it correctly route by channel-id AND port-id?
- [ ] Token escrow accounts — is the mapping from (port, channel) → escrow account collision-free across upgrades?
- [ ] Packet sequence handling — what happens on out-of-order receive?
- [ ] Memo/payload field — is it ever interpreted by the receiver in a way the sender didn't intend?

### Known Patterns

- The "Dragonberry" class of Cosmos IBC bugs (2022-2023) traced to packet ordering and ACK confusion
- The Nomad bridge bug (Aug 2022) — trusted-root replay allowed by missing zero check; not Go but the structural pattern (trusted-root validation) recurs in IBC-style code

---

## 🚨 #11 — p2p / Networking Surface

### Common Attack Vectors

| Attack | Mechanism | Mitigation |
|--------|-----------|------------|
| **Eclipse** | Attacker controls all of victim's peer slots | diverse peer selection, peer scoring, fast peer churn |
| **Sybil** | Attacker creates many cheap peer identities | proof-of-work or proof-of-stake peer admission |
| **Bandwidth amplification** | Tiny request → huge response (e.g., gossip topic subscription) | response size budget, rate-limited subscriptions |
| **Slow loris** | Many half-open TCP connections | per-IP connection limit, idle timeout |
| **Resource exhaustion** | Filling mempool with min-fee txs to evict competitor txs | priority fee floor, sender quotas |
| **Block withholding** | Withhold a block to fork the chain | gossip protocol propagation guarantee |
| **Peer scoring poisoning** | Attacker abuses the scoring rules to ban honest peers | sanity checks on score, allowlist friends |

### Go-Specific Surface

- libp2p stream handling: every incoming stream spawns a goroutine — goroutine leak on slow peers; one-second handler deadline
- gossipsub message validation: validating large messages serially blocks the gossipsub goroutine pool
- RPC handlers without timeouts: a misbehaving client can pin a worker indefinitely
- `net/http` server defaults: no read/write timeout → slow loris vector

### Checklist

- [ ] Every inbound stream handler — has a deadline / context timeout?
- [ ] Every message validation — bounded in CPU and memory?
- [ ] Every RPC method — has a per-method timeout?
- [ ] Every peer scoring rule — can a peer drive its own score (positive or negative)?
- [ ] Peer admission — is there a cost to creating a new peer (POW, deposit, IP rate-limit)?

---

## 🚨 #12 — Consensus State Machine Determinism

### The Big Picture

Consensus engines (Tendermint/CometBFT, HotStuff, IBFT, GASPER, etc.) all share one property: **every honest validator processing the same sequence of inputs (messages, txs, blocks) must reach the same state**. Any non-determinism is a consensus bug.

### Sources of Non-Determinism (Beyond Map Iteration #1 and Wall-Clock #3)

1. **Floating-point arithmetic** — same float operation on x86 vs ARM yields different results
2. **`runtime.GC()` timing** — if logic depends on GC having run (it shouldn't, but...)
3. **Goroutine scheduling order** — if state mutation order is goroutine-scheduling-dependent
4. **Network message arrival order** — if state mutation depends on arrival order rather than canonical ordering
5. **`json.Marshal` of maps** (same as #1; encoding/json sorts keys, but other encoders may not)
6. **External dependencies returning different results** — DNS, oracle reads, time servers
7. **Compiler version differences** — same Go source can produce different machine code; if the produced code differs in observable behavior (e.g., math edge cases), nodes can diverge

### Checklist

- [ ] No floating-point in consensus-relevant code (use `math/big` or fixed-point integers)
- [ ] No goroutine concurrency in consensus state machine — single-threaded, message-pump style
- [ ] No reliance on map iteration order
- [ ] No reliance on `time.Now()` or wall clock
- [ ] No reliance on external network calls
- [ ] Build reproducibility — same source → same binary across all nodes' build environments (gomod hashes verified)

### Detection Patterns

- Run validator pairs with `--debug-consensus-trace` and diff logs
- Replay block import on two independently-built binaries
- Cross-implementation interop tests (Geth ↔ Reth ↔ Erigon)

---

## L1 Audit Baseline Known-Issue Catalog (for Deduplication)

Before claiming a novel finding, grep against these public reports / CVE databases:

| Source | URL |
|--------|-----|
| Ethereum CL security advisories | https://github.com/ethereum/consensus-specs/security |
| Geth security advisories | https://github.com/ethereum/go-ethereum/security/advisories |
| Reth security advisories | https://github.com/paradigmxyz/reth/security/advisories |
| Cosmos SDK security advisories | https://github.com/cosmos/cosmos-sdk/security/advisories |
| CometBFT security advisories | https://github.com/cometbft/cometbft/security/advisories |
| Bitcoin Core CVE list | https://en.bitcoin.it/wiki/Common_Vulnerabilities_and_Exposures |
| GHSA Go advisories | https://pkg.go.dev/vuln/list |

Your finding has been seen before if it matches the title or root cause of an advisory in the last 24 months — flag as DUPLICATE OF <CVE-ID or GHSA-ID> in the finding's `duplicate_of_v12` field equivalent.

---

## Quick-grep Patterns (for recon Phase 1.0 + L1 Bake)

```bash
# Map iteration that might affect consensus
grep -rn 'range\s\+\w\+\s*{' --include='*.go' | grep -iE '(consensus|state|validator|reward|slash)'

# time.Now() in consensus-relevant paths
grep -rn 'time\.Now\(\)' --include='*.go' | grep -ivE '(test|log|metric|prometheus)'

# Concurrent map without sync wrap
grep -rn 'map\[' --include='*.go' | grep -v '^.*test'

# Goroutines without context
grep -rn 'go func' --include='*.go' | head -50

# Integer arithmetic on untrusted input
grep -rn 'func.*amount.*uint' --include='*.go'

# JSON without DisallowUnknownFields
grep -rn 'NewDecoder' --include='*.go' | grep -v 'DisallowUnknownFields'

# http.Get / http.Post without context (no timeout)
grep -rn 'http\.\(Get\|Post\)' --include='*.go'
```

These are STARTING POINTS, not a security checklist. Each match is a candidate to be investigated, not a confirmed bug.
