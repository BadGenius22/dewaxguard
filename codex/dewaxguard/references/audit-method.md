# Audit Method — Cross-Cutting Rules (applies to ALL audit work, every tool)

These three rules bind every audit session regardless of tool: dewaxguard, dewaxoffense, dewaxdlt,
plamen, solidity-auditor, solana-auditor, or an ad-hoc read. They are tool-independent because each
one describes a way the *output of a model* can look like work without being work.

Source: 0xSimao, "How I use AI in smart contract audits (2026)", 4 August 2026 (user-supplied
article, no URL captured). Adapted to a multi-agent pipeline, where the failure modes are amplified
rather than removed.

---

## Rule A-1: A quiet pass is not coverage

An agent pass that surfaces nothing is evidence that *this run* surfaced nothing. It is not evidence
that the code is clean. These are different claims and only the first one is supported.

This matters more in a multi-agent pipeline than for a single human, because the pipeline runs the
same non-deterministic process N times and then reports the union as if it were a swept area.

**Binding consequences:**

1. **Never write "coverage" for a count of processed findings.** `N/N verified`, `N/N hypotheses
   routed`, `all files analyzed` are throughput numbers. Label them throughput. The word *coverage*
   is reserved for a claim backed by a mechanical enumeration (a file list, a selector list, an
   entry-point list) where the enumeration itself is the evidence.
2. **Never treat "iteration produced 0 new findings" as a stopping proof.** It is a stopping
   *heuristic* and must be reported as one: "run converged" not "area is clean".
3. **Every audit report states its negative space** — what was not examined, what was examined but
   not proven either way, and which areas the run was unstable on. A report with no negative-space
   section is incomplete, not clean.
4. **A clean sub-agent return never upgrades confidence in a finding's absence.** It only fails to
   lower it.

## Rule A-2: No uncited mechanism claim, ever

Do not ask a model how something works and accept the answer. In a multi-agent pipeline every
handoff is exactly that: recon tells breadth what the protocol does, inventory tells depth what was
found, chain tells verify what to prove. Each hop launders a guess into a premise.

**Binding consequences:**

1. **Any claim about what the code does, crossing an agent boundary, carries `file:line`.** This
   covers recon summaries, protocol descriptions, "the guard at X prevents Y", "this is only
   callable by Z", and every load-bearing sentence in a finding.
2. **A consuming agent treats an uncited claim as a hypothesis, not a fact**, and must either verify
   it against source before relying on it or mark the finding's dependence on it explicitly.
3. **This applies to my own prior turns.** A conclusion I reached earlier in the session is a
   hypothesis to re-check if it becomes load-bearing for a verdict, a submission, or a memory write.
4. **A subagent's report is a claim, not a result.** Check the load-bearing parts against the
   primary source before relaying them, before they enter a verdict, and before they enter memory.

## Rule A-3: A test that cannot fail proves nothing

Writing a PoC is cheap now. Reading it is the work. A test that exercises a mock rather than the
real integration proves only that the mock behaves the way the model imagined it.

**Binding consequences — a PoC is not evidence until all four hold:**

1. **Mutation check.** Revert the bug (restore the missing guard, fix the operator, patch the line)
   and re-run. The test MUST fail. If it still passes, the assertion is not measuring the bug and
   the result is void, whatever the tag says.
2. **Positive control.** Before trusting a *negative* result, run a known-good operation through the
   same harness and confirm it succeeds. A `FAIL` from a broken harness is indistinguishable from a
   `FAIL` from a hardened target.
3. **Real-path audit.** Enumerate every address / program / account the test touches. Each is either
   a real deployed identity (cite it) or an explicitly labelled mock. No mock may sit on the value
   flow being proven.
4. **Assertion audit.** The assertion measures a balance or accounting delta in the attacker's
   favour. "Did not revert", "call succeeded", and a bare `expectRevert` are not assertions about
   harm.

Downgrade rule: a PoC failing any of the four drops to `[CODE-TRACE]` at best and cannot support a
CONFIRMED verdict.
