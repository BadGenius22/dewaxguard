# Platform Quirks — DewaxGuard

This directory holds platform-specific semantic quirks that every audit in the corresponding language MUST read before analysis.

## Purpose

Every smart contract platform has idiosyncrasies that, if misunderstood, produce **invalid findings** — findings that look technically sound in theory but cannot occur in production. These quirks are hard to discover from surface-level documentation and often require either (a) deep protocol knowledge, (b) reading the target project's own tests to see what they avoid, or (c) painful audits where invalid findings got rejected.

This directory captures those quirks in a central, durable location so future audits don't repeat the same mistakes.

## Structure

```
platform-quirks/
├── README.md            — this file
├── stellar.md           — Stellar / Soroban quirks
├── ethereum.md          — Ethereum / EVM quirks (stub)
├── solana.md            — Solana / Anchor quirks (stub)
├── aptos.md             — Aptos Move quirks (stub)
├── sui.md               — Sui Move quirks (stub)
└── cross-platform.md    — common misconceptions that bite multiple platforms
```

## Usage

1. **During recon**: The recon prompt for each language MUST read the corresponding quirks file and pass it as context to all spawned agents.
2. **During analysis**: Every depth, scanner, and verification agent MUST have the quirks file in its context window.
3. **Pre-verification gate**: Before spawning verifiers, the orchestrator MUST cross-check every finding against the "Invalid Finding Patterns" section of the quirks file. Invalid findings are withdrawn before wasting verification cycles.
4. **Post-audit**: If a finding was rejected due to a platform quirk, **add the lesson to the quirks file**. This document only improves by accumulating pain.

## History of Lessons

- **2026-04 LayerZero Soroban audit**: Wrote 1H + 2M findings assuming Stellar persistent storage deletes on TTL expiry. Actually, persistent/instance storage **archives** with preserved values; only temporary storage deletes. See `stellar.md` entry #1.
