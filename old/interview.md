# Vendor vs Valor Interview Guide

This file is the interview and assignment guide for Vendor vs Valor. The three architecture docs stay focused on their titles:

- `design-v2.md`: why this product exists and the decision model.
- `mvp-hld-and-build-spec.md`: the buildable MVP and load-bearing contracts.
- `target-architecture.md`: the production architecture the MVP grows into.

Use this guide for the human conversation: pitch, demo path, role mapping, likely questions, and fallback lines.

---

## 1. The answer in one sentence

Emergence's thesis is leverage: one good thing multiplied across the portfolio. Vendor vs Valor is the decision layer that helps allocate engineering capital with the same rigor every time a portfolio company asks whether to build, buy, extend, or self-host a capability.

## 2. The 30-second pitch

Every portfolio company repeatedly faces "should we build this or buy it?" decisions. Today those calls are often made from local judgment, vendor demos, or shallow research. Vendor vs Valor turns that into a repeatable, cited, human-gated workflow: it interviews the operator, researches build and buy evidence, reasons over four strategic paths, challenges its own recommendation, and emits an auditable strategy.

The key point: it is advisory infrastructure, not an autonomous decision-maker. Research is automated; the capital-allocation call stays with the humans.

## 3. The 2-minute narrative

Emergence acquires profitable, founder-led B2B software companies that are often technically underinvested. As the platform team modernizes them, the same capability questions recur: vector DBs, eval harnesses, billing, fraud, document parsing, data products, AI infrastructure.

The waste is not just that each company repeats research. The bigger miss is portfolio arbitrage: something too expensive for one company may be cheap when amortized across several, and a vendor that looks cheap today may become expensive once switching costs and renewal risk are priced in.

Vendor vs Valor encodes that decision discipline once:

- Intake captures the capability need, constraints, resources, customization need, and qualitative steer.
- Research builds two evidence pools: BUILD and BUY.
- Synthesis reasons over four paths: build, buy, buy-then-extend, adopt-and-self-host.
- A challenger pass argues for a different path using the same verified evidence.
- The final output is a cited strategy with recommendation, runner-up, decisive factors, path dossiers, risks, reversibility, and open questions.

The product mirrors the governance pattern from model-risk work: the thing that produces an artifact is not the thing that clears it. In this project, claims are authored by research/synthesis stages but verified by a separate `grounded_claim` gate that reads cached source bytes.

## 4. What to show first

Lead with the decision surface, not the code.

1. The four-path model:
   Build, buy, buy-then-extend, adopt-and-self-host. Explain that "acquire" was removed because M&A diligence is outside what web research can responsibly prove.
2. The two-pool insight:
   Paths are not separate agents. BUILD and BUY are the evidence pools; synthesis recombines them into four strategic lenses.
3. The trust layer:
   Every factual claim is source-bound, cached, verified, filtered, and only then allowed into synthesis.
4. The human gates:
   Intake, research, and strategy are review points. The system pauses; the operator approves or edits.
5. The target arc:
   The MVP is one-process and file-backed. The Target splits it into services, durable orchestration, structural grounding, portfolio memory, provider routing, and calibration.

## 5. Demo flow

Use the current vector-database scenario unless the interviewer asks for a different runtime need:

> We need a vector database to power semantic search over our product catalog. Small platform team, cost-conscious, data is not especially sensitive, and we want flexibility over vendor lock-in.

### Preflight

- Confirm `.env` has the Gemini key and model overrides if needed.
- Run `uv run pytest` if there is time.
- If network is risky, pre-stage one clean run so `runs/<id>/sources/` contains cached evidence.

### Quick checkpoint demo

Use this when time is short or you want to show the research core:

```bash
uv run python scripts/cp4_demo.py
```

What to point out:

- Intake creates a structured profile and soft steer.
- BUILD and BUY run as separate evidence pools.
- Claims are cited and verified.
- Unsupported claims are dropped, partial/stale/conflicting claims are flagged.
- Artifacts are inspectable under `runs/<id>/`.

### Full end-to-end demo

Use this when there is enough time for the graph:

```bash
uv run python scripts/cp5_demo.py
```

What to point out:

- LangGraph parks at gates and resumes with approvals.
- The graph runs intake -> research -> synthesis/challenger -> strategy.
- `strategy.md` is the main deliverable.
- Report rendering is the next slice if `report_node` is still a TODO.

## 6. Repository walkthrough

Start with the files that prove the architecture exists as code:

- `rubric/metrics.json`: the 14 research dimensions. These are structure, not scores.
- `rubric/paths.json`: canonical path-to-evidence-pool mapping.
- `skills/grounded_claim/`: `Claim`, `assert_claim`, `verify`, `filter`, source cache, locator computation.
- `skills/schema_stage/`: load -> LLM -> validate -> persist wrapper with input-hash skipping.
- `agents/`: the prompts that hold the product IP: intake, query planning, build research, buy research, synthesis, challenger.
- `stages/intake.py`: profile schema and markdown rendering.
- `stages/research.py`: planner, search, fetch, cache, author, assert, verify, filter, coverage.
- `stages/synthesis.py`: four-path dossiers, challenger, claim-id validation, buy-then-extend API gate, price-conflict flagging.
- `graph.py`: LangGraph nodes, isolated interrupt gates, parallel BUILD/BUY branches, checkpointer support.
- `tests/`: proof that the load-bearing invariants are executable, not just documented.

## 7. What is already implemented

Current code has:

- Rubric and path validation.
- `grounded_claim` with computed locators, source cache, cost-date requirements, verifier status separation, stale-cost filtering, and tests.
- `schema_stage` with input-hash idempotency and tests.
- Intake profile generation and validation.
- Research with LLM query planning fallback, domain-diverse discovery, full-page fetch/cache, excerpt shaping for pricing/date windows, claim assertion, verification, filtering, and coverage gaps.
- Synthesis with four dossiers, recommendation, runner-up, decisive factors, open questions, challenger degradation, citation validation, buy-then-extend API-surface enforcement, and conservative price-conflict flags.
- LangGraph skeleton with three isolated gate nodes and parallel BUILD/BUY research branches.
- Demo scripts for CP4 and CP5.

Call out honestly:

- `report_node` is currently a TODO slice.
- Portfolio memory is intentionally stubbed in MVP.
- Structural grounding at emission is Target, not MVP.
- Confidence scoring is Target, not MVP.

## 8. Why the design changed from old docs

The old version used five paths, weighted rubrics, scoring, and a specific HIPAA document-parser scenario. The current version is stronger because:

- Five paths became four: acquire was removed because it needs M&A diligence, not web research.
- Weighted scoring was removed because it creates false precision and makes the operator do a 14-number chore.
- Qualitative decisive factors replaced weights: the engine explains what drove the recommendation.
- The demo scenario became runtime input instead of design structure.
- `grounded_claim` became the trust center, with cached source bytes and independent verification.
- Challenger was added so the engine argues against itself before it ships a recommendation.

## 9. Role mapping

Use these lines when the conversation turns to fit for the assignment or role:

- "Design shared AI infrastructure portfolio companies standardize on":
  This is a standardized decision layer. Every company can run capability-sourcing decisions through the same rails.
- "Own system-design reviews across the portfolio":
  Vendor vs Valor makes those reviews consistent, cited, repeatable, and auditable instead of ad hoc.
- "Optimize cost/latency":
  MVP already caches sources and avoids redundant work with input hashes. Target adds provider routing, cross-run cache reuse, token budgets, and spend caps.
- "Mentor portfolio engineers":
  The output teaches the decision discipline every run because it shows evidence, alternatives, decisive factors, and reversibility.
- "Governance differentiator":
  `grounded_claim`, the challenger, and the audit trail are governance rails for capital allocation instead of model risk.

## 10. Answers to likely questions

### Why not just use a generic deep-research agent?

Generic research is the commodity. Vendor vs Valor owns the decision layer: two evidence pools, four strategic paths, portfolio reuse logic, cost/reversibility/compliance dimensions, claim verification, and challenger-tested synthesis.

### Why no numeric score?

Scores look precise but are hard to defend. The useful artifact is not "buy scored 3.8." It is "buy-then-extend wins because API surface is strong, build effort is high, data sensitivity is low, and switching cost is manageable; build wins instead if proprietary data becomes the moat."

### Why not include acquire?

Acquire is real, but it is M&A diligence. The system should not pretend web research can value a company or diligence an acquisition. If a sibling already has a capability, the Target surfaces reuse through Portfolio Memory; it does not score M&A.

### What is the deepest technical piece?

The `grounded_claim` contract. The author emits only a draft claim and quote. Code computes the locator into cached source content, builds the claim id, and keeps status `UNVERIFIED`. Verification is a separate pass that reads cached bytes and sets `SUPPORTED`, `PARTIAL`, or `UNSUPPORTED`. Unsupported claims are dropped before synthesis.

### Why LangGraph?

The pipeline needs human gates and resumability. LangGraph provides `interrupt()` and checkpointer-backed resume natively, so the MVP does not hand-roll workflow state. The Target can swap the checkpointer backend without rewriting node logic.

### Why Gemini?

The workload is input-heavy research and synthesis. Gemini gives low iteration cost and large context headroom. The provider interface keeps it reversible, so per-stage routing to Claude or GPT is a configuration decision later.

### What fails safely?

Search/fetch failures become coverage gaps. Unsupported claims are dropped. Partial claims are flagged. Gated pricing is stated as a finding. Conflicting cost evidence is surfaced instead of silently averaged. If the challenger is time-boxed, synthesis still produces a runner-up.

### How does it scale?

Target splits the MVP into Intake, Research, Synthesis, Reporting, Portfolio Memory, and Orchestration services. Research fans out within tracks. The source cache becomes cross-run with freshness rules. Portfolio Memory turns local decisions into compounding institutional memory.

## 11. Demo talking points by artifact

### `profile.md` / `profile.json`

"This is where the operator's vague need becomes structured input. The key is case-agnostic intake: the system does not hard-code healthcare, fintech, or any vertical. It captures general constraints and lets evidence drive the decision."

### `build-research.md` and `buy-research.md`

"These are substrates, not recommendations. BUILD and BUY collect facts; synthesis later frames those facts into four paths."

### `verify-report.json`

"This is the trust checkpoint. It shows what was kept, dropped, rejected at assertion, or flagged. The author cannot bless its own claims."

### `strategy.md`

"This is the product output: recommendation, runner-up, decisive factors, per-path dossiers, reversibility, and open questions. It is designed for a human decision review, not for blind automation."

### `sources/`

"The source cache is what makes the demo and verification stable. Verification reads cached bytes, not live web pages that may change mid-run."

## 12. Strong phrasing to reuse

- "Research is autonomous; judgment is human-gated."
- "Paths are lenses over evidence pools, not separate agents."
- "The system grounds facts, not vibes."
- "No recommendation ships without reversibility."
- "A missing price is a finding, not a hole to fill with a made-up number."
- "The engine knows the edge of its competence. That is why acquire is out."
- "The MVP proves the engine is grounded and consistent. The Target proves it can become calibrated and portfolio-aware."

## 13. What not to say

- Do not call it an autonomous capital allocator. It is advisory.
- Do not say it replaces legal, security, procurement, or M&A diligence.
- Do not promise portfolio memory in the MVP. It is a Target service.
- Do not pitch scores, weights, or numeric confidence. Those were deliberately removed.
- Do not hard-code the vector database example into the product story. It is only a runtime demo input.
- Do not overclaim source verification. MVP catches unsupported claims post-hoc; Target moves grounding earlier and makes unsupported claims block promotion.

## 14. Closing line

Vendor vs Valor is not just a demo of agents doing research. It is a small version of the operating system a permanent-capital software platform needs: a repeatable, cited, human-gated way to decide where engineering capital should go.
