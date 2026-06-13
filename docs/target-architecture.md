# Target Architecture
### Vendor vs Valor — Production Scale

**What this document is.** The **Target** system, described at **architecture altitude** — components, responsibilities, the contracts and boundaries between them, and the cross-cutting concerns (durability, grounding, trust, security, scale). It is deliberately *not* HLD or LLD: you describe a system you are not yet building by its boundaries and contracts, not its wiring. The buildable slice is the *MVP HLD & Build Specification*; the rationale is *Design & Decision Model*. Each section names the **MVP shortcut it replaces**, so the through-line from demo to platform is explicit.

**Design tenets (inherited from the MVP, hardened here):**
1. **Advisory, never deciding** — humans own capital-allocation calls.
2. **Every claim grounded** — and here grounding is *structural*, enforced at emission, not a post-hoc cleanup.
3. **Qualitative, reasoned output** — recommendation + runner-up + decisive factors; numeric **confidence returns** here (it was deferred from the MVP) as a *qualitative-plus-signal*, never a false-precision score.
4. **Argue against yourself** — the challenger becomes a mandatory gate, not an optional pass.
5. **Durable & auditable** — no run is lost; every recommendation is reconstructable forever.
6. **Portfolio-aware by default** — reuse is checked before any fresh build/buy.

---

## B1. System context (C4 level 1)

```
        ┌───────────────────────────────────────────────────────────┐
        │                     Vendor vs Valor                       │
        │                                                           │
 Platform│   ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌─────────┐ │
 team   ─┼──▶│  Intake  │─▶│  Research │─▶│ Synthesis│─▶│Reporting│ │──▶ Decision
 / CTO   │   │  Service │  │  Service  │  │  Service │  │ Service │ │    record +
        │    └──────────┘  └─────┬─────┘  └────┬─────┘  └─────────┘ │    report
        │                       │             │                     │
        │   ┌───────────────────▼─────────────▼──────────────────┐  │
        │   │            Portfolio Memory Service                 │ │
        │   │  decisions · capabilities · vendors · reusable IP   │ │
        │   └─────────────────────────────────────────────────────┘ │
        │   ┌─────────────────────────────────────────────────────┐ │
        │   │            Orchestration Service (durable)          │ │
        │   └─────────────────────────────────────────────────────┘ │
        └────────────┬───────────────────────┬──────────────────────┘
                     │                        │
            ┌────────▼────────┐      ┌────────▼─────────┐
            │  LLM providers  │      │ Research sources │
            │ (routed: Gemini,│      │ web_search · MCP │
            │  Claude, OSS)   │      │ connectors · docs│
            └─────────────────┘      └──────────────────┘
```

External actors: the platform team and portfolio-company engineering leads (initiators/reviewers), LLM providers (routed, not single-vendor), and research sources (web + MCP connectors + licensed corpora). Everything inside the boundary is ours to design.

---

## B2. Service decomposition (C4 level 2) — replaces the MVP's single process

**MVP shortcut:** four pipeline *stages* and two *skills* run in one process; the filesystem is the state store.

**Production:** the four stages become four **independently deployable services**, plus two cross-cutting services. **The MVP's stage contracts become network contracts** — this is the payoff of having drawn the `schema_stage` boundary in the MVP: the unit of deployment already exists.

| Service | Responsibility | MVP origin |
|---|---|---|
| **Intake Service** | Conversational need-profiling; emits the validated `Profile` contract (need, constraints, soft steer). | MVP Stage 1 |
| **Research Service** | Fan-out build/buy research workers; live grounded retrieval; owns the source cache. | MVP Stage 2 |
| **Synthesis Service** | Four-path reasoning, the challenger gate, decisive factors, confidence. | MVP Stage 3 |
| **Reporting Service** | Renders reports + serves the interactive dashboard. | MVP Stage 4 |
| **Portfolio Memory Service** | System of record for decisions, capabilities, vendors, reusable assets. | MVP stub |
| **Orchestration Service** | Durable workflow engine: stage sequencing, gates, retries, checkpoints. | MVP LangGraph graph |

**The two skills survive the split as shared libraries, not services.** `grounded_claim` and `schema_stage` are *contracts and disciplines*, not stateful components — they are vendored into whichever services emit claims (Research, Synthesis) and wrap stages (all four). The trust guarantee travels with the code, not with a network hop.

Why split: research is bursty and parallel (scale horizontally, independent of intake); synthesis is credit-light but correctness-critical (deploy/version separately); portfolio memory is a durable store with its own SLA. The MVP collapses all of this into one process — correct for a demo, wrong for a platform.

---

## B3. Durable orchestration — graduates the MVP's LangGraph checkpointer

**MVP shortcut:** the pipeline already runs as a **LangGraph graph** — nodes, `interrupt()` human gates, and a checkpointer (in-memory or SQLite) — with a per-node input-hash guard avoiding redundant recomputation. The shortcut is only the *checkpointer backend* (SQLite, single process, no concurrency) and the *manual `engine_version`* string.

**Production:** the **same graph, a durable checkpointer backend, and parallelism** — and, if scale demands more than LangGraph's execution model gives, the graph sits behind an orchestration interface so it can be re-hosted on a heavier durable-execution engine (Temporal / Step Functions class) without rewriting node logic. Crucially, the MVP→Target step here is **a checkpointer swap, not a re-architecture** — `SqliteSaver` → `AsyncPostgresSaver` is a configuration change, and the nodes, gates, and graph topology are unchanged. This is the cleanest seam in the whole system, and it is *why* LangGraph was chosen for the MVP. (It also generalizes the Jitterbit iPaaS Bot's checkpointed execution for 50+ node workflows.)

- **Graph nodes = activities; the checkpointer = the durable store.** Each node is idempotent (the hash guard guarantees it) and individually retried with backoff.
- **Checkpoint at sub-node granularity.** The MVP checkpoints at node boundaries; production checkpoints *within* the research fan-out — 30 vendor lookups that die at #27 resume at #27, not from zero. (LangGraph's super-step checkpointing extended to the parallel workers of B4.)
- **Human gates = durable signals.** Already true in the MVP (`interrupt()` parks the graph awaiting a `Command(resume=…)`); production just backs it with the durable checkpointer so a gate can wait days without holding a process. (No semantic change — only the backend.)
- **Event-sourced run log** — every state transition appended; both the resumability substrate and the audit trail (B8). LangGraph's checkpoint history is the seed; production adds a durable, queryable event store.
- **Real code-hashing replaces the MVP's manual `engine_version`** — a node's code version becomes part of its checkpoint/guard identity, so a logic change auto-invalidates downstream rather than relying on a human to bump a string.
- **Config + rubric version pinned per run** — a run records the rubric hash so historical decisions stay interpretable after the rubric evolves.

```
Graph: DecisionRun  (LangGraph; durable checkpointer backend)
  → node: intake                (idempotent via hash guard)
  → interrupt(): gate1
  → parallel:                    (fan-out, B4)
       node: research[BUILD]
       node: research[BUY]
  → node: verify  (per claim, structural — B5)
  → interrupt(): gate2
  → node: synthesize              (four-path lenses)
  → node: challenger-gate         (mandatory — B6)
  → node: confidence              (qualitative-plus-signal — B6)
  → interrupt(): gate3
  → node: render + persist decision record (B7, B8)
```

---

## B4. Research at scale — extends the MVP's parallel tracks

**MVP shortcut:** BUILD and BUY already run concurrently, but each track is still one web_search agent with a per-run source cache.

**Production:**
- **True parallel fan-out.** The two tracks run concurrently; within a track, sub-questions (vendor A, vendor B, OSS option C, cost model, compliance posture) fan out as parallel workers, each with an isolated context window — the deep-research "sub-agent isolation" pattern, preventing context-poisoning across unrelated sub-topics. (The MVP's two evidence pools become many parallel sub-pools that compose into the same two substrates.)
- **Source tiering & trust weighting.** Sources ranked (primary/official > analyst > vendor-marketing > forum). A claim's confidence is a function of its source tier; marketing-only claims are flagged, never decisive. (The MVP records sources flatly; production grades them.)
- **Caching & dedupe across runs.** The MVP's per-run source cache becomes a **cross-run cache with freshness TTL**: a vendor's API/pricing posture researched for one company is reused when another evaluates the same vendor — a portfolio-level efficiency the single-need MVP can't have. This is also what extends the MVP's *within-run* reproducibility into *cross-run* reproducibility (pinned evidence pools), closing the boundary the MVP explicitly left open.
- **MCP connectors** beyond web_search: licensed market-intel, the companies' own contract repositories, internal cost-actuals from past builds (which makes the cost model progressively self-calibrating — see B6).
- **Provider routing** (the APIM-Bot pattern): research workers route across Gemini / Claude / OSS by cost/latency/capability, with token-aware budgeting per run.

---

## B5. Structural grounding — replaces the MVP's post-hoc verify

**MVP shortcut:** research agents `assert_claim` freely (sources must exist and be in the cache), then a separate `verify` pass re-reads cached content and `filter` strips/flags. Weaker because the model can still *generate* an unsupported claim from a real source; we only catch it after.

**Production (structural + verifier gate) — same `Claim` object, same three operations, enforcement point moved:**
- **`assert_claim` becomes structural.** The research worker cannot emit a `Claim` whose `text` isn't supported by its bound source's retrieved content — enforced by the output schema/tool contract at emission, not by a later pass. Combined with the MVP's existing rule (cite only from the cache), a claim that is fabricated *or* misattributed is structurally harder to produce in the first place.
- **`verify` becomes a hard gate, not a cleanup.** It independently re-checks each claim against its source text; any `UNSUPPORTED` **blocks promotion** to synthesis rather than being quietly dropped. This is the governance-rails pattern from the Amex work — a mandatory gate every claim transits, analogous to the model-gating built there (hallucination/faithfulness/PII checks before a model could ship).

**The two failures stay distinct (the precise statement):** structural binding eliminates **fabricated sources** — `assert_claim` can only reference the retrieved pool. The verifier independently catches **misattribution** — a real source cited for a claim it does not actually support. Both gates are load-bearing; neither makes the other redundant. (This corrects the imprecise "fabricated URLs become impossible" framing — structural binding kills fabrication, the verifier kills misattribution.)

- **Atomicity by decomposition.** A pre-verify step splits compound claims ("Vendor X has an open API *and* SOC2 *and* costs $2k/mo") into atomic, separately-verifiable claims — replacing the MVP's prompt-instruction-and-accept.
- **Faithfulness scoring** per research doc (coverage, support ratio, conflict count) tracked over time as a quality metric of the engine itself (feeds B6's confidence and B10's eval).

---

## B6. Synthesis, confidence & calibration — hardens the MVP's Stage 3

**MVP already does the right things** (four-path lenses over two pools, the challenger producing the runner-up, decisive factors replacing weights, open questions for gaps). Production adds rigor and **revives the confidence signal the MVP deferred** — as a *qualitative-plus-signal*, never a numeric score summed from weights (those stay gone).

- **The challenger becomes a mandatory gate.** In the MVP it is degradable; here a recommendation **cannot ship** until the challenger has run and *failed* to mount a credible alternative above a bar. The challenge transcript is stored (B8).
- **Confidence, returned and honestly bounded.** Expressed qualitatively (strong / moderate / close-call) and backed by *signals*, not a fabricated number: evidence coverage, share of SUPPORTED vs PARTIAL claims, source-tier weighting (B4), and **whether the challenger could mount a credible counter-case** (a recommendation that survives a strong adversarial pass is high-confidence; one the challenger nearly overturned is a flagged close-call). This is the natural home for the challenger's "earned confidence" outcome the MVP could only gesture at.
- **Score calibration → recommendation calibration.** Periodically back-test past recommendations against realized outcomes (did the "build" we favored on time-to-value actually ship on time?). Calibration adjusts the research scoping and the decisive-factor reasoning — closing the loop the MVP can't. Requires Portfolio Memory (B7) and enough decided cases to back-test.
- **Stability / inter-run consistency.** The same decision re-run over a *pinned* evidence pool (B4 cross-run cache) must not swing; variance above a threshold is itself flagged for human attention. (This is the MVP's regression-harness *stability* check, promoted to a live runtime guard.)
- **Immutable decision audit.** Every recommendation stores its evidence ids, the proposing model+version, the rules/gates that fired, the challenger transcript, and the rubric hash (B8).

---

## B7. Portfolio Memory Service — the deferred MVP component, now central

**MVP shortcut:** stubbed; single-need; no memory.

**Production — this is the compounding asset and the leverage multiplier:**
- **System of record** for: every past decision (profile, dossiers, recommendation, what the human actually chose, and later the *outcome*); each company's capability inventory; vendor dossiers (pricing seen, API/extensibility posture, viability signals); and reusable internal assets (the IP one company built that another could adopt).
- **Feeds every stage:** intake pre-fills "a sibling already evaluated this"; research dedupes/caches against prior runs (B4); synthesis computes the **amortization view** (a build's cost ÷ N adopting companies) and the **reuse-first check** — recommend adopting a sibling's asset before a fresh build/buy. (Dimension #12, dormant in the MVP, becomes active here.)
- **Cross-company arbitrage queries:** "three companies pay for the same vector DB → consolidate the contract"; "company A's valuation models could serve company B's trade-in flow."
- **Data model (sketch):** `Decision`, `Capability`, `Vendor`, `ReusableAsset`, `Company`, linked so a capability gap in one company can be matched to an asset or decision in another.
- **Governance:** company-scoped access controls; regulated-company data partitioned and never co-mingled into shared research caches without scrubbing (B8).

This service is *why* the engine is worth more to a holding company than to any single startup. It is the narrative centerpiece even though it is out of the MVP.

**Note on "acquire."** Even here, the engine does **not** evaluate acquisition as a scored path — that boundary holds at every scale. What Portfolio Memory adds is the *reuse* check ("a sibling already has this"), which is a build/buy-avoidance signal, not an M&A recommendation. Acquisition stays with the humans who run Emergence's actual acquisition function.

---

## B8. Cross-cutting: trust, audit, security

- **Full auditability.** The event-sourced log (B3) + immutable decision audit (B6) means any historical recommendation can be reconstructed exactly: what was known, what was cited, which gates fired, who approved. This is the capital-allocation analogue of model-risk audit trails.
- **Human-gate authority model.** Gates carry identity — who approved, with what edits — so accountability is explicit.
- **Data isolation & compliance.** Regulated-company data is partitioned; research caches are scrubbed before cross-company reuse; the engine flags but never clears compliance (the non-goal preserved at scale). *The MVP satisfies this trivially* — single-need run dirs, no cross-run cache — so the partition boundary need only become real when B4's cross-run cache and B7's shared memory arrive.
- **Provider/data governance.** LLM routing respects per-company data-residency and provider-allowlist policies (a regulated portfolio company may forbid certain providers or require a specific region).
- **Observability** (the Langfuse/DeepEval lineage): per-stage tracing, faithfulness/coverage metrics (B5), cost/latency per run, drift alarms on recommendation stability (B6).

---

## B9. Scaling & deployment

- **Stateless services + durable workflow store.** Intake/Research/Synthesis/Reporting scale horizontally; Orchestration and Portfolio Memory hold state.
- **Research is the scaling bottleneck** (web/LLM-bound, bursty): autoscale research workers; queue + backpressure; per-run token budgets to bound cost.
- **Multi-tenancy by company** with strict isolation; shared services, partitioned data.
- **Cost controls:** provider routing, cross-run caching, token budgeting, and a hard per-decision spend cap with human escalation above it.
- **Failure posture:** any activity retriable and idempotent; a dead research worker reschedules; a poisoned context is contained to its sub-agent; no single failure loses a run.

---

## B10. Engine self-evaluation at scale — promotes the MVP's regression harness

**MVP shortcut:** a good-to-have, degradable golden-fixture harness asserting the deterministic skeleton (mapping/sections/claims-resolve), stability (no path-flip over a fixed pool), and leakage (no UNSUPPORTED claims escape).

**Production:** the same three checks become **continuous**, plus the loop the MVP can't close:
- **Skeleton / stability / leakage** run in CI on every prompt or rubric change — a prompt edit that introduces instability or a leak fails the build. (The MVP's `engine_version` bump becomes a real gate.)
- **Faithfulness metrics** (B5) tracked as time series; drift triggers alarms.
- **Outcome back-testing** (B6 calibration) — the only eval that needs the real world: did the recommendations the engine made come true? This is what turns "the engine is internally consistent" into "the engine is *right*," and it requires Portfolio Memory (B7) + decided cases.

The MVP proves the engine is *consistent and grounded*; the Target proves it is *calibrated and correct*. That is the honest line between the two.

---

## B11. MVP → Target migration path (the roadmap)

| Capability | MVP | Target | Migration trigger |
|---|---|---|---|
| Orchestration | LangGraph + SQLite checkpointer | LangGraph + durable checkpointer (Postgres) | first multi-day run / first lost run |
| Concurrency | BUILD/BUY parallel branches | deeper parallel fan-out within each track | research latency hurts UX |
| Grounding | post-hoc verify | structural + hard gate | first misattributed claim reaches a human |
| Challenger | degradable pass | mandatory gate | recommendations go to real capital calls |
| Confidence | deferred (none) | qualitative-plus-signal | reviewers ask "how sure are we?" |
| Scoring discipline | reasoned, uncalibrated | outcome-back-tested calibration | enough decided cases to back-test |
| Memory | stub | full service | 2nd company onboarded |
| Reproducibility | within-run (source cache) | cross-run (pinned corpora) | audit/compliance requirement |
| Providers | single (Gemini) | routed (Gemini/Claude/OSS) | cost/latency pressure |
| Output | static HTML | served dashboard | reviewers want to re-examine live |
| Eval | degradable harness | continuous CI + back-testing | first prompt-change regression |

The ordering follows the same prioritization discipline: each upgrade is triggered by a real pain, not built speculatively — the same discipline the engine enforces on its users.

*End of Target Architecture. Together with the Design & Decision Model and the MVP HLD & Build Specification, this is the full arc: a credible 2-day build that visibly grows into a portfolio-scale platform.*
