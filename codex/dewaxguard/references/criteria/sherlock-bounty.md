# Sherlock Bug Bounty — Judging Criteria

## Severity Definitions

| Level | Impact |
|-------|--------|
| **Critical** | Direct theft of user funds at rest or in motion; Permanent freezing of funds; Protocol insolvency |
| **High** | Theft of unclaimed yield; Permanent freezing of unclaimed yield; Temporary freezing of funds |
| **Medium** | Griefing; DoS; Gas exhaustion; Smart contract unable to operate |
| **Low** | Contract fails to deliver promised returns without loss |

## Key Rules

- **Timestamp priority**: First valid submission wins. Duplicates NOT rewarded.
- **Bug Bounty Page is source of truth** (not README)
- **PoC MANDATORY** for all severities
- Previous audit findings are out of scope

## Automatic Invalidators
Same as competitive Sherlock (AI-1 through AI-37) plus:
- Admin trust assumptions apply (admin actions that break code = design choice)
- Economic infeasibility = invalid
