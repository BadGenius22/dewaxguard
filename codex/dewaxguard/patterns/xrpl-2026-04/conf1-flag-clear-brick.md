# CONF-1: CanConfidentialAmount CLEAR Bricks MPTokens

**Audit**: XRPL Sherlock, April 2026 | **Severity**: Medium | **Feature Pool**: Confidential Transfers for MPT (XLS-0096)

## Attack templates

[M-08](../../methodology/M08-holder-plants-trap.md) holder-plants-trap + [M-09](../../methodology/M09-sync-gap-detection.md) SYNC_GAP detection — combined.

## One-line

`ConfidentialMPTConvertBack` zeroes encrypted balance ciphertexts but leaves their SField slots present. Issuer legitimately clears `CanConfidentialAmount`; any holder who previously did Convert→ConvertBack has MPToken permanently bricked by `ValidConfidentialMPToken` invariant.

## The triad + SYNC_GAP

| Criterion | Instance |
|-----------|----------|
| (1) Holder action | `Convert → MergeInbox → ConvertBack` (full round trip). Cost: 3 tx fees + standard confidential-proof generation. |
| (2) Admin op | `MPTokenIssuanceSet` with `tmfMPTClearCanConfidentialAmount` (legitimate capability toggle) |
| (3) Failure mode | Subsequent Payment / Clawback / etc. to the holder fails `tecINVARIANT_FAILED` — MPToken bricked |

## SYNC_GAP specifics

**Aggregate counter**: `sfConfidentialOutstandingAmount` on issuance — returns to 0 after ConvertBack.

**Per-entity residual**: three encrypted SFields on holder MPToken:
- `sfConfidentialBalanceSpending` — zeroed but PRESENT (no `makeFieldAbsent`)
- `sfConfidentialBalanceInbox` — not touched on ConvertBack
- `sfIssuerEncryptedBalance` — zeroed but PRESENT

**Precondition** (`MPTokenIssuanceSet.cpp:230-240`): checks aggregate — passes since COA=0.

**Downstream invariant** (`MPTInvariant.cpp:549-558`, `ValidConfidentialMPToken::finalize`): reads per-entity — fails because encrypted fields exist but `lsfMPTCanConfidentialAmount` is now cleared.

## Root cause

`ConfidentialMPTConvertBack.cpp:210-228` never calls `makeFieldAbsent` on the encrypted fields. Combined with the preclaim checking only the aggregate, this is a textbook SYNC_GAP.

## Cross-language generalization

SYNC_GAP + holder-plants-trap combined pattern applies wherever:
- A feature toggle has aggregate-based "it's safe to disable" check
- Per-entity cleanup on the underlying ops is incomplete (e.g. zeroing vs removing fields)
- A downstream invariant enforces tight "feature-flag ↔ per-entity-state" coherence

Examples:
- **EVM**: OpenZeppelin's `_beforeTokenTransfer` hook enforces "transfer disabled → no pending approvals"; admin disables transfer while user approvals remain → transfers fail even to admin.
- **Solana**: Token2022 extension disabled by admin; extension-specific TLV data on ATAs is zeroed but not removed → `transfer_checked` fails with extension-not-found.
- **Move**: Aptos object reference that expects a specific Capability flag; cleanup zeros the field instead of removing; later ops hit "unexpected capability state".

## PoC structure

```
1. admin.create_asset(confidential_amount=true, mutable=true)
2. admin.upload_issuer_encryption_key()
3. holder.authorize()
4. admin.pay(holder, 100)               // transparent balance
5. holder.generate_key_pair()
6. holder.convert(50)                    // plants encrypted fields
7. holder.merge_inbox()
8. holder.convert_back(50)               // zeroes fields but doesn't remove
9. admin.mpt_issuance_set(
       clear = CanConfidentialAmount
   )                                     // passes — COA == 0
10. admin.pay(holder, 10)                // tecINVARIANT_FAILED
11. admin.clawback(holder, 10)           // tecINVARIANT_FAILED
12. holder.unauthorize()                 // tecHAS_OBLIGATIONS (sfMPTAmount > 0)
13. admin.destroy_asset()                // tecHAS_OBLIGATIONS (stranded supply)
```

## Feature-pool classification

**XLS-0096 Confidential Transfers for MPT** — root cause code path (`ConfidentialMPTConvertBack`, `ValidConfidentialMPToken`) gated on `featureConfidentialTransfer`. Direct reward-pool match, no bridge needed.

## Dedup verdict

All clean. No prior audit covers XLS-0096 Confidential MPT (not in Halborn MPT DEX, not in FYEO PD/SF). GitHub baseline clean.

## Recommended fix

- **Option A** (preferred): `ConfidentialMPTConvertBack` should `makeFieldAbsent` on zero ciphertexts when accompanied by a proof the encrypted value is zero. Closes SYNC_GAP at source.
- **Option B**: `MPTokenIssuanceSet` CLEAR precondition maintains a per-issuance count of MPTokens with encrypted fields present; refuse CLEAR unless count == 0.

## Why this is the richest finding

Unlike ESC-1/2/3 which all exploit the same F-13 blind spot (different admin ops), CONF-1 validates a completely new pattern — **SYNC_GAP** — in a completely new feature pool. 4 findings, 2 pools, 2 fundamental mechanisms (F-13 and SYNC_GAP). Breadth of exploit-generator templates pays off.

## Related

- [M-09 SYNC_GAP detection](../../methodology/M09-sync-gap-detection.md) — the reusable template derived FROM this finding
- [ESC-1/2/3](.) — same attack class (holder-plants-trap) but different mechanism
