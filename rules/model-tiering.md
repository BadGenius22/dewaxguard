# Model Tiering (Per-Phase Cost/Recall Policy)

> **Origin**: ClaudeDevs multi-model patterns (2026-07). Running every phase at the top model is wasteful; running the *finding* phases cheap is dangerous. This rule splits the pipeline by role so cost drops where judgment is low and premium capability stays where recall matters.
>
> **Status**: Applied by `scripts/dewaxguard_driver.py` (the deterministic driver). The legacy prompt-only orchestrator does not read this file — it is a driver-mode policy.

---

## The two patterns we borrow (and how they map here)

The ClaudeDevs patterns are about *not* paying the top-tier rate for every token:

| Pattern | ClaudeDevs shape | dewaxguard mapping |
|---------|------------------|--------------------|
| **Orchestrator** | Premium model plans and delegates token-heavy work to cheaper sub-agents | A cheap fan-out **dispatcher** subprocess spawns the finding sub-agents; the dispatcher only coordinates, so it runs on `sonnet`/`haiku` while the sub-agents keep their tier |
| **Advisor** | Cheap executor does the bulk; premium model is consulted only at critical decision points | The **decision gate** (bug validator) runs at the commander tier; the high-token PoC/trace **worker** runs cheap |

**The caveat that shapes the mapping.** Those patterns were benchmarked on coding/research (SWE-bench Pro, BrowseComp). Security auditing is **recall-sensitive** — a missed high-severity bug costs far more than a slow run. So we apply the cheap-executor idea only to low-judgment, verifiable work (PoC execution, formatting, coordination) and **never** to the bug-hunting agents. Premium capability stays on the phases that decide whether a bug exists.

---

## The three tiers

| Tier | Model | Roles | Why |
|------|-------|-------|-----|
| **worker** | `sonnet` / `haiku` | verify (PoC + code trace), preflight, bake, inventory, and every fan-out **dispatcher** (recon, breadth, niche, depth, chain, report) | High-token, low-judgment, or pure coordination. The dispatcher's own model does not touch finding quality — the sub-agents it spawns carry that. |
| **finding** | `opus` (core/thorough) | the breadth / depth / niche / nemesis / chain-synthesis / recon-deep **sub-agents**, plus the report Critical+High writer, plus in-subprocess `nemesis` | Where bugs are actually found or the flagship deliverable is written. Recall-sensitive — **never down-tiered.** |
| **commander** | `--commander-model` (default `opus`; `fable` for the advisor pattern) | the bug validator decision gate | Low-token, high-judgment, bounded, verifiable accept/reject scoring — the one place premium pays off cheaply. |

**Key mechanism.** A phase's `claude -p` subprocess model (set in the driver's `PHASES` registry via `Phase.model`) is **independent** of the `model=` a phase prompt passes to a `Task` sub-agent. So a `sonnet` dispatcher can spawn `opus` finding agents. That independence is what lets us make the coordination cheap without touching recall.

---

## Where each tier is set

- **Subprocess tier** — `Phase.model` in `scripts/dewaxguard_driver.py`. `"commander"` resolves at run time to `--commander-model`.
- **Finding sub-agent tier** — the `model=` literals inside the phase prompts (`30_breadth.md` agent table, `45_depth*.md`, `47_chain.md`, `60_report.md` writer agents, `10_recon.md`). **These are the recall-critical knobs — leave them at `opus` for core/thorough.**

If you change a phase's role (e.g. make a dispatcher do finding work directly in-subprocess), update its `Phase.model` accordingly — a subprocess that reasons about bugs itself must be `opus` (see `nemesis`), not `sonnet`.

---

## Enabling the Fable advisor pattern

```bash
python3 scripts/dewaxguard_driver.py --mode core --src ./contracts --commander-model fable
```

This runs the **validator decision gate** on Fable 5 while everything else stays on its role tier. Because the gate is low-token, the incremental cost is small and it lands exactly at the ClaudeDevs "premium advisor at a critical decision point." Leave `--commander-model` at its default (`opus`) for a pure cost-reduction run with no Fable spend.

---

## What NOT to do

- **Do not down-tier the finding sub-agents** (breadth/depth/niche/nemesis/chain-synthesis). That trades recall for cost in the one place recall is the product.
- **Do not up-tier the dispatchers.** A dispatcher that only spawns `Task` agents and self-checks their outputs gains nothing from a premium model.
- **Do not put a `--model fable` on a fan-out phase** expecting the sub-agents to inherit it — they don't; sub-agent tier comes from the prompt `model=` literal.
