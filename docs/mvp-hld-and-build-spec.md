# MVP High-Level Design & Build Specification
### Portfolio Decision Engine (Buy-vs-Build Research Engine)

**What this document is.** The **MVP**, described at **HLD altitude** with **targeted LLD** for the contracts whose precision is load-bearing. It is the buildable slice — what ships in a 1–2 day Claude Code-assisted build and runs live in the interview. The vision and rationale live in *Design & Decision Model*; the production-scale design lives in *Target Architecture*. Every shortcut here names the production answer it points to: **`→ Target §x`**.

**Substrate & model (decided):** **LangGraph** for orchestration — the pipeline is a graph, the three human gates are `interrupt()` points, and resumability is the checkpointer; this is chosen because it natively provides the gate + resume semantics this engine needs and because it makes the MVP→Target durability migration a checkpointer swap rather than a rewrite (**`→ Target §B3`**). **Gemini** (Flash as the workhorse, Pro available for synthesis where context/reasoning headroom helps) as the default model, **behind a provider interface** so a per-stage swap to Claude or GPT is a config change, not a refactor. Both are deliberately reversible choices. Model placeholders are used throughout so the provider is never hard-coded into a stage.

**Altitude discipline (so this doc doesn't sprawl):** HLD is the spine — for each stage and skill, its internal structure, data flow, and interfaces. LLD precision is spent **only** where ambiguity would cause a bug or where the contract *is* the IP: the `Claim` object, the `profile` contract, the two skills' operation signatures, the idempotency hash, and the cost-grounding rules. Everything else (the CLI surface, the HTML renderer) is obvious from its HLD and is not over-specified.

**Locked decisions driving this spec:**
- Output is **qualitative**: recommendation + runner-up + "wins when" conditions + per-path dossiers + engine-surfaced decisive factors + open questions. **No weights, no scores, no numeric confidence.** (Confidence returns in *Target*.)
- Paths are **lenses over two evidence pools**, not research targets. Two research agents (BUILD, BUY); four paths framed by synthesis.
- **Four paths**: build, buy, buy-then-extend, adopt-and-self-host. **Acquire is dropped** everywhere.
- **Case-agnostic**: no domain baked in. The demo scenario is runtime input, not design-time structure.
- Grounding is **post-hoc verify** (the `grounded_claim` skill), with the structural upgrade deferred. **`→ Target §B5`**.
- A **challenger** pass produces the runner-up; **degradable** to single-pass synthesis if the clock runs out.
- Reusable layer = **two skills** (`grounded_claim`, `schema_stage`) + **one config** (`paths.json`). No scoring kernel.
- Orchestration: **LangGraph graph** — gated stage flow with parallel BUILD/BUY research branches, `interrupt()` gates, checkpointer-backed resume; MVP uses an in-memory/SQLite checkpointer. **`→ Target §B3`**.
- Portfolio memory: **out of MVP** (stub interface only). **`→ Target §B7`**.
- Report: **lightweight self-contained HTML** in MVP.

---

## 1. MVP goal & success criteria

**Goal:** a command-line research engine that takes a capability need supplied at runtime, interviews the operator, autonomously researches build and buy paths with live verified citations, reasons over four strategic paths, argues against its own answer, and emits a cited `strategy.md` + a self-contained `report.html` — end to end, live, for *any* need the operator describes.

**Done = all true:**
1. `intake` produces a schema-valid `profile.json` capturing need, constraints, and the operator's **soft qualitative steer** — for an arbitrary domain, with no hardcoded domain knowledge.
2. Both research substrates run and emit `build-research.{md,json}` / `buy-research.{md,json}` where **every non-trivial claim is a `Claim` with ≥1 resolvable, cached source**.
3. The **verify** pass independently re-reads each claim's cached source and labels it `SUPPORTED | PARTIAL | UNSUPPORTED`; `filter` drops the unsupported and flags the partial before synthesis.
4. `synthesize` emits `strategy.md` with: a **recommendation** + thesis; per-path **dossiers** (pros/cons/risks/reversibility) for the four paths, each factual bullet cited; a **runner-up** with "wins when" conditions; **decisive factors**; and **open questions**.
5. The **challenger** pass produces the runner-up by making the strongest *cited* case for an alternative path over the same evidence pools (degradable).
6. `report.html` renders standalone (no server, no external assets) with dossiers, expandable cited evidence, and visually distinct **flags** (partial-evidence, stale-cost, conflicting-price).
7. The whole run is **resumable**: the graph parks at each gate and resumes on signal; a node whose inputs are unchanged reuses its artifact; editing the profile re-runs only what depends on it.

**Explicit non-goals for MVP:** no UI server, no auth, no application database (the SQLite checkpointer is LangGraph's, not a data store we model against), no intra-track fan-out beyond BUILD/BUY parallelism, no structural-grounding-at-emission, no portfolio-memory seed, no numeric scoring/confidence/sensitivity, no procurement actions.

---

## 2. Architecture overview (thin — the MVP's complexity is in the HLD, not here)

A **LangGraph pipeline over a file-backed artifact store.** Each stage is a graph node: `(input artifacts) → (output artifacts)` via the `schema_stage` skill, with the three human gates implemented as `interrupt()` points. **LangGraph's checkpointer holds run state and drives resume**; the stage *artifacts* (markdown + JSON sidecars + the source cache) still live on disk as the durable, human-inspectable record — so you keep "open any intermediate in a text editor" debuggability while getting native pause/resume. MVP uses an in-memory or SQLite checkpointer; the Target swaps it for Postgres with no node changes (**`→ Target §B3`**). That is the entire MVP architecture; the interesting design is per-stage (§5) and per-skill (§3).

```
 $ pde run --need "<free-text capability need>"        (invokes the LangGraph graph)
        │
        ▼
┌──────────────────┐  interrupt()  ┌──────────────────────────────┐
│ NODE: INTAKE     │──gate-1──────▶│ human reads/edits profile.md │
│  intake_agent    │  resume(cmd)  │ resume with approve/edit      │
│  → profile.{md,json}◀────────────└──────────────────────────────┘
└──────────────────┘
        │ (Command(resume=…))
        ▼
┌─────────────────────────────────────────────────────────┐
│ NODE: RESEARCH  (BUILD and BUY run in parallel)           │
│   research_agent(track=BUILD) → build-research.{md,json}  │
│   research_agent(track=BUY)   → buy-research.{md,json}    │
│   verify + filter (per track) ← grounded_claim skill      │
└─────────────────────────────────────────────────────────┘
        │  interrupt() gate-2: human reviews research, resume
        ▼
┌─────────────────────────────────────────────────────────┐
│ NODE: SYNTHESIS + CHALLENGER                             │
│   synthesize (LLM, four-path lenses) → recommendation    │
│   challenger (LLM, cited counter-case) → runner-up        │
│   assemble → strategy.md                                  │
└─────────────────────────────────────────────────────────┘
        │  interrupt() gate-3: human reviews strategy, resume
        ▼
┌──────────────────┐
│ NODE: REPORT     │ → report.html  (standalone, deterministic)
└──────────────────┘
```

**Why this shape for an MVP:** the gates and resume are native (`interrupt()` + checkpointer) rather than hand-rolled; every intermediate artifact is still a file you can open; the run is resumable across days without holding a process; and it is demo-safe offline (the source cache replays if the room's wifi dies). **One LangGraph footgun to design around:** on resume, a node re-enters **from the top of its function body**, so any pre-`interrupt()` work in a node re-executes. Keep pre-gate side effects idempotent or isolate them in their own nodes (the `schema_stage` wrapper already makes node bodies idempotent — it writes deterministic artifacts keyed by input hash, §3.2/§4).

---

## 3. The reusable layer — two skills (LLD-level, because the contracts are the IP)

The orchestration is commodity; these two skills are the spine everything composes from. They are spec'd at LLD precision because their contracts are load-bearing.

### 3.1 `grounded_claim` — the trust layer

Owns the entire lifecycle of a grounded claim: its structure, its source-binding rule, and its verification. Invoked from **both research agents, the challenger, and synthesis** wherever a factual assertion is made.

**The `Claim` object (LLD):**
```json
{
  "id": "c0a1f3",                  // content-addressed: hash(text + sorted(source_urls))
  "text": "Vendor X exposes a documented REST API for custom extensions.",
  "sources": [
    {
      "url": "https://…",
      "title": "…",
      "accessed_date": "2026-06-13",
      "source_date": "2025-11-02",  // publish/update date if detectable; null otherwise
      "locator": {"type": "char_span", "start": 4120, "end": 4290},  // pointer into CACHED content
      "display_quote": "documented REST API"   // <15 words, for the report only
    }
  ],
  "dimension": "m10_customization",  // which research dimension this feeds (the 14 survive as tags)
  "track": "BUY",                    // provenance: which evidence pool
  "cost_tagged": false,              // true for claims feeding cost dimensions (stricter rules, §3.1.3)
  "status": "UNVERIFIED"             // UNVERIFIED → SUPPORTED | PARTIAL | UNSUPPORTED  (set by verify ONLY)
}
```

**Three operations (LLD signatures):**
```python
assert_claim(text, sources, dimension, track) -> Claim
    # Creates a Claim with status=UNVERIFIED.
    # REJECTS if sources is empty  → an unsourced claim is unconstructable, not discouraged.
    # REJECTS if any source.url is not already in the run's source cache (closed evidence pool).
    # For cost_tagged claims: REJECTS if any source lacks source_date (§3.1.3 mitigation 1).

verify(claim) -> Claim
    # Structurally separate from the author. Loads CACHED content for each source.url,
    # resolves the locator against that content, and independently judges:
    #   SUPPORTED  — the cited span supports the claim text
    #   PARTIAL    — related but incomplete / weaker than asserted
    #   UNSUPPORTED— the source does not support the claim
    # Reads the bytes itself; NEVER trusts the author's display_quote or summary.
    # The author can never set status; only verify can.

filter(claims, policy) -> (kept, dropped)
    # UNSUPPORTED → dropped (logged to dropped[] for the gap/open-questions view)
    # PARTIAL     → kept, marked flag="partial_evidence" (rendered visually distinct)
    # SUPPORTED   → kept, flows to synthesis
    # Additional flags applied here: "stale_cost" (§3.1.3 mitigation 2),
    #                                 "price_conflict" (§3.1.3 mitigation 3)
```

**3.1.1 Source caching (the mechanism that makes verify cheap and demo-safe).**
Each source is fetched **once**, at research time, and its *content* is cached per run at `sources/<sha256(url)>.{content,meta}`. `verify` re-reads the **cached bytes** — same network cost as one fetch, no verify-time flakiness, deterministic within a run. The cache *is* the closed evidence pool: `assert_claim` can only cite URLs already in it. This delivers most of structural grounding as a side effect, cheaply. **`→ Target §B5`** makes binding structural at emission.

**3.1.2 Atomicity.** Claims must be one checkable fact. MVP enforces this by **prompt instruction** and accepts the occasional compound claim. **`→ Target §B5`** adds a decomposition step.

**3.1.3 Cost-grounding rules (LLD — the four D10 mitigations).** Cost is the flakiest research dimension. `cost_tagged` claims (those feeding dimensions 3/4/5) carry stricter rules:
1. **Dated source required** — `assert_claim` rejects a cost-tagged claim whose sources lack `source_date`.
2. **Staleness flag** — `filter` marks `stale_cost` when `source_date` is **> 12 months** before `accessed_date`. Rendered inline: *"~$2k/mo (source dated 2024; verify current pricing)."* Flat 12-month threshold; no per-dimension thresholds (handled in prompts).
3. **Conflict surfacing** — when two cost claims for the same path/vendor disagree **materially** (LLM-judged in synthesis, not a coded epsilon), both are presented as a **range with both sources**: *"reported between ~$2k–$3.5k/mo [a][b]."* Never silently pick one. (Engine Rule #5.)
4. **Gated pricing as a finding** — when cost research returns no public price, the dossier states it explicitly: *"pricing not publicly listed; gated behind sales contact."* This is intelligence, not a gap to smooth over. (Replaces any neutral-midpoint inflation.)

MVP implementation note: synthesis conservatively flags obvious numeric `price_conflict` cases when cost-tagged claims in the same track/dimension/source-host disagree materially. It does not attempt full vendor normalization across arbitrary domains.

**MVP→Target seam:** post-hoc here (assert freely → verify → filter); structural + hard gate in *Target*. Same object, same three operations — the upgrade is a strategy swap behind the interface.

### 3.2 `schema_stage` — the stage lifecycle wrapper

Every stage repeats the same four steps; this skill does them once.

**Signature (LLD):**
```python
schema_stage.run(
    stage_name,        # "intake" | "research" | "synthesis" | "report"
    inputs,            # list of run-dir files to load
    prompt,            # the stage's instructions (the IP, from /agents)
    output_contract,   # validation spec: required fields/sections + grounding checks (NOT numeric ranges)
    render,            # json -> markdown function for the .md sidecar
    run_dir
) -> {"json": ..., "md": ..., "run_json_updated": True}
    # Steps: load inputs → call LLM with prompt → validate output against output_contract
    #        → persist .json (+ generated .md) → update run.json (status, recorded_hash)
```

**`output_contract` in the qualitative world validates structural presence + grounding, not numbers:**
- required fields/sections present and non-empty;
- enums in range (e.g. `intent ∈ {core, adjacent, enabling}`);
- every factual assertion resolves to a verified `Claim` (SUPPORTED or PARTIAL). Connective prose ("therefore buy-then-extend looks favorable") is glue, not a factual assertion, and is **not** required to cite — the engine grounds facts, not conjunctions.

**Render direction differs by stage (both wrapped by the same skill):**
- intake / research: **json is source-of-truth**, md generated from it (so prose and evidence never drift).
- synthesis: **md *is* the deliverable** (prose-heavy); json is a structural sidecar (section manifest + referenced claim-ids) for the renderer to consume.

**Why this is the layer optimization:** adding a stage becomes "write a prompt + an output shape," not "write plumbing." It also *is* the Target's service boundary, drawn early — the MVP `schema_stage.run()` call and the Target network service share an interface. **`→ Target §B2`**.

### 3.3 Config, not a skill: `/rubric/paths.json`

The path→evidence-pool mapping (which pools/dimensions feed each of the four paths). Single call-site (synthesis), so it stays **config validated inline**, not a skill — promoting it would be abstraction without reuse.
```json
{
  "build":              {"pools": ["BUILD"]},
  "buy":                {"pools": ["BUY"]},
  "buy_then_extend":    {"pools": ["BUY", "BUILD"], "gate": "buy.api_surface present"},
  "adopt_self_host":    {"pools": ["BUILD", "BUY"], "note": "favored under data-residency/sensitivity constraints"}
}
```

---

## 4. The run directory & resumption (LLD — the durability model)

Two layers cooperate: **LangGraph's checkpointer** holds graph execution state (which node is next, the channel values) and drives pause/resume across `interrupt()` gates; the **run directory** holds the durable, human-inspectable artifacts (markdown, JSON sidecars, the source cache). The checkpointer answers *"where is the graph?"*; the directory answers *"what did each stage produce?"* and is the audit/debug surface. MVP uses an in-memory or SQLite checkpointer; **`→ Target §B3`** swaps it for Postgres (no node changes) and adds an event log.

```
runs/<run-id>/
  run.json              # artifact manifest: per-stage status + recorded input-hash (the skip guard, below)
  profile.{md,json}     # need + constraints + soft steer (validated)
  sources/<hash>.{content,meta}   # cached source content (the closed evidence pool)
  build-research.{md,json}        # BUILD substrate: Claim[]  (md generated from json)
  buy-research.{md,json}          # BUY substrate: Claim[]
  verify-report.json    # what verify labeled; what filter dropped/flagged
  strategy.{md,json}    # the deliverable (md is truth; json indexes sections + claim-ids)
  report.html           # standalone report
```
*(LangGraph's checkpointer stores graph execution state separately — thread/checkpoint records, not shown here. `run.json` is the artifact-level manifest the nodes read to decide whether work can be skipped.)*

**Resumption & idempotency (LLD — the D9 fix).** Resumption *across gates* is LangGraph's checkpointer: the graph parks at an `interrupt()` and resumes on a `Command(resume=…)` signal. Avoiding *redundant recomputation* is a node-level guard layered on top: each node, before doing LLM work, computes its input-hash and compares to the value recorded in `run.json`. A node **skips its body and reuses the existing artifact** iff:
```
stage.status == "done"  AND  stage.recorded_hash == current_hash(stage)

where current_hash(stage) = hash(
    input_files(stage)        # upstream artifacts it reads
  + prompt_file(stage)        # editing the prompt invalidates the stage
  + rubric_files              # metrics.json + paths.json
  + model_id                  # same inputs, different model ⇒ different output
  + engine_version            # MANUAL string, bumped on logic changes (MVP limitation; → Target code-hash)
)
```
This guard is what makes node bodies **idempotent** — which is also exactly what defuses the LangGraph "re-enter from the top on resume" footgun (§2): a node that re-executes after an interrupt recomputes the same hash, finds its artifact present, and no-ops instead of re-calling the LLM. **Consequences that fall out for free:** editing the profile's soft steer at gate 3 changes synthesis's input-hash → synthesis re-runs on resume, while research (unchanged inputs) is skipped — so **no special "rescore"/"redo" commands are needed**; the guard *is* the general rule. Per-track re-run works because each track's artifact is hashed independently.

**Reproducibility boundary (state this in the room — it's a strength).** The skip guarantee covers everything *except live web results*, which are inherently non-deterministic. So the precise claim is: **"given the same cached evidence pool, the engine produces the same assessment"** — within-run reproducibility, guaranteed by the source cache. Cross-run freshness is *intentional* (you want current data), bounded by the staleness flags, not by the hash. **`→ Target §B6`** adds cross-run pinning via cached corpora.

---

## 5. Stage specs (HLD)

### 5.1 Stage 1 — Intake → `profile.{md,json}`

**Type:** single LLM agent, conversational, schema-terminated. **Complexity: LOW–MEDIUM** (the case-agnostic generality is in the prompt).

**Behavior:** a structured interview covering need, intent/core-value test, resources, constraints (compliance regime, data sensitivity, existing stack, timeline), customization needs, and the **soft qualitative steer** (what matters most, in the operator's words — *no numbers*). Because the engine is case-agnostic, the agent asks good follow-ups for a domain it knows nothing about in advance; it does **not** recognize or special-case any vertical.

**The contract it emits — `profile.json` (LLD; validated by code before Stage 2):**
```json
{
  "run_id": "…",
  "need": {"capability": "…", "business_context": "…", "problem": "…"},
  "intent": {"core_value_proximity": "core | adjacent | enabling", "rationale": "…"},
  "resources": {"eng_headcount": 0, "relevant_skills": ["…"],
                "budget_note": "free-text, no required numbers", "runway_note": "…"},
  "constraints": {"compliance": ["…"], "data_sensitivity": "…",
                  "existing_stack": ["…"], "timeline_hard_stop": "…"},
  "customization_need": "low | medium | high",
  "soft_steer": "free-text: what the operator says matters most"   // replaces the weight vector
}
```
**Validation (code, not LLM):** required `need` fields non-empty; enums in range; `soft_steer` present. No weights, nothing sums to anything. Fail → halt with a precise error.

**Gate 1:** the node hits `interrupt()` surfacing `profile.md` for review; the graph parks. Human edits the file if needed and resumes with `Command(resume="approve")`.

### 5.2 Stage 2 — Research substrates → `*-research.{md,json}`

**Type:** two parallel invocations of one parameterized research agent (`track ∈ {BUILD, BUY}`), each a two-phase **plan → read/reason** flow followed by `verify` + `filter`; a join step assembles the combined `verify-report.json`. **Complexity: MEDIUM — the engine's center of gravity.** (The scoping prompts are the IP and are the build's schedule risk — see §7.)

Each track runs, in one idempotent node:
1. **Plan (Phase A, `agents/research_query_plan.md`).** An LLM call expands the profile + the track's dimensions into `priority_dimensions` (the 4–6 decisive for *this* profile) and a diversified, profile-aware query set (8–12 keyword queries biased toward primary/datable sources). This is a single planning pass — **not** the Target-Architecture intra-track research fan-out (no reflection/re-search loop). Degrades to deterministic fallback queries if the planner is unavailable. The planner sees the same profile fields as the author (see below); it does **not** see `soft_steer`.
2. **Discover.** Domain-diverse search (`max_per_domain` cap) so one SEO listicle/site cannot dominate the pool; fetch + cache full content once.
3. **Read/reason (Phase B, `agents/research_build.md` / `research_buy.md`).** The author grounds atomic `Claim`s in the cached content. The source excerpt given to the author keeps the head plus deterministically pulls **cost/pricing/date windows** forward so deep pricing tables survive truncation. Source-credibility is a *selection* rule in the prompt (prefer primary/datable over listicles) — never an author-set flag, preserving the trust-layer invariant.

**Profile fields research reasons over (and hashes):** `need`, `intent`, `resources`, `constraints`, `customization_need`. **Excluded:** `soft_steer` (synthesis-only, §4) — a gate-3 steer edit must not re-run research. Both prompts ride in the input hash, so editing either invalidates the cache.

**BUILD substrate covers:** industry approaches/best-practices; benchmarks across approaches (OSS options, reference architectures); **live cost analysis** (eng-effort as team-months/FTE-time — *not* how-to tutorials, infra, the maintenance/bloat curve — researched, dated); build risks (talent scarcity, overruns, tech-debt accretion).

**BUY substrate covers:** commercial options; fit vs. the profile; **live pricing** (short + at-scale + renewal, dated); **API surface & extensibility** (this gates buy-then-extend); data-handling/compliance posture; vendor viability.

**Output:** each track emits `Claim[]` via `assert_claim` (sources cached on fetch), then `verify` re-reads cached content and labels, then `filter` drops/flags. The json also carries `priority_dimensions` and per-dimension `coverage` (which dimensions got evidence; an empty *priority* dimension is surfaced as a coverage gap → feeds Gate 2 and synthesis `open_questions`). The `*-research.md` is **generated from** the filtered json so prose and evidence never drift.

**Gate 2:** node `interrupt()` surfaces both research docs + `verify-report.json`; human reviews and resumes with `Command(resume="approve")`.

### 5.3 Stage 3 — Synthesis + challenger → `strategy.{md,json}`

**Type:** two LLM steps (synthesis, then challenger) + deterministic assembly. **Complexity: MEDIUM** (challenger degradable).

**(a) `synthesize` — LLM, four-path lenses.** Reads `profile.json` + both filtered pools + `paths.json`. For each of the four paths, reasons over the **mapped** evidence pool(s) (§3.3) and writes a **dossier**: pros, cons, key risks, **reversibility note** (Engine Rule #6), with every factual bullet carrying its own verified `Claim` ids. Produces the **recommendation** + 2–3 sentence thesis and the **decisive factors** (the 3–5 dimensions that drove it — this is the weight-replacement, §Design 3.4). Surfaces **open questions** for `null`/thin evidence (stated as gaps, never invented).

**(b) `challenger` — LLM, adversarial path-advocate (degradable).** Handed the recommendation **and the evidence pools** (not just the conclusion — otherwise it hallucinates a counter-case), it makes the strongest **cited** case for a *different* path, under the same `grounded_claim` discipline (every counter-claim is a verified `Claim`). Its output becomes the **runner-up** with "wins when" conditions. **Degradation:** if the sprint runs short, the runner-up comes from a single synthesis pass; the challenger is the first thing to drop and the structure is unchanged.

**(c) assemble — CODE.** Validates that the synthesis output has one dossier per canonical path, that runner-up differs from the recommendation, that every cited claim id resolves to the verified evidence pool, that every factual dossier bullet carries claim ids, and that a buy-then-extend recommendation cites BUY-side `m10` API/extensibility evidence. Broken citations or missing gate evidence fail the stage; they are never silently dropped. Then it combines recommendation + dossiers + runner-up + decisive factors + open questions into `strategy.md` (the deliverable) and a `strategy.json` sidecar (section manifest + claim-ids) for the renderer. No new model call.

**Gate 3:** node `interrupt()` surfaces `strategy.md`; the human may edit the profile's soft steer and resume (synthesis re-runs via the input-hash guard, research is skipped — §4), then resume to the report node.

### 5.4 Stage 4 — Report → `report.html`

**Type:** deterministic renderer (CODE; small templating, no LLM). **Complexity: LOW–MEDIUM.**

Single self-contained `.html` (inline CSS/JS, opens offline). Contents: recommendation banner + thesis; the four **per-path dossiers** (pros/cons/risks/reversibility); the **runner-up** + "wins when" conditions; **decisive factors**; expandable evidence with clickable source URLs; **flagged claims** (`partial_evidence`, `stale_cost`, `price_conflict`) visually distinct; an **open-questions** panel; a stubbed portfolio-reuse panel ("MVP: single-need; see roadmap"). Reads only `strategy.json` + the claim sidecars — no model call, so it is instant and reproducible.

---

## 6. The IP artifacts — what actually ships in `/agents`, `/rubric`, `/skills`

These files *are* the differentiator; the orchestration is commodity.

- **`/rubric/metrics.json`** — the 14 research dimensions, each with the question it answers and the per-track "what to look for" list. The research checklist that makes coverage consistent.
- **`/rubric/paths.json`** — the path→evidence-pool mapping (§3.3).
- **`/agents/intake.md`** — interview prompt + `profile.json` schema + soft-steer capture. *Case-agnostic — no domain cues.*
- **`/agents/research_query_plan.md`** — Phase-A search planner (§5.2): profile + dimensions → `priority_dimensions` + diversified, profile-aware query set. Single planning pass, not intra-track fan-out.
- **`/agents/research_build.md`** / **`/agents/research_buy.md`** — per-track scoping prompts (§5.2) + the `assert_claim` contract + citation-mandatory + atomicity + source-credibility-as-selection + dimension-prioritization instruction.
- **`/agents/synthesis.md`** — four-path reasoning + decisive-factors + open-questions prompt.
- **`/agents/challenger.md`** — adversarial path-advocate prompt (sees pools + recommendation; cited counter-case).
- **`/skills/grounded_claim/`** — `Claim` + `assert`/`verify`/`filter` (the reproducibility & trust guarantee).
- **`/skills/schema_stage/`** — the stage lifecycle wrapper.

---

## 7. Failure modes & demo-safety (interview-day reality)

| Failure | MVP handling |
|---|---|
| A `web_search`/fetch fails mid-research | claim-level try/except; the track continues; the missing area is noted as a coverage gap (an open question), not a crash. Already-cached sources persist. |
| A source fetched fine but is unreachable later | irrelevant — `verify` reads the **cache**, not the live web. No re-fetch to fail. |
| Research returns thin/no evidence for a path or dimension | surfaced as an **open question**, never invented. Gated pricing → stated as a finding (§3.1.3.4). |
| LLM emits an uncited or compound claim | `assert_claim` rejects unsourced claims structurally; compound claims accepted in MVP (prompt-mitigated). |
| LLM asserts a claim its source doesn't support | `verify` re-reads cached content, labels `UNSUPPORTED`, `filter` drops it before synthesis. |
| Stale or conflicting pricing | `stale_cost` flag (>12mo) / `price_conflict` range with both sources (§3.1.3). |
| Run interrupted | resume from the checkpointer's last checkpoint; the per-node input-hash guard reuses unchanged artifacts so no completed work repeats. |
| Challenger underperforms / time-boxed | degrade to single-pass synthesis; runner-up still produced; structure unchanged. |
| Live demo network risk | the source cache replays the whole run offline. **Pre-stage one clean run before the interview.** |

---

## 8. Build order for the 1–2 day sprint (dependency-sequenced, honest estimate)

The qualitative pivot *removed* work (no scoring/weights/validation machinery) and *added* some (two real skill boundaries, the challenger, case-agnostic intake). Net is similar hours, redistributed. **The research scoping prompts are the schedule risk** — getting reliably cited, current, on-track claims is the part that eats time; pre-write and pre-test them before sprint day.

1. **`/rubric/metrics.json` + `/rubric/paths.json`** — the spine everything references. ~1–2h.
2. **`grounded_claim` skill** — `Claim`, `assert`/`verify`/`filter`, source cache. The trust core; test it in isolation. ~3–4h.
3. **`schema_stage` skill** + LangGraph graph skeleton (nodes + edges + `interrupt()` gates + checkpointer) + the per-node input-hash guard. Knowing LangGraph already, this is wiring, not learning. ~2–3h.
4. **Stage 1 intake** agent + `profile.json` validator (case-agnostic prompt is the work). ~2h.
5. **Stage 2 research** agent (one parameterized track) + scoping prompts + wire `grounded_claim`; run BUILD and BUY in parallel. ~4–6h *(the long pole — pre-tested prompts shrink this)*
6. **Stage 3 synthesis** (four-path lenses) **+ challenger**. ~3–4h.
7. **Stage 4 HTML renderer.** ~2h.
8. **Engine-regression harness** (good-to-have, degradable): skeleton/stability/leakage assertions on a golden fixture. ~1–2h.
9. **One clean end-to-end run + cache it for demo safety.** ~1h.

Total ≈ **20–26h** of focused work — a tight but feasible 2-day sprint. **Must-demo core:** 1–6. **Polish:** 7. **Narrative-and-safety:** 8–9. If time is short: the heatmap-free markdown strategy alone is demoable (drop 7 to a styled table), the challenger degrades to single-pass (item 6), and the regression harness (item 8) drops entirely — each is an independent switch that doesn't touch the others.

---

*End of MVP HLD & Build Specification. The Target Architecture holds the production-scale design every shortcut here points to.*
