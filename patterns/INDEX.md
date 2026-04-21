# Real-Finding Pattern Library

> **Validated attack patterns from completed audits.** Each entry is a real submitted finding — agents read these as concrete examples of "what a complete, submittable finding looks like" for a given attack template.

## Directory layout

```
patterns/
├── xrpl-2026-04/          # XRPL Sherlock April 2026 audit
│   ├── esc1-clawback-shield.md
│   ├── esc2-dust-destroy.md
│   ├── esc3-vault-share.md
│   └── conf1-flag-clear-brick.md
└── (future audits added here as they complete)
```

## How to use

When an agent hits an attack-template trigger (e.g. M-08 holder-plants-trap), consult the relevant pattern entries to see:
- How the attack was concretely structured in a real codebase
- What the PoC looked like
- What the feature-pool classification argument was
- What the dedup verdict was
- What severity was achieved

## Index by attack template

| Template | Pattern |
|----------|---------|
| [M-08](../methodology/M08-holder-plants-trap.md) holder-plants-trap | `xrpl-2026-04/esc1-clawback-shield.md` |
| [M-08](../methodology/M08-holder-plants-trap.md) holder-plants-trap | `xrpl-2026-04/esc2-dust-destroy.md` |
| [M-08](../methodology/M08-holder-plants-trap.md) holder-plants-trap | `xrpl-2026-04/esc3-vault-share.md` |
| [M-08](../methodology/M08-holder-plants-trap.md) + [M-09](../methodology/M09-sync-gap-detection.md) SYNC_GAP | `xrpl-2026-04/conf1-flag-clear-brick.md` |

## Contribution guide

After each audit, add a per-audit directory with one file per submitted finding. Each file should include:
- Feature / root cause summary
- Attack template (which M-xx)
- Cross-language mapping (what's generalizable)
- PoC pattern (not full source — just the shape)
- Severity achieved
- Dedup verdict
