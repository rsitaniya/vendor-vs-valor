# Vendor vs Valor

An advisory intelligence engine for capability-sourcing decisions. Given a natural-language description of a capability need, it runs structured intake, dual-track research (build economics and buy-market scan), and four-path strategic synthesis — producing a cited, qualitative recommendation with a challenger-sourced runner-up.

Output is advisory only. Every claim is independently cited and verified against cached source content. No scores, no weighted rubrics.

Companion writeup: [sitaniya-com.pages.dev/blog/vendor-vs-valor](https://sitaniya-com.pages.dev/blog/vendor-vs-valor)
Sample report (Indian capital markets use case): [vendor-vs-valor-sample-report.html](https://sitaniya-com.pages.dev/vendor-vs-valor-sample-report.html)

> **Status:** MVP, built solo, in the open. It's had more thought put into its citation discipline than its uptime. Treat it like a research assistant you're still training, not a system you'd bet a quarter on.

### What it won't do
It won't approve a purchase, replace your legal/security/procurement review, or paper over a vendor's missing price with a guess: a hidden price is a finding, not a gap to fill in. And it won't make the final call: research is the part it automates, judgment about where the money goes stays with a person.

---

## How it works

**Intake.** The engine elicits a structured need-profile from the raw input: capability description, team, stack, budget, timeline, constraints, compliance regime, and a soft qualitative steer. The profile is written to `profile.md` and surfaced to the operator at Gate 1 before research begins.

**Research.** Two tracks run in parallel — BUILD (in-house economics, talent, OSS alternatives) and BUY (vendor landscape, pricing, integration, lock-in) — across 14 research dimensions drawn from `rubric/metrics.json`. Each factual claim is asserted with a source URL and a verbatim display quote, then independently verified by re-reading the cached page content. A claim's verification status (`SUPPORTED / PARTIAL / UNSUPPORTED`) can only be set by the verifier, never by the authoring LLM. Research artifacts (`build-research.md`, `buy-research.md`) and a verify report are surfaced at Gate 2.

**Synthesis.** Four strategic lenses (`build`, `buy`, `buy_then_extend`, `adopt_self_host`) are applied over the two evidence pools. A challenger pass then constructs the strongest cited case for an alternative path before the final strategy is committed. Output is `strategy.md`: recommendation, runner-up, "wins when" conditions, decisive factors, per-path dossiers, and explicit open questions. The HTML report is produced at Gate 3.

---

## Pipeline

```
input.md
   │
   ▼
[intake] ──► [gate 1: review profile] ──► [research_build] ─┐
                                          [research_buy]   ──┤
                                                             ▼
                                                      [research_join]
                                                             │
                                          [gate 2: review research]
                                                             │
                                                       [synthesis]
                                                             │
                                          [gate 3: review strategy]
                                                             │
                                                        [report]
                                                             │
                                                      runs/<id>/
                                                      report.html
```

The three gates are LangGraph `interrupt()` points. The pipeline parks, writes its artifact, and waits for the operator by default: approve, or edit (gate 1: one clarification round for fields still on a placeholder that matter to research quality, then the profile in `$EDITOR`; gate 3: the soft steer, which re-runs synthesis — the input-hash guard skips research). Gate 2 is approve/abort only; there's no sanctioned edit path for research claims. Pass `--auto-approve` to `run.py` for the old unattended behavior. Each work node is idempotent via a content-hash guard: a re-entered node recomputes its input hash, finds its existing artifact, and no-ops.

---

## Project layout

```
vendor-vs-valor/
├── graph.py                  # LangGraph pipeline: nodes, edges, gate interrupts, checkpointer
├── run.py                    # CLI entry point — reads input-market-data-india.md, drives graph end-to-end
│
├── stages/
│   ├── intake.py             # Stage 1: elicit and validate profile.json / profile.md
│   ├── research.py           # Stage 2: per-track search → claim assertion → verify + filter
│   ├── search.py             # DuckDuckGo discovery + trafilatura full-page fetch + cache
│   ├── synthesis.py          # Stage 3: four-path synthesis over evidence pools
│   ├── challenger.py         # Adversarial pass: strongest cited case for the alternative
│   └── report.py             # Stage 4: HTML report from strategy.md
│
├── skills/
│   ├── grounded_claim/       # Trust layer: assert_claim, verify, filter; source cache
│   │   ├── models.py         # Claim, Source, Locator, ClaimDraft, VerificationJudgment
│   │   ├── claim.py          # assert_claim() and verify() implementations
│   │   ├── cache.py          # Per-run source cache (fetch once, read many)
│   │   └── locate.py         # char_span locator: find display_quote in cached content
│   └── schema_stage/         # LLM wrapper: load → prompt → structured output → validate → persist
│
├── engine/
│   ├── runstore.py           # RunStore: run dir, RunManifest, artifact helpers
│   ├── hashing.py            # Input-hash guard (idempotency, spec §4)
│   └── constants.py          # Shared flags: STALE_COST, UNDATED_COST, PARTIAL_EVIDENCE, etc.
│
├── llm/
│   ├── provider.py           # LLMProvider interface — swap model via env var, not code
│   └── gemini.py             # Gemini implementation (Flash workhorse, Pro for synthesis)
│
├── rubric/
│   ├── metrics.json          # 14 research dimensions with per-track scoping hints
│   └── paths.json            # Four strategic paths and their evidence-pool mappings
│
├── agents/                   # Prompt templates for each stage (markdown)
│   ├── intake.md
│   ├── research_build.md
│   ├── research_buy.md
│   ├── research_query_plan.md
│   ├── synthesis.md
│   └── challenger.md
│
├── tests/                    # pytest suite
│   ├── test_grounded_claim.py
│   ├── test_schema_stage.py
│   ├── test_graph.py
│   ├── test_intake.py
│   ├── test_research.py
│   ├── test_synthesis.py
│   ├── test_challenger.py
│   ├── test_rubric.py
│   └── test_runstore.py
│
├── docs/
│   ├── design-v2.md          # Decision model, engine rules, design rationale
│   ├── mvp-hld-and-build-spec.md  # Contracts, stage specs, build order (authoritative)
│   └── target-architecture.md     # Production-scale design (context only; not built)
│
├── runs/                     # Output root — one subdirectory per run (gitignored)
├── pyproject.toml
└── .env.example
```

---

## Setup

**Prerequisites:** Python 3.11+, [`uv`](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/rsitaniya/vendor-vs-valor.git
cd vendor-vs-valor
uv sync
cp .env.example .env
```

Edit `.env`:

```ini
GEMINI_API_KEY=<your key from https://aistudio.google.com/apikey>
GEMINI_MODEL_FLASH=gemini-3.5-flash        # workhorse: intake + research
GEMINI_MODEL_PRO=gemini-3.1-pro-preview    # synthesis + challenger
LLM_PROVIDER=gemini
ENGINE_VERSION=0.1.0
```

Verify your key has access to both model tiers before running:

```python
from google import genai
for m in genai.Client().models.list():
    print(m.name)
```

---

## Usage

Copy `input-template.md` and fill it in — one pass, every question the engine
can use, "not specified" for anything you don't know:

```bash
cp input-template.md my-need.md
```

(See `input-market-data-india.md` / `input-auth-startup.md` for filled-in examples.)

Run the pipeline:

```bash
uv run python run.py                  # reads ./input-market-data-india.md by default
uv run python run.py path/to/need.md  # explicit path
```

By default the engine pauses at each gate for real review (approve/edit/abort — see "Pipeline" above) and opens the HTML report on completion. Add `--auto-approve` to skip review and run unattended. Intermediate artifacts are written to `runs/<timestamp-id>/` as the pipeline progresses.

```bash
uv run python run.py my-need.md --auto-approve   # unattended, old behavior
```

Two full committed example runs, including `strategy.md` and `report.html`:
- [`runs/example-market-data-india/`](runs/example-market-data-india/) — `input-market-data-india.md`, the capital-markets scenario walked through in the [companion writeup](https://sitaniya-com.pages.dev/blog/vendor-vs-valor)
- [`runs/example-auth-startup/`](runs/example-auth-startup/) — `input-auth-startup.md`, the auth/access-management scenario

### Run artifacts

| File | Stage | Description |
|---|---|---|
| `run.json` | all | Manifest: per-stage status + recorded input hashes |
| `profile.json` / `profile.md` | intake | Structured need-profile |
| `build-research.json` / `build-research.md` | research | BUILD track: claims + verify report |
| `buy-research.json` / `buy-research.md` | research | BUY track: claims + verify report |
| `verify-report.md` | research | Consolidated claim verification summary |
| `strategy.json` / `strategy.md` | synthesis | Four-path strategy + challenger output |
| `report.html` | report | Self-contained HTML report |
| `source_cache/` | research | Cached full page content (one file per URL) |

---

## Key design invariants

**`grounded_claim` trust layer.** The authoring LLM emits a `ClaimDraft` (text + URL + verbatim quote). `assert_claim()` fetches and caches the URL, finds the quote, and creates a `Claim` with status `UNVERIFIED`. Only `verify()` — which re-reads cached bytes and calls an independent judge — can set `SUPPORTED`, `PARTIAL`, or `UNSUPPORTED`. The author can never set a claim's status.

**Source cache as closed evidence pool.** Sources are fetched once per run via `trafilatura` and stored in `runs/<id>/source_cache/`. Verification reads only cached content, never the live web. This makes every run reproducible and auditable.

**Idempotency hash guard.** Every work node computes a hash of its inputs before executing. If the hash matches a recorded artifact from a prior run of that node, the node returns immediately without calling the LLM. This also handles LangGraph's re-entry-from-top behavior on resume: the re-entered node no-ops without double-calling the model.

**Provider interface.** No node imports a model provider directly. All LLM calls go through `llm/provider.py`. Model IDs and provider selection live in `.env`. Swapping from Gemini to another provider is a config change, not a code change.

**Qualitative output only.** There are no scores, weights, or numeric confidence values anywhere in the pipeline. The engine reasons over evidence and surfaces decisive factors; it does not manufacture false precision through weighted aggregation.

---

## Configuration

Every tunable value lives outside stage code, in one of three places: model IDs and provider selection in `.env`, search/verification thresholds in `engine/constants.py` (`MAX_SOURCES`, `STALE_DAYS`, per-domain caps, excerpt budgets), and the domain logic itself in `rubric/metrics.json` / `rubric/paths.json`. Swapping the LLM provider, resizing the evidence pool, or changing what counts as a stale price is a config edit, not a code change.

---

## Why grounded_claim, not a research agent

Most deep-research agents ask one model to find sources, write claims, and cite them, then trust that model's own citations. A 2026 audit of deep-research agents ([*Cited but Not Verified: Parsing and Evaluating Source Attribution in LLM Deep Research Agents*, arXiv:2605.06635](https://arxiv.org/html/2605.06635v1)) found frontier models keep citation link validity above 94% and topical relevance above 80%, while the citation's actual factual accuracy lands at only 39–77%. One tested model's accuracy fell from 78.6% to 16.7% as a single research session went from 2 to 150 tool calls: citations kept looking valid while no longer supporting the claim.

`grounded_claim` avoids this by construction, not by prompting harder:
- `assert_claim()` cannot create a citation to a URL outside the run's cache, or a quote it can't locate verbatim in the cached bytes. An ungrounded citation is a rejected claim, not a lucky one.
- The author can never set a claim's verified status. Only `verify()` can, by re-reading the cached bytes at the claim's locator and judging a narrow question in isolation, with no view of the author's own reasoning.
- Every run persists its full evidence pool (`runs/<id>/source_cache/`) alongside the claims, verify report, and strategy. A decision made today can be re-opened and checked against the exact bytes it was built on, months later.

---

## Tests

```bash
uv run pytest
```

The test suite covers `grounded_claim`, `schema_stage`, the graph topology (park/resume), each pipeline stage, the rubric schema, and `RunStore`. Tests run without network access and without a real LLM key — live-model behavior is covered by the smoke scripts in `scripts/`.

---

## Docs

| Document | Purpose |
|---|---|
| `docs/mvp-hld-and-build-spec.md` | Primary spec: data contracts, stage interfaces, hash guard, build order |
| `docs/design-v2.md` | Decision model, four-path reasoning, engine design rationale |
| `docs/target-architecture.md` | Production-scale design (portfolio memory, fan-out, served dashboard) — context only, not built |

---

## License
MIT, see [LICENSE](LICENSE).

## Author
Built by [Rohan Sitaniya](https://github.com/rsitaniya).
