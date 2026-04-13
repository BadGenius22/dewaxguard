# Phase 4b.5: RAG Validation Sweep (Solodit Database)

> **Trigger**: Always, after Phase 4b depth loop exits and before Phase 5 (verification + bug validator).
> **Purpose**: Validate every finding against historical precedent in the Solodit vulnerability database. Adds a confidence axis based on prior art.
> **Model**: sonnet (haiku rejects unified-vuln-db MCP tool schemas containing oneOf/allOf)
> **Budget**: 1 agent (not counted against breadth/depth budget)

---

## Why This Exists

A finding with strong historical precedent (multiple Solodit matches for the same vulnerability class) is:
- **More likely to be accepted** by judges (recognized class, clear precedent)
- **Easier to argue against AI invalidators** (the class exists and has been awarded before)
- **Useful for severity calibration** (compare against similar findings' severities)

A finding with NO precedent is either:
- **Genuinely novel** (rare, high signal — flag for extra verification)
- **A false positive** (most common — agents hallucinate "vulnerabilities" that don't exist as a class)

The bug validator (Phase 5d) uses the RAG score as one of its confidence axes.

---

## Pre-check: RAG_TOOLS_AVAILABLE flag

Before spawning, the orchestrator reads `{SCRATCHPAD}/build_status.md` for `RAG_TOOLS_AVAILABLE`. This flag is set by the recon agent's MCP tool probe in Phase 1.

| Flag value | Action |
|-----------|--------|
| `RAG_TOOLS_AVAILABLE = true` | Spawn RAG sweep with MCP path enabled |
| `RAG_TOOLS_AVAILABLE = false` | Spawn RAG sweep in **WebSearch fallback mode** |
| Flag missing | Assume `true`; agent handles failures via fallback chain |

The recon agent probes MCP availability by attempting one call to `mcp__unified-vuln-db__validate_hypothesis` with a trivial input. If the call returns successfully (any result), set `RAG_TOOLS_AVAILABLE = true`. If it errors with schema/API failure, set `false`.

---

## Orchestrator spawns

```
Task(
  subagent_type="general-purpose",
  model="sonnet",
  prompt="
You are the RAG Validation Sweep Agent for DewaxGuard.

## Your Task
For EVERY finding in {SCRATCHPAD}/findings_inventory.md:
1. Call mcp__unified-vuln-db__validate_hypothesis(hypothesis='{finding title}: {1-line root cause}')
2. Call mcp__unified-vuln-db__search_solodit_live(keywords='{vulnerability class} {key term}', max_results=10)
3. Record the result with both scores

If a tool call fails (timeout, schema error, API error), record [RAG: TOOL_ERROR] for that finding — do NOT silently skip.

## Fallback Chain (if MCP tools fail)
1. Try mcp__unified-vuln-db__get_similar_findings(pattern='{finding description}')
2. If that fails: try mcp__unified-vuln-db__get_common_vulnerabilities(category='{vulnerability class}')
3. If ALL MCP tools fail: WebSearch fallback — search 'site:solodit.xyz {vulnerability class} {key term}' and extract match count
4. If WebSearch also fails: record [RAG: ALL_TOOLS_FAILED] and score = 0.3

**Fast-fail rule**: If the FIRST MCP call fails with a schema/API error, assume ALL MCP calls will fail. Switch IMMEDIATELY to WebSearch fallback for remaining findings — do not retry each one. This prevents N×timeout delays.

**Empty-DB detection**: If MCP tools SUCCEED but return 0 examples for the first 3 findings, treat as 'empty database' and run WebSearch as a COMPLEMENT for all remaining findings. MCP success with empty results = MCP failure for novel protocols.

## Score Calculation
Per finding, compute Final RAG Score = max(validate_hypothesis_score / 10, solodit_match_score)
Where:
- validate_hypothesis_score: returned by the MCP tool (0-10 typically)
- solodit_match_score: 1.0 if 5+ matches, 0.7 if 2-4 matches, 0.3 if 1 match, 0.0 if 0 matches

## Output
Write to {SCRATCHPAD}/rag_validation.md:

| Finding ID | Title | validate_hypothesis | Solodit Matches | Final RAG Score | Notes |
|-----------|-------|---------------------|-----------------|-----------------|-------|
| M-01 | EIP-712 missing macro binding | 8/10 | 12 matches | 1.0 | Strong precedent: ABCD audit 2024, EFGH 2023... |

Return: 'DONE: {N} findings validated, {E} tool errors, fallback={MCP|WEB|NONE}, avg_score={X.XX}'
")
```

---

## Retry on agent failure (orchestrator inline)

If the RAG sweep agent itself fails (API error, crash, 0 output):
1. **Do NOT retry with the same model** — failures are typically schema-level, not transient
2. Log: `"RAG sweep failed: {error}. Writing floor scores."`
3. Write `{SCRATCHPAD}/rag_validation.md` with `0.3` floor for all findings (preserves pipeline progress)
4. Continue to Phase 5 (verification + bug validator)

---

## Integration with Bug Validator (Phase 5d)

The bug validator reads `rag_validation.md` and uses the RAG score as **one input to the confidence breakdown**:

| RAG Score | Effect on bug validator |
|-----------|------------------------|
| ≥ 0.7 (strong precedent) | +5 confidence boost. Highlight in report: "X historical matches on Solodit." |
| 0.4-0.7 (some precedent) | Neutral. Note matches in report. |
| 0.1-0.4 (weak precedent) | -5 confidence. Flag for extra verification. |
| 0.0 (no precedent) | -10 confidence. Either novel (rare) or likely FP. Force extra trace. |

---

## Submission Hardening Use (Phase 5d.1)

When the bug validator scores a finding < 85 due to "no precedent" deduction:
- The Submission Hardening pass uses the Solodit matches (when present) as **differentiating evidence**
- Cite specific historical findings to strengthen the dup-resistance argument: "Similar to [Sherlock issue X-NN, contest Y]: ${one-line summary}"
- This signals to judges: "this is a recognized class with known severity" rather than a novel speculation

---

## Output Artifact

`{SCRATCHPAD}/rag_validation.md` — read by:
- Phase 5d (Bug Validator) — for confidence axis input
- Phase 5d.1 (Submission Hardening) — for deduplication evidence and precedent citations
- Phase 6 (Report) — for "Historical Precedent" footnote per finding
