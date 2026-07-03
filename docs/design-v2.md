# Vendor vs Valor
### Design & Decision Model (v2.0)

> An advisory intelligence layer that turns capability sourcing from a hallway conversation into a grounded, citation-backed recommendation — by first understanding intent, then researching internal and vendor-led paths autonomously, then reasoning over four strategic options and arguing against its own answer before it ships.

**Author:** Rohan
**Context:** Designed for Emergence Software (permanent-capital B2B software holding company; "buy-to-build" model; multiple portfolio companies across data and infrastructure verticals).
**Status:** Design — targets a 1–2 day implementation of the MVP slice (see *MVP HLD & Build Specification*).
**Companion documents:** *MVP HLD & Build Specification* (the buildable slice, at HLD + targeted-LLD altitude) and *Target Architecture* (the production-scale design, at architecture altitude).
**Substrate & model:** **LangGraph** orchestration (graph nodes, `interrupt()` human gates, checkpointer-backed resume) with **Gemini** as the default model (Flash workhorse, Pro for synthesis), behind a provider interface so the model is swappable. Both are reversible choices; the reasoning lives in §10.
**Deliverable shape:** Markdown core (`profile.md`, `build-research.md`, `buy-research.md`, `strategy.md`) + lightweight self-contained HTML report.

**What changed from v1.0:** the engine is now **qualitative, not scored**. Weighted rubrics and 1–5 scoring are gone — they were unverifiable theater that offloaded a 14-number chore onto the operator. The engine now *reasons and cites*: it surfaces which factors were decisive rather than asking the human to pre-weight them. It also **argues against its own recommendation** (a challenger pass) before producing the runner-up. The five-path model is now four (acquire dropped — it is M&A diligence, not web-researchable). The engine is **case-agnostic by specification**: no domain is baked into the design.

---

## 0. TL;DR for the reader who has 60 seconds

Emergence's entire edge is **leverage**: build one good thing, multiply it across N companies. Every portfolio company independently faces a stream of "build it or license it" calls — a vector DB, an eval harness, a billing system, a fraud model, a document parser. Today those calls are made locally, inconsistently, and without rigorous research. That is wasted capital and duplicated effort across the portfolio.

This engine is the **research infrastructure** for those calls. A platform-team operator describes a need; the engine runs intake to build a structured **need-profile**, runs **two research tracks** (build economics and buy-market scan), reasons over **four strategic paths**, and produces an **advisory recommendation** — with a runner-up, the conditions under which the runner-up wins, the decisive factors, and the evidence behind every claim. Then, before it ships, a **challenger pass** tries to make the strongest cited case for a *different* path; whatever it surfaces becomes the runner-up. Every claim is cited and independently verified.

It is deliberately **advisory, not autonomous-deciding**: research is autonomous, the decision stays human. That is the correct posture for capital-allocation decisions and it mirrors the governance-rails pattern — every model passes through a common gate — applied to capital instead of compliance.

**Vendor vs Valor verdict on the engine itself:** *buy-then-extend.* Generic deep-research agents are commoditized and open-source; the **domain logic, dual-track scoping, four-path reasoning, citation grounding, and portfolio-reuse lens** are the IP. We stand on a research primitive and build the differentiating layer. (The engine, applied to itself, recommends exactly this.)

---

## 1. Why this exists — the business case

### 1.1 The problem, stated in Emergence's terms

Emergence acquires profitable, founder-led, **chronically underinvested** B2B software companies and then invests to scale them. "Underinvested" means each company arrives with a backlog of deferred technical decisions. As the platform team modernizes them — adding AI capabilities, replacing aging infrastructure, building data products — the same question recurs dozens of times across the portfolio:

> *Do we build this capability in-house, license a SaaS, license a platform and extend it, or adopt open-source and self-host it?*

Made locally and casually, these decisions:
- **Duplicate effort** — six companies each evaluating vector DBs independently.
- **Miss the portfolio-arbitrage** — a "build" that's expensive for one company is cheap amortized across six.
- **Lack rigor** — chosen on a vendor demo or a senior engineer's gut, not researched.
- **Ignore reversibility** — cheap SaaS with brutal switching costs becomes a trap nobody priced.

### 1.2 Why an engine, not a consultant or a checklist

| Option | Why it falls short for Emergence |
|---|---|
| Hire consultants per decision | Doesn't compound; no institutional memory; slow; expensive per-call. |
| Static framework (McKinsey/BETSOL-style checklist) | Humans still do 100% of the research; inconsistent depth; no citations; no portfolio lens. |
| Generic deep-research agent | Researches anything, knows nothing about capability-sourcing structure, TCO, or reuse economics. |
| **This engine** | Encodes the decision logic once, runs the research autonomously, reasons consistently, remembers across the portfolio (Target), and cites every claim. |

## 2. Scope, users, and non-goals

### 2.1 Primary user
**Emergence platform / portfolio engineering team.** Operators who make or review capability decisions across multiple companies. Secondary consumer: a portfolio-company CTO/engineering team who submits a need and reads the resulting strategy.

### 2.2 What it does
- Elicits a structured need-profile through conversation, including a **soft qualitative steer** on what the operator cares about most.
- Researches build-path and buy-path autonomously in parallel, with every claim cited and verified.
- Reasons over **four strategic paths** as analytical lenses over the research.
- **Argues against its own recommendation** (challenger pass) to produce an adversarially-sourced runner-up.
- Produces an advisory strategy: recommendation, runner-up, "wins when" conditions, decisive factors, per-path pros/cons/risks/reversibility, and explicit open questions.

### 2.3 What it explicitly does NOT do (non-goals)
- **Does not make the final decision.** Advisory only. Human owns the call.
- **Does not execute** (no procurement, no provisioning, no contracts).
- **Does not replace** legal/security review — it flags compliance dimensions, it does not clear them.
- **Does not score or rank numerically.** It reasons qualitatively and surfaces decisive factors; it does not manufacture false precision through weighted totals.
- **Does not evaluate "acquire / M&A" as a path.** Acquisition is Emergence's own function and requires diligence the engine cannot responsibly produce from web research. If a sibling already has the capability, that surfaces as reuse (Target), not as an M&A recommendation.
- **Is not a vendor-ranking SEO tool** — it is grounded research, not a Gartner clone.

### 2.4 Case-agnostic by design

The engine encodes **no domain knowledge**. It does not "recognize HIPAA" or special-case any vertical. Intake elicits compliance regime, data sensitivity, and constraints as **general fields**; synthesis reasons over whatever those fields contain. A demonstration necessarily instantiates one example need at runtime — the way you demo a compiler by compiling one program — but the example is **runtime input, never design-time structure.** This is deliberate: a case baked into the design would reframe the engine from *infrastructure* into *a solution to one problem*. It also self-disciplines the design — every mechanism must justify itself in general terms, with no domain-specific cheats smuggled in.

---

## 3. The decision model (the actual IP)

This is the part no off-the-shelf tool has. Everything else is plumbing.

### 3.1 Vendor vs Valor evaluates **four paths**

| Path | Definition | Emergence resonance |
|---|---|---|
| **Build** | Develop in-house from scratch / open-source primitives. | Right when it's core IP or generates proprietary data. |
| **Buy** | License a commercial SaaS / managed product. | Right for commodity, non-differentiating capability. |
| **Buy-then-extend** | License a core platform with a strong API, build the differentiating layer on top. | The dominant modern playbook; usually the real answer. |
| **Adopt-and-self-host** | Take open-source, run and harden it internally. | Cost/control middle path; trades license fees for ops burden. **Often the right answer under data-residency or sensitivity constraints** — self-hosting beats both a raw build and a vendor dependency when data cannot leave the perimeter. |

**Why four, not five.** v1.0 included **acquire** (M&A). It is dropped — everywhere, including the Target. Acquire is the only "path" that isn't a recombination of build/buy evidence: assessing it needs valuation and diligence data that web research cannot responsibly produce, and acquisition is Emergence's *own* core function, not something its decision-engine should opine on. Keeping it would force either invented evidence or a hollow row. The boundary is intentional: the engine should know the edge of its own competence rather than produce a half-built fifth path.

**Why four, not two.** A two-path engine looks naive to an M&A-native, modern-stack audience. Buy-then-extend is the playbook most decisions actually land on; adopt-and-self-host is the path that wins in regulated/sensitive contexts. Showing all four signals you understand the real decision surface.

### 3.2 Paths are lenses, not research targets

The critical design move: **paths are not independent research targets — they are recombinations of two underlying evidence pools.** The engine runs **two research agents**, each producing an evidence *substrate*:

- **BUILD substrate** — industry approaches, OSS primitives, eng-effort estimates, the maintenance/bloat curve, build risks.
- **BUY substrate** — commercial options, pricing (short + long-term + renewal), fit, **API surface and extensibility** (this is what gates buy-then-extend), data-handling/compliance posture, vendor viability.

Every path is spanned by these two pools:

| Path | Evidence it draws on |
|---|---|
| Build | BUILD substrate |
| Buy | BUY substrate |
| Buy-then-extend | BUY (the base platform + its API surface) **+** BUILD (the extension-layer effort) |
| Adopt-and-self-host | BUILD (OSS primitives, ops burden) **+** BUY (the OSS-as-product landscape, support options) |

So the agents own **evidence**; synthesis owns **path framing**. No path requires its own agent, and no path requires invented evidence — buy-then-extend cites buy *and* build claims because that evidence genuinely exists in the pools. This dissolves the v1.0 "five paths, two tracks" gap cleanly: synthesis reasons and cites, which is exactly what it is good at.

### 3.3 The research dimensions (the 14 survive as structure, not scores)

The 14 decision dimensions from v1.0 **are not gone** — they survive as the **research checklist and dossier structure**: the things each track investigates and each path's dossier reports on. They are no longer scored cells summed into weighted totals. You keep the rigor ("we examined reversibility, vendor viability, integration cost…") without the false precision.

| # | Dimension | Question it answers |
|---|---|---|
| 1 | Strategic differentiation / moat | Does owning this build competitive advantage or proprietary data that compounds? |
| 2 | Proprietary-data generation | Does building this *generate* data no competitor can replicate? |
| 3 | Total cost — build | Eng salaries × time, infra, opportunity cost of what those engineers *aren't* building. |
| 4 | Total cost — maintenance (the bloat curve) | What does upkeep cost in year 2, 3, 5 as it accretes features and tech debt? |
| 5 | Total cost — buy (short + long term) | License + integration + per-seat scaling + price-escalation risk at renewal. |
| 6 | Time-to-value | Time to a working capability for each path. |
| 7 | Resource & talent availability | Do we have the engineers/skills, or must we hire? |
| 8 | Reversibility / switching cost | How expensive is it to unwind this decision later? *The dimension most frameworks omit.* |
| 9 | Data ownership / sensitivity / compliance | Where does data live? Regulatory exposure? Vendor data-handling risk? |
| 10 | Customization need vs. availability | How much must it bend to our workflow, and can each path deliver that? |
| 11 | Focus / core-value alignment | Does doing this ourselves distract from the company's core value? |
| 12 | ★ Portfolio reuse & amortization | Can this be built once and shared across N companies? (The Emergence multiplier; Target.) |
| 13 | Vendor viability / lock-in risk | Is the vendor durable? Acquisition/EOL risk? |
| 14 | Integration complexity | Cost to wire into existing (often legacy, underinvested) stacks. |

### 3.4 How the engine prioritizes without weights

v1.0 asked the operator to pre-weight 14 dimensions summing to 1.0 — unverifiable, unnatural, and fragile. Replaced by a two-part mechanism:

- **Soft steer at intake.** The operator says, in conversation, what they care about most ("speed and data control matter more than upfront cost here"). No numbers. A natural sentence, captured as a qualitative field on the profile.
- **Decisive factors in output.** The *engine* reports which 3–5 dimensions actually drove the recommendation, and why. The prioritization work moves from the human (pre-weighting a vector) to the engine (showing its reasoning) — which is both more rigorous and more useful: the human reacts to a surfaced rationale instead of guessing weights up front.

The runner-up's **"wins when" conditions** preserve the *sensitivity* idea qualitatively: "if integration cost matters more than time-to-value, buy-then-extend overtakes build" — without any weight vector to perturb.

---

## 4. System architecture (vision)

### 4.1 The pipeline (four stages, human-gated)

```
   NODE 1             NODE 2                       NODE 3                  NODE 4
┌──────────────┐  ┌──────────────────────────┐  ┌──────────────────┐  ┌──────────────┐
│  INTAKE      │  │   RESEARCH                │  │  SYNTHESIS       │  │   REPORT     │
│  INTAKE      │─▶│  ┌────────┐  ┌─────────┐ │─▶│  + CHALLENGER    │─▶│              │
│              │  │  │ BUILD  │  │  BUY    │ │  │                  │  │              │
│ → profile.md │  │  │ subst. │  │ subst.  │ │  │ → strategy.md    │  │ → report.html│
│  (+ steer)   │  │  └────────┘  └─────────┘ │  │   (rec+runner-up)│  │              │
│ interrupt()  │  │  parallel + verify claims │  │ interrupt()      │  │              │
│   gate-1     │  │                           │  │   gate-3         │  │              │
└──────────────┘  └─────────────┬────────────┘  └──────────────────┘  └──────────────┘
                       interrupt() gate-2
```

Three human gates, implemented as LangGraph `interrupt()` points: confirm the profile before research, review research before synthesis, review strategy before it's final. The graph parks at each and resumes on signal. **Autonomous research, human judgment.**

### 4.2 Stage 1 — Intake → `profile.md` + `profile.json`

A conversational agent that elicits and structures: the **need** (capability, business context, problem); the **intent / core-value test** (near the moat or peripheral?); **resources** (eng headcount, skills, budget, runway); **constraints** (compliance regime, data sensitivity, existing stack, timeline hard-stops); **customization needs**; and the **soft qualitative steer** (what matters most, in the operator's words).

Because the engine is **case-agnostic**, intake carries the system's hardest prompt: it must elicit the right dimensions for a domain it knows nothing about in advance, asking good follow-ups across arbitrary verticals. The *machinery* stays simple (validate required fields present); the *intelligence* lives in the prompt.

> Build complexity: **LOW–MEDIUM.** A well-prompted single agent with a light schema. The case-agnostic generality raises it above v1.0's "LOW." MVP-critical.

### 4.3 Stage 2 — Research (two substrates)

Two independently-scoped research agents produce the two evidence pools (§3.2). Each emits a cited markdown doc plus a machine sidecar of **claims**. **Every non-trivial claim carries a resolvable source and is independently verified** (see §5). Uncited or unsupported claims are dropped or flagged, never asserted.

> Build complexity: **MEDIUM.** This is the engine's center of gravity. A research primitive does the heavy lifting; the *scoping prompts* — what each track looks for — are the IP. MVP-critical; BUILD and BUY run in parallel as separate LangGraph branches.

### 4.4 Stage 3 — Synthesis + challenger → `strategy.md`

Takes `profile.json` + both research pools and:
- Reasons over the **four paths** as lenses (§3.2), drawing cited evidence from the relevant pool(s).
- Produces a **recommendation** with a 2–3 sentence thesis.
- Runs a **challenger pass**: handed the *need profile*, the recommendation, *and the evidence pools*, it makes the strongest **cited** case for a different path, then resolves to one of three recorded states. **Mounted** — a distinct, grounded counter that clears the same pool/gate parity synthesis does, shown as a **first-class counter-recommendation** with profile-grounded "wins when" conditions (convergence with synthesis' own second-best is noted, not double-rendered). **Concurred** — it returned the recommended path because it could not beat it; that agreement is itself signal (earned confidence) and is surfaced, with the runner-up falling back to synthesis' own. **Degraded** — invalid/ungrounded output never fails the stage, but the reason is recorded and rendered (visible, not silent).
- Reports **decisive factors** (§3.4) and **open questions / what we couldn't determine** (explicit gaps, not smoothed over).
- Validates that every cited claim id resolves to verified evidence before writing `strategy.md`; bad citations fail loudly rather than being cleaned up. Dossier citations are bound to individual bullets, not only to a dossier-level citation list.
- Enforces the buy-then-extend gate: that path needs BUY-side API/extensibility evidence, not just a vague vendor-fit claim.

> Build complexity: **MEDIUM.** The challenger is one extra LLM call over the same pools; it is **degradable** to a single-pass synthesis if the sprint runs short. MVP-critical (challenger degradable).

### 4.5 Stage 4 — Report + human review → `report.html`

Renders the strategy into a lightweight, self-contained HTML report (inline CSS/JS, opens offline): recommendation up top, per-path dossiers with pros/cons/risks/reversibility, the runner-up and its conditions, decisive factors, expandable evidence with live source links, flagged claims (partial-evidence, stale-cost, conflicting-price) visually distinct, and an open-questions panel. Deterministic renderer — no model call, so it is instant and reproducible.

> Build complexity: **LOW–MEDIUM.** Markdown alone is demoable; the HTML is polish.

### 4.6 Portfolio memory (cross-cutting, Target — stubbed in MVP)

A store of past decisions, each company's existing capabilities, reusable assets, and vendor history, feeding every stage — so the engine can say *"a sibling already built plate-recognition valuation; reuse rather than rebuild,"* or *"three companies licensed the same vector DB; consolidate the contract."* **Out of the MVP** (a stub interface only); the seeded, then learning, service is detailed in *Target Architecture* §B7. It is the highest-leverage *narrative* component and the compounding asset, but it is not on the critical path to a working demo.

---

## 5. Grounding & trust — the `grounded_claim` discipline

Grounding is the engine's core trust claim, so it is **one unified capability**, not a convention smeared across stages. Every factual assertion anywhere in the system — both research agents, the challenger's counter-claims, and synthesis where it asserts — passes through it.

**The `Claim` object:** an atomic, checkable assertion bound to **≥1 source** (URL, title, accessed-date, and a *locator* into the source content), tagged with its research dimension and its track (provenance), and carrying a verification **status** the author cannot set.

**Three operations, and the author can never bless its own claim:**
- **`assert`** — creates a claim; *rejects if it has no source.* An unsourced claim is unconstructable, not merely discouraged. Authors may only cite URLs already in the run's **source cache** (the closed evidence pool).
- **`verify`** — a structurally separate pass that resolves the locator against the **cached source content** and independently judges `SUPPORTED | PARTIAL | UNSUPPORTED`. It reads the bytes itself; it never trusts the author's summary. (A governance-rails pattern in miniature — the thing that *produces* an artifact is never the thing that *clears* it.)
- **`filter`** — applies policy: `UNSUPPORTED` → dropped (logged for the gap view); `PARTIAL` → kept but **visibly flagged** in the report; `SUPPORTED` → flows to synthesis.

**Source caching.** Each source is fetched **once** and its *content* cached per run. Verification re-reads the cached bytes — same network cost as one fetch, no verify-time flakiness, and the cache *is* the closed evidence pool. This makes within-run re-runs reproducible (verify and rescore read frozen bytes, not the live web).

This single discipline is also the **MVP→Target seam**: the MVP runs grounding **post-hoc** (assert freely, then verify+filter); the Target makes `assert` **structural** (the model cannot emit outside the retrieved set) and `verify` a **hard gate**. Same object, same three operations — the upgrade is a strategy swap behind the interface, not a rewrite. (*Target Architecture* §B5.)

---

## 6. Engine rules (governance — the constitution)

Stated so the human trusts the output.

1. **Quality over cost.** Cost never silently overrides a higher-quality/lower-risk path. Where cost drives the call, it is named as a decisive factor, not hidden.
2. **Every claim cited and verified.** Grounding is mandatory and independently checked. No hallucinated vendors, prices, or benchmarks.
3. **Advisory, never deciding.** The engine recommends; the human decides. Hard gate.
4. **Show the work.** Every conclusion traces to cited, verified evidence. The dossier is auditable end to end.
5. **Surface conflicts, don't hide them.** When sources disagree (e.g. on pricing), the engine shows the disagreement and both sources rather than picking silently.
6. **Reversibility is always assessed.** No recommendation ships without a switching-cost assessment.
7. **Argue against yourself.** No recommendation ships without a challenger pass attempting the strongest cited case for an alternative.
8. **Portfolio lens (Target).** Every decision checks "did a sibling already solve this?" before recommending a fresh build or buy.

---

## 7. The Vendor vs Valor decision on the engine itself

Applying the engine's own logic (the strongest demonstration that the framework works):

- **Generic deep-research capability** → **adopt / buy.** Open-source deep-research agents and orchestration frameworks (LangGraph and its ecosystem) are mature, MCP-native, benchmarked, commoditized. Rebuilding this is wasted capital. *Verdict: adopt — LangGraph for orchestration, a hosted model API for inference.*
- **Domain logic, dual-track scoping, four-path reasoning, the `grounded_claim` discipline, the challenger, the portfolio-reuse lens** → **build.** This is the differentiating IP. No vendor has it. It generates a proprietary asset (portfolio decision memory) that compounds. *Verdict: build.*
- **Net path: buy-then-extend** — adopt the orchestration + model primitives, build the differentiating layer on top. Exactly the path the engine is designed to surface, and the path modern stacks converge on. The narrative writes itself.

---

## 8. The reusable layer — two skills + one config

The orchestration is commodity; the IP is the prompts, the rubric structure, and **two reusable skills** that the whole pipeline composes from. (v1.0 imagined three skills; on the qualitative redesign the third — a numeric `scoring_kernel` — dissolved entirely, because there are no scores to validate or sum. Abstraction without multiple call-sites is ceremony; what survived earned its place.)

- **`grounded_claim`** (§5) — the `Claim` object + `assert` / `verify` / `filter`. Invoked from both research agents, the challenger, and synthesis. The trust guarantee.
- **`schema_stage`** — a higher-order wrapper for every stage: `run(stage, inputs, prompt, output_contract, render)` does load-inputs → call-LLM-with-prompt → validate-output → persist (`.json` + generated `.md` + manifest update). Every stage collapses to a declaration (inputs, prompt, output shape, renderer); adding a stage is "write a prompt + an output shape," not "write plumbing." In the qualitative world `output_contract` validates **structural presence + grounding** (required sections exist, claims resolve to verified `Claim`s), not numeric ranges. This is also the Target's service boundary, drawn early for free (*Target Architecture* §B2).
- **Config, not a skill: `/rubric/paths.json`** — the path→evidence-pool mapping (§3.2). Repurposed from v1.0's per-path *scoring guidance* to *which pools/dimensions feed each path*. Single call-site (synthesis), so it stays config, validated inline — not promoted to skill-hood.

The old "separate judgment from mechanism" principle survives, distributed: the mechanical `verify` gate in `grounded_claim` + the mechanical path→pool mapping synthesis must respect. More robust than one kernel you could forget to call.

---

## 9. Build plan — carving the 1–2 day MVP

The design is the full vision; the MVP is the credible slice you demo. (Detailed, dependency-sequenced build order lives in the *MVP HLD & Build Specification* §8.)

### 9.1 MVP (must-haves for the demo)
- **Stage 1 intake** → `profile.md` + soft steer (LOW–MEDIUM).
- **The two skills** (`grounded_claim`, `schema_stage`) as real boundaries (MEDIUM) — the spine everything composes from.
- **Stage 2 research**, both substrates in parallel, real web research, every claim cited **and verified** (MEDIUM).
- **Stage 3 synthesis + challenger** → `strategy.md`: four-path reasoning, recommendation, runner-up, decisive factors, open questions (MEDIUM; challenger degradable to single-pass).
- **One end-to-end worked run**, live, on a runtime-supplied example need.

### 9.2 Fast-follow (if time remains)
- **Stage 4 HTML report** with dossiers + live source links + flagged claims.
- **Engine-regression harness** (§ below) — degradable to fully absent.
- **Deeper intra-track fan-out** of vendor/OSS/cost/compliance sub-questions.

### 9.3 Explicitly deferred (name them; don't build)
- Portfolio memory as a real service/DB (stub interface only in MVP).
- Auth, multi-user, persistence beyond files.
- Procurement/execution integrations.
- Numeric confidence, score calibration, full sensitivity sweep (all Target — the engine is qualitative in MVP).
- Structural grounding at emission (MVP is post-hoc verify; structural is Target).

### 9.4 Engine self-evaluation (good-to-have in MVP, degradable to absent)

Two kinds of eval exist; only one is a component:
- **Per-run output quality** is *not a separate component* — it is the emergent sum of `grounded_claim` (claims verified, unsupported dropped), `schema_stage` (sections present, claims resolve), and the challenger (adversarial completeness). Nothing to build.
- **Engine-regression harness** (good-to-have, degradable): a golden-fixture harness that pins the **deterministic skeleton** and tolerance-checks the **judgment**. It asserts: (a) deterministic artifacts hold — path→pool mapping respected, all dossier sections present, all referenced claims resolve to SUPPORTED/PARTIAL; (b) **stability** — re-run synthesis over the *same cached pool* N times; the recommended path must not flip (a flip over fixed evidence is a real instability bug); (c) **leakage** — zero UNSUPPORTED claims reach the deliverable. It snapshots neither the raw prose (it varies) nor the live web (non-deterministic). This is *how you test a non-deterministic system*: pin the skeleton, tolerance-check the judgment.

### 9.5 Suggested repo shape
```
vendor-vs-valor/
  README.md
  DESIGN.md                  ← this document
  /skills
    grounded_claim/          ← Claim object + assert/verify/filter (the trust layer)
    schema_stage/            ← load→LLM→validate→persist wrapper
  /agents
    intake.md                ← intake prompt + profile schema + soft-steer capture
    research_query_plan.md   ← search planner: profile+dimensions → diversified queries
    research_build.md        ← build-substrate scoping prompt
    research_buy.md          ← buy-substrate scoping prompt (incl. API/extensibility)
    synthesis.md             ← four-path reasoning prompt
    challenger.md            ← adversarial path-advocate prompt
  /rubric
    metrics.json             ← the 14 research dimensions + what each track looks for
    paths.json               ← path→evidence-pool mapping (config, not scores)
  /eval
    fixtures/                ← golden profiles + cached pools for regression
    regression.py            ← skeleton/stability/leakage assertions
  /runs
    <runtime-need>/...       ← per-run artifacts (profile, research, strategy, report) + source cache
  graph.(py)                 ← LangGraph graph: nodes + interrupt() gates + checkpointer + per-node hash guard
```

---

## 10. Foundation choice — decided, behind interfaces, reversibly

Two independent choices: **orchestration substrate** and **model provider**. Both are made, and both sit behind thin interfaces so they stay reversible — the engine practicing the reversibility it preaches.

### 10.1 Orchestration → LangGraph

| Candidate | Pro | Con |
|---|---|---|
| **LangGraph** *(chosen)* | Native `interrupt()` human-gates + checkpointer-backed pause/resume map exactly onto the three-gate pipeline; "edit-the-checkpoint-and-resume" matches the gate-3 soft-steer-edit flow; the MVP→Target durability upgrade is a checkpointer swap (SQLite → Postgres), not a rewrite; familiar. | Dependency surface; the "node re-enters from the top on resume" footgun must be designed around (defused by idempotent, hash-guarded node bodies). |
| Hand-rolled orchestration (model API + custom driver) | Leanest; no framework dependency; full control. | Re-implements pause/resume/checkpointing the framework already provides and has hardened; the Target durability story becomes a rewrite, not a config swap. |
| deepagents-style (plan→delegate→synthesize) | Clean sub-agent isolation for the two-substrate pattern. | Younger; thinner guarantees; still need the gate/resume layer. |

**Why LangGraph wins here specifically:** the engine's hard parts are the *prompts, the four-path reasoning, and the `grounded_claim` discipline* — none of which a framework provides. The *commodity* part is sequencing four nodes with three human pauses and resumable state, which is **precisely** what LangGraph's `interrupt()` + checkpointer give natively. So the framework absorbs the commodity work and stays out of the IP. And it makes the *Target Architecture* §B3 migration — file-state MVP → durable production engine — a checkpointer configuration change rather than a re-architecture, which is the cleanest possible MVP→Target seam.

### 10.2 Model → Gemini (default), provider-swappable

| Provider | Fit for this workload |
|---|---|
| **Gemini** *(chosen default)* | Cheapest of the frontier-tier on the input-heavy research/synthesis workload; largest context window (headroom to feed both research pools + profile + rubric into synthesis without aggressive truncation); free dev tier (Flash) cuts sprint iteration cost. Flash as the workhorse, Pro for the synthesis node where context/reasoning headroom helps most. |
| Claude / GPT | Comparable or stronger reasoning, but more expensive per token for no capability gain *on this structured-research task*; kept as drop-in swaps behind the provider interface for any stage that later proves to need them. |

The model sits behind a provider placeholder, so per-stage routing (e.g. a different model for the challenger to reduce self-agreement, or a stronger model for synthesis) is a config change — the seed of the Target's provider-routing layer (*Target Architecture* §B4).

**The decision criterion, stated honestly:** minimize reversibility cost and let the framework own only the commodity. Both choices are reversible by construction (interfaces), so this is "decided, but not married" — the correct senior posture, and itself a small demonstration of the engine's own logic applied to its own construction.

*End of Design & Decision Model. The MVP HLD & Build Specification is the buildable slice; the Target Architecture is the production arc every MVP shortcut grows into.*
