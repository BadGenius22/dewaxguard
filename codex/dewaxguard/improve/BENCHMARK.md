---
name: dewaxguard:benchmark
description: "Run DewaxGuard against known-vulnerable contracts and auto-compare results. Instant regression testing after methodology changes. Use: /dewaxguard benchmark"
user-invocable: false
---

# DewaxGuard Live Benchmark Suite

> **Invoked by**: `/dewaxguard benchmark [language] [--quick]`
> **Purpose**: Instant regression testing. Run the pipeline against known-vulnerable contracts, auto-compare, measure recall.
> **Speed**: ~2-5 min per benchmark (light mode). Full suite in ~30 min.

---

## ⛔ MANDATORY: run BLIND (v1.21.0)

The committed benchmark sources contain answer-leaking comments (`// VULNERABLE: ...`, `// SAFE: false positive trap`). **Auditing them directly measures reading comprehension, not bug-finding — the recall number is worthless.** Before ANY benchmark run you MUST strip the answers:

```bash
# 1. Produce answer-blind copies (comments stripped; ground-truth.json NOT copied)
BLIND=$(scripts/blind_benchmark.sh --out /tmp/dgblind)     # all benchmarks
#   or:  scripts/blind_benchmark.sh --out /tmp/dgblind evm-share-inflation solana-missing-signer

# 2. Run the breadth/depth agents on $BLIND/<id>/src  (NEVER on benchmarks/<id>/src)

# 3. Score the agent output against the (unseen) ground truth
scripts/score_benchmark.py <agent_output.txt> benchmarks/<id>/ground-truth.json
#   -> Recall: F/N | Traps clean: C/T | severity deltas per finding
#   exit 0 iff recall==100% AND no trap triggered (CI-gateable)
```

`scripts/selfcheck.sh` regression-guards that `blind_benchmark.sh` removes every answer keyword. **Two banned anti-patterns**: (a) auditing the un-stripped source, (b) editing a `ground-truth.json` to match agent output — oracles are corrected only when the code is independently re-read and the oracle is provably wrong, always with an `_oracle_review` note (see the v1.21.0 Sui correction). See `ACCURACY.md`.

---

## Benchmark Directory Structure

```
~/.agents/skills/dewaxguard/benchmarks/
├── manifest.json                    # Registry of all benchmarks
├── evm/
│   ├── reentrancy-basic/
│   │   ├── src/                     # Minimal vulnerable contract
│   │   ├── foundry.toml             # Build config
│   │   └── ground-truth.json        # Expected findings
│   ├── share-inflation/
│   │   ├── src/
│   │   ├── foundry.toml
│   │   └── ground-truth.json
│   └── oracle-staleness/
│       ├── src/
│       ├── foundry.toml
│       └── ground-truth.json
├── solana/
│   ├── missing-signer/
│   ├── pda-substitution/
│   └── ...
├── aptos/
│   └── ...
└── sui/
    └── ...
```

---

## manifest.json Format

```json
{
  "version": "1.0.0",
  "benchmarks": [
    {
      "id": "evm-reentrancy-basic",
      "name": "Basic Reentrancy",
      "language": "evm",
      "path": "evm/reentrancy-basic",
      "difficulty": "easy",
      "vulnerability_class": "reentrancy",
      "expected_severity": "High",
      "lines_of_code": 45,
      "added_in": "1.2.0",
      "description": "Single-contract reentrancy via external call before state update"
    }
  ]
}
```

---

## ground-truth.json Format

```json
{
  "findings": [
    {
      "severity": "High",
      "class": "reentrancy",
      "location": {
        "file": "src/Vault.sol",
        "line_start": 42,
        "line_end": 48
      },
      "description": "External call before state update allows reentrant withdrawal",
      "must_detect": true
    }
  ],
  "false_positive_traps": [
    {
      "description": "Safe reentrancy guard on deposit() — should NOT be flagged",
      "location": {
        "file": "src/Vault.sol",
        "line_start": 20,
        "line_end": 25
      }
    }
  ]
}
```

`must_detect: true` = pipeline MUST find this to pass.
`false_positive_traps` = things that LOOK vulnerable but aren't. Pipeline should NOT flag these.

---

## Benchmark Execution Flow

### `/dewaxguard benchmark`

```
1. Read manifest.json
2. For each benchmark (or filtered by language/--quick):

   a. Copy benchmark to temp directory
   b. Run: /dewaxguard light {temp_dir}
      (light mode = fast, ~2 min per benchmark)
   c. Read generated AUDIT_REPORT.md
   d. Compare vs ground-truth.json:
      - For each must_detect finding:
        → Search report for matching severity + location (±10 lines)
        → FOUND / MISSED
      - For each false_positive_trap:
        → Search report for findings near that location
        → CLEAN (not flagged) / FALSE_POSITIVE (incorrectly flagged)
   e. Record result

3. Print summary table
4. Write results to benchmarks/results/{version}_{date}.md
```

### Quick Mode (`--quick`)
Run only benchmarks tagged `difficulty: "easy"`. Fastest smoke test (~5 min total).

### Language Filter (`/dewaxguard benchmark evm`)
Run only benchmarks for the specified language.

---

## Results Output

```markdown
# Benchmark Results — DewaxGuard v{version}

Date: {YYYY-MM-DD}
Mode: full / quick / {language}
Duration: {total time}

## Summary
| Metric | Value |
|--------|-------|
| Total benchmarks | {N} |
| Bugs detected | {N}/{total must_detect} |
| Recall | {%} |
| False positives triggered | {N}/{total traps} |
| FP Rate | {%} |

## Per-Benchmark Results
| ID | Language | Class | Expected | Found? | FP? | Time |
|----|----------|-------|----------|--------|-----|------|
| evm-reentrancy-basic | evm | reentrancy | High | FOUND | CLEAN | 1.8s |
| evm-share-inflation | evm | share inflation | Critical | FOUND | CLEAN | 2.1s |
| evm-oracle-staleness | evm | oracle | Medium | MISSED | CLEAN | 1.5s |
| solana-missing-signer | solana | access control | High | FOUND | CLEAN | 2.3s |

## Regressions (vs previous run)
| ID | Previous | Current | Change |
|----|----------|---------|--------|
| evm-oracle-staleness | FOUND | MISSED | REGRESSION |

## Recommendations
- evm-oracle-staleness: REGRESSION — investigate what changed since v{prev_version}
```

---

## Adding New Benchmarks

### From Past Audits (`/dewaxguard benchmark add`)

After `/dewaxguard improve` identifies a miss:

1. Ask user: "Add a benchmark for this vulnerability class?"
2. If yes, create a MINIMAL vulnerable contract:
   - Strip all non-essential code from the original
   - Keep ONLY the vulnerable pattern + enough context to compile
   - Target: <100 lines of code per benchmark
   - NEVER copy the original contract verbatim (IP concerns)
3. Write ground-truth.json with expected findings
4. Add to manifest.json
5. Run the benchmark to verify it works

### From Public CTFs

Supported sources for seeding:
- **Damn Vulnerable DeFi** (EVM): Well-known challenges, great for baseline
- **Ethernaut** (EVM): OpenZeppelin's challenge set
- **Neodyme Workshop** (Solana): Solana-specific vulnerabilities
- **Move CTF challenges** (Aptos/Sui): Community challenges

### Benchmark Quality Rules

1. Each benchmark tests exactly ONE vulnerability class
2. Maximum 100 lines of source code (minimal reproduction)
3. Must compile and be auditable by the pipeline
4. Must include at least one `false_positive_trap` (tests precision, not just recall)
5. Description must be generic (class-level), not reference the original source

---

## Regression Detection

When running benchmarks after a methodology change:

```
previous_results = load("benchmarks/results/{prev_version}_*.md")
current_results = run_benchmarks()

for each benchmark:
  if previous == FOUND and current == MISSED:
    → REGRESSION DETECTED
    → Print: "WARNING: {benchmark_id} regressed after v{version} changes"
    → Suggest: revert the change or add a guard

for each benchmark:
  if previous == MISSED and current == FOUND:
    → IMPROVEMENT DETECTED
    → Print: "IMPROVEMENT: {benchmark_id} now detected after v{version} changes"
```

---

## Integration with Other Improvement Commands

```
/dewaxguard improve       → identifies gaps → proposes fixes
                          → after applying fixes:
                          → auto-suggest: "Run /dewaxguard benchmark to verify?"

/dewaxguard benchmark     → detects regressions
                          → if regression found:
                          → auto-suggest: "Revert last change? Or investigate?"

/dewaxguard batch-import  → identifies methodology gaps across many contests
                          → after applying fixes:
                          → auto-suggest: "Run /dewaxguard benchmark to verify?"

/dewaxguard consolidate   → removes/merges content
                          → after applying:
                          → auto-suggest: "Run /dewaxguard benchmark to check for regressions?"
```

Every improvement path ends with a benchmark verification step.

---

## Bootstrap: Starter Benchmarks

To bootstrap the suite, create these 6 starter benchmarks covering core vulnerability classes:

### EVM (3)
1. **evm-reentrancy-basic**: External call before state update. ~40 lines. High.
2. **evm-share-inflation**: ERC4626 first-depositor attack. ~60 lines. Critical.
3. **evm-unchecked-return**: Low-level call without return check. ~30 lines. Medium.

### Solana (2)
4. **solana-missing-signer**: Instruction handler without signer check. ~50 lines. High.
5. **solana-pda-substitution**: PDA not verified against expected seeds. ~60 lines. High.

### Move (1)
6. **sui-shared-object-race**: Shared object concurrent access. ~50 lines. Medium.

These cover the most common vulnerability classes per language and provide a baseline recall measurement from day 1.
