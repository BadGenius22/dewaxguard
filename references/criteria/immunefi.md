# Immunefi Bug Bounty — Judging Criteria

## Severity Definitions

| Level | Impact |
|-------|--------|
| **Critical** | Direct theft of user funds (at-rest or in-motion); Permanent freezing of funds/NFTs; Unauthorized minting; Protocol insolvency; Governance hijacking |
| **High** | Theft of unclaimed yield; Permanent freezing of yield; Temporary freezing of funds; Oracle manipulation |
| **Medium** | Griefing; Block stuffing; Gas theft; DoS |
| **Low** | Contract fails to deliver promised returns |

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
