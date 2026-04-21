# Sherlock PoC Requirements

> **Coded PoC is mandatory for any severity**, including Low. Explicitly overrides standard Sherlock judging rules.

## Requirement source

From the contest FAQ (XRPL April 2026):
> "A valid finding must demonstrate new impact or significantly elevated impact in 'Current version' in comparison to 'Previous Version', and must include a **coded PoC that contains transactions and/or APIs that relate to a feature's XLS spec**. Coded PoCs are mandatory for any issue of any severity."

Key clauses:
- **Coded** — not a walkthrough, not a conceptual trace. Runnable code.
- **Transactions and/or APIs** — the code must submit txs or call RPC methods.
- **Feature's XLS spec** — ties to the reward-pool classification (see [M-04](../../methodology/M04-feature-pool-coverage.md)).
- **Any severity including Low** — Sherlock explicitly waives the walkthrough fallback.

## Preferred PoC style

In-tree unit test matching the project's test framework:
- **EVM**: Foundry `forge test`; Hardhat `npx hardhat test`.
- **Solana**: Anchor `#[cfg(test)]` module; or `solana-program-test`.
- **Move / Aptos**: `aptos move test`.
- **Move / Sui**: `sui move test`.
- **Soroban**: Rust `#[cfg(test)]` with `soroban-sdk::testutils`.
- **C++ / XRPL**: `beast::unit_test` — see [patterns/xrpl-2026-04](../../patterns/xrpl-2026-04/) for 4 validated examples.

## Self-contained PoC rules

1. **Single file if possible** — reviewer pastes one block into one location.
2. **Auto-discovered by build** — use conventions that don't require CMake edits (XRPL auto-globs `src/test/app/`, Foundry auto-discovers `test/**/*.t.sol`).
3. **Banner comment at top**:
   ```
   // ===================================================================
   //  SAVE THIS FILE AS: {path/relative/to/project/root.ext}
   // ===================================================================
   ```
4. **No external fixtures** — all test data constructed inline.
5. **Deterministic** — same input = same output. No randomness beyond what the framework provides.

## Assertion requirements

Every PoC must explicitly assert:
1. **Pre-state** — the initial state before the attack.
2. **Intermediate state** after the planting action (if applicable).
3. **Expected error / failure** on the admin action — use `ter(tecINVARIANT_FAILED)`, `expect(revert)`, `.expect_err(...)` etc.
4. **Post-state** — prove the bricking / inconsistency is permanent.
5. **Second attempt** — re-run the failing op to prove it's persistent, not transient.

## Output requirements

Expected-output section should include:
- The test-framework header line ("Running 1 test case..." etc.)
- Any log lines that prove the bug (e.g. `FTL: Invariant failed: ...` for XRPL)
- The success summary ("0 failures", "ok. 1 passed", "test result: ok")

## Reproducibility

Reviewer should be able to:
1. `cd {project}/{test-dir}`
2. Paste the code block into `{test-file-path}`
3. `{build-command}`
4. `{run-command}`
5. See exactly the expected output

**5 steps, 5 minutes** — target reproducibility budget.

## Pristine-repo validation (recommended before every submission)

Per Sherlock contest FAQ (April 2026 update), PoCs are expected to apply cleanly to a pristine clone of the contest repo. Use `git stash` to verify your PoC is self-contained without losing your working state:

```bash
# 1. Stage ONLY the PoC files (not your other in-progress work)
git add <poc-file-path(s)>

# 2. Save as a patch file OUTSIDE the repo to prevent accidental stashing
git diff --cached > /tmp/poc.patch

# 3. Stash everything else (including your other in-progress audit work)
git stash push -u -m "WIP before PoC validation"

# 4. Apply the patch to the now-clean tree
git apply /tmp/poc.patch

# 5. Build + run the PoC — if it works, the PoC is self-contained
cd .build && cmake --build . --target xrpld
./xrpld --unittest=YourTestSuite

# 6. Restore your working state
git checkout -- .      # discard the applied patch
git stash pop          # restore your other WIP
```

If step 5 fails, your PoC depends on other uncommitted changes. Fix before submitting — judges test against pristine clones.

## Anti-patterns

- **Don't attach external files** — Sherlock is markdown-only.
- **Don't reference `/path/to/X`** — placeholder syntax reviewers paste literally.
- **Don't use "should revert"** without a concrete expected error code.
- **Don't fake reproduction output** — judges know the framework signatures.
- **Don't skip pristine-repo validation.** A PoC that works only on your dirty tree is an invalid submission.

## Examples

See 4 validated XRPL beast test PoCs in [`patterns/xrpl-2026-04/`](../../patterns/xrpl-2026-04/):
- `esc1-clawback-shield.md`, `esc2-dust-destroy.md`, `esc3-vault-share.md`, `conf1-flag-clear-brick.md`

Each uses a single `_test.cpp` file, auto-globbed into the xrpld binary, asserting `tecINVARIANT_FAILED` / `tecINSUFFICIENT_FUNDS` / `tecHAS_OBLIGATIONS` via `ter(...)`.
