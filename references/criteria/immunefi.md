# Immunefi Bug Bounty — Judging Criteria

## Severity Definitions

| Level | Impact |
|-------|--------|
| **Critical** | Direct theft of user funds (at-rest or in-motion); Permanent freezing of funds/NFTs; Unauthorized minting; Protocol insolvency; Governance hijacking |
| **High** | Theft of unclaimed yield; Permanent freezing of yield; Temporary freezing of funds; Oracle manipulation |
| **Medium** | Griefing; Block stuffing; Gas theft; DoS |
| **Low** | Contract fails to deliver promised returns, **but doesn't lose value** |

**Classification discipline (v2.3 is impact-based — map to the table above, NOT a generic Impact×Likelihood matrix):**
- **"No value lost / no user demonstrably harmed standalone" → Low** ("fails to deliver promised returns, doesn't lose value"), even when the invariant break feels severe. Protocol-breakage / safety-control-defeat / internal-accounting or event-log corruption **without fund movement = Low**, not Medium.
- **Medium "Griefing" requires DEMONSTRATED damage to users/protocol** — a weakened safety margin that only harms *in a chain* (needs a second bug/condition) is not standalone damage.
- **Chain-enablers inherit the STANDALONE proven impact** for classification (usually Low) until the full chain is PoC'd. A `[FORK-PASS]` that only proves "function is callable / state mutated" but `[FORK-FAIL]`s on theft/freeze/profit → Low.
- (Ostium C1: permissionless missing-`onlyCallbacks` defeats a circuit breaker + corrupts accounting, self-costing / no value lost → **Low**, not the matrix's Medium.)

## Key Rules

- **Program Primacy**: Each program defines its own scope and severity. Program page overrides defaults.
- **PoC MANDATORY** for ALL severities. No PoC = not considered.
- **First reporter priority**: First valid submission rewarded.
- **KYC may be required** for payout.

## Automatic Invalidators
- Requires leaked keys/credentials
- Requires admin/owner access without code bug
- External stablecoin depeg (not caused by code)
- Best practice recommendations without impact
- Feature requests
- Gas optimizations
- Centralization risks without exploit path
- Theoretical without proof (AI-37)

## PoC Requirements

Must:
- Compile and execute successfully
- Demonstrate concrete impact (not just function callability)
- Use realistic conditions (no impossible states)

## Payout Model

Critical: up to program's max (often $50K-$500K+)
High: varies by program
Medium: varies by program
Low: varies by program

Each program can override defaults. Always check the specific program page.
