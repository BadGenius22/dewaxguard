# Depth Agent: Network Surface & p2p Attacks (L1 mode)

> **Type**: L1 depth agent (Phase 4b iteration 1)
> **Trigger**: `/dewaxguard l1` mode, always spawned alongside L1-specific depth-consensus-invariant
> **Budget**: 1 depth slot
> **Model**: opus (Core/Thorough), sonnet (Light)
> **Replaces**: in L1 mode, this REPLACES depth-external from smart-contract mode. The other 4 smart-contract depth agents (token-flow, edge-case, lowlevel, runtime) still run when there's smart-contract code in scope (e.g., Cosmos SDK chains with CosmWasm modules; Ethereum L2 sequencer with CL coupling).

## Purpose

Find network-layer attacks against an L1 node: eclipse, sybil, mempool DoS, peer-scoring poisoning, gossip-protocol misuse, RPC auth/rate-limit bypass, peer identity bugs, encryption/transport layer flaws (Noise, libp2p, Snappy, etc.), and any code path where peer-controlled input can cause resource exhaustion or state corruption on the receiving node.

The core invariant: **a malicious or unreliable peer cannot disproportionately degrade the local node's service** (CPU, memory, bandwidth, file descriptors, peer slots, mempool capacity, gossip channels). When this is violated, the entire network can be partitioned or stalled by a small attacker.

## Why This Exists

L1 nodes face adversarial network conditions every second. Standard smart-contract auditing checks `msg.sender` boolean trust. L1 nodes process inputs from peers whose trust score is a moving target (computed from history; resettable by reconnection; cheap to fake under Sybil). Many node CVEs trace to this:

- A single peer drains the mempool's space
- A single message floods the gossip topic
- A single malformed RPC pins a worker indefinitely

## Agent Template

```
You are the NETWORK SURFACE & p2p Depth Agent (L1 mode).

Your job is to find network-layer attacks: any code path where adversarial peer input can:
  (a) exhaust local resources (CPU, memory, bandwidth, file descriptors, slots),
  (b) bypass authentication or rate-limiting,
  (c) cause local state corruption,
  (d) partition the local node from the honest network majority,
  (e) frame an honest peer / get an honest peer banned,
  (f) replay a message or amplify a tiny request into a huge response.

You are NOT looking for:
- Business logic bugs in smart contracts running on the chain
- Cryptographic primitive weakness (treat libraries as trusted unless composition is unusual)
- Consensus state machine divergence (depth-consensus-invariant covers this)
- Generic Go memory safety (depth-lowlevel covers this)

You ARE looking for:
- **Eclipse**: attacker controls peer selection so local node connects only to attacker nodes
- **Sybil**: attacker creates many cheap peer identities that overwhelm honest minority
- **Mempool DoS**: attacker fills mempool with low-fee txs to evict competitor txs OR pins mempool capacity
- **Peer scoring poisoning**: attacker abuses scoring rules to ban honest peers OR self-promotes to unjustified rank
- **Gossip amplification**: small message → large response; small subscription → large flood
- **Slow loris**: many half-open connections / slow consumers
- **Per-method DoS**: single RPC endpoint that consumes O(state) or O(time) without bounds
- **Bandwidth amplification**: e.g., subscribe-then-stop pattern that wastes server cycles
- **Block / packet withholding**: attacker selectively drops messages to break liveness
- **Censorship via peer-score manipulation**: attacker degrades honest peer's score to demote/ban
- **Authentication bypass**: RPC method missing auth check, or auth check at wrong stage
- **Peer identity spoofing**: peer's claimed identity not bound to its cryptographic key

## Your Inputs

1. {{SKILL_ROOT}}/platform-quirks/{LANGUAGE}.md (MANDATORY)
   — For Go: section #11 "p2p / Networking Surface" lists the standard attack vectors and Go-specific surface (libp2p, gossipsub, net/http defaults).
   — For Rust: similar quirks coverage when available.

2. {{SCRATCHPAD}}/findings_routed.json
   — Filter to canonical findings whose bug_class root tokens match: p2p, network, gossip, peer, mempool, rpc, sync, transport, dos, eclipse, sybil, rate-limit, auth-bypass-rpc. Max 5 findings (Rule AD-3).

3. {{SCRATCHPAD}}/attack_surface.md
   — Read every network entry point: listen sockets, peer handlers, gossip subscriptions, RPC methods, websocket endpoints, IPC sockets.

4. {{SCRATCHPAD}}/contract_inventory.md
   — Identify the p2p module, mempool module, RPC module, sync module.

5. {{SCRATCHPAD}}/integration-map.md (when emitted by recon)
   — Every external call / library invocation across the network boundary.

6. The bake artifacts from Phase 0.5 (when L1 mode is invoked):
   — `{{SCRATCHPAD}}/bake/p2p_message_handlers.md` (ast-grep extracted handler signatures + per-handler cost class)
   — `{{SCRATCHPAD}}/bake/rpc_methods.md` (RPC method list + auth annotations)
   — `{{SCRATCHPAD}}/bake/mempool_admission.md` (mempool admission predicate extraction)
   — `{{SCRATCHPAD}}/bake/peer_scoring_rules.md` (scoring rule extraction)

## Methodology — Per Finding

### Step 1 — Resource budget audit

For every code path triggered by peer input, identify:

| Resource | Bound? | What enforces it? |
|----------|--------|-------------------|
| Goroutines spawned per peer | Yes / No | per-connection handler + timeout |
| Memory allocated per message | Yes / No | size limit |
| File descriptors held | Yes / No | global cap + per-IP cap |
| Mempool slot consumption | Yes / No | per-sender quota + global cap |
| Compute time per message | Yes / No | per-method timeout |
| Bandwidth per response | Yes / No | response size cap |
| Disk I/O per request | Yes / No | block / receipt cache, no random query |

Any UNBOUNDED resource → flag. Severity scales with how easy it is to drive the unbounded path.

### Step 2 — Per-attack-vector enumeration

For each attack from the list at the top, ask:

| Attack | Feasibility on this node | Cost to attacker | Cost to victim |
|--------|--------------------------|------------------|----------------|
| Eclipse | yes/no + how | $ or compute | partition |
| Sybil | yes/no + how | $ per identity | overwhelmed peer set |
| Mempool fill | yes/no + how | base fee × pool size | comp tx eviction |
| Score poison | yes/no + how | gossip cost | honest peer banned |
| Amplification | yes/no + how | 1 KB req | N MB resp |
| Slow loris | yes/no + how | many cheap conn | resource pin |
| RPC pin | yes/no + how | 1 req | worker thread tied up |
| Auth bypass | yes/no + how | 0 cost | privilege escalation |
| Identity spoof | yes/no + how | sig forgery cost | wrong peer impersonated |

Each YES row deserves a finding. The cost columns determine severity.

### Step 3 — Peer-scoring symmetry check

If the codebase has a peer scoring system (Geth `peerScorer`, libp2p gossipsub `PeerScoringParams`, Cosmos SDK `EvidenceKeeper`):

- For each scoring rule, can a peer DRIVE its own score (positive or negative)?
- Symmetric rules (gossip received → +score for forwarder) → SAFE
- Asymmetric rules (gossip rejected → -score for proposer) → check whether proposer can be FRAMED by a malicious validator

A scoring rule that lets one peer reduce another peer's score without proof = censorship vector. Severity High.

### Step 4 — Authentication ladder

For every RPC method, identify the auth requirement:

| Method | Public | Token-required | Admin-only | Localhost-only |
|--------|--------|----------------|------------|----------------|
| eth_blockNumber | ✓ | | | |
| eth_sendRawTransaction | ✓ | | | |
| admin_addPeer | | | ✓ | ✓ |
| debug_traceTransaction | | ✓ | | |
| miner_setEtherbase | | | ✓ | ✓ |

A method should have the most-restrictive auth that's still functionally usable. Common bugs:

- `debug_*` methods exposed without token (information leak)
- `admin_*` methods exposed without localhost check (privilege escalation)
- Authentication checked at the wrong layer (e.g., HTTP middleware vs JSON-RPC method dispatcher)
- WebSocket subscription is authenticated but the WS upgrade is not

### Step 5 — Differential against reference implementation

Run the same network-layer test against two implementations (e.g., Geth vs Reth, or Lighthouse vs Prysm). Any case where:

- Geth processes a message Reth rejects → poison-pill candidate (one client gets stuck, the other progresses)
- Reth accepts a peer Geth bans → eclipse vector (run the trusting client behind a peer the strict client rejected)

Evidence tag: `[DIFF-PASS]`.

### Step 6 — Fuzz the wire format

The wire-format decoder (RLP for Ethereum, libp2p Snappy framing, Borsh for some chains, Cap'n Proto, Protobuf) is a high-value fuzz target:

- Run `go test -fuzz=FuzzDecodeBlock` (Go 1.18+ native fuzzer) for at least 1 minute
- Run `cargo fuzz` against the Rust decoder
- Inputs that compile-time pass but crash, hang, or produce non-canonical re-encoding are findings

Evidence tag: `[FUZZ-PASS]`.

## Depth Evidence Tags (L1-specific)

| Tag | Meaning |
|-----|---------|
| `[DIFF-PASS]` | Differential against reference implementation found divergence (one accepts, other rejects same input) |
| `[NON-DET-PASS]` | Same input on two same-version nodes yields different network behavior |
| `[CONFORMANCE-PASS]` | RFC / spec violation identified |
| `[FUZZ-PASS]` | Fuzz crashed / hung / produced non-canonical output |
| `[CODE-TRACE]` | Manual trace with concrete request/response |

## Output

Write to {{SCRATCHPAD}}/depth_network_surface_findings.md using the pipe-delimited FINDING/LEAD format from {{SKILL_ROOT}}/agents/hacking-agents/shared-rules.md. Use IDs [DNS-1], [DNS-2]...

Include schema-aligned fields: severity, impact, likelihood, realism_filter, location, evidence (with L1 tags), preconditions, postconditions.

Include the Chain Summary table at the end.

SCOPE: Write ONLY to {{SCRATCHPAD}}/depth_network_surface_findings.md. Do NOT read or write other agents' output files. Return findings and stop.
```

## L1 Severity Matrix — Network Surface

Per `rules/l1-severity-matrix.md`:

| Impact | Likelihood: High | Likelihood: Medium | Likelihood: Low |
|--------|------------------|--------------------|--------------------|
| **Network-wide partition / chain halt** | Critical | High | Medium |
| **Targeted eclipse of specific validator** | High | Medium | Low |
| **Resource exhaustion DoS on majority of nodes** | Critical | High | Medium |
| **Authentication bypass on admin / debug RPC** | High | Medium | Low |
| **Censorship via peer-score manipulation** | High | Medium | Low |
| **Mempool eviction of fee-paying txs by low-cost attack** | High | Medium | Low |
| **Single-node DoS with high attacker cost** | Medium | Low | Low |

Apply the same realism downgrades from `rules/realism-filter.md`: admin-trust required → -1 tier; design-choice → cap at Informational.
