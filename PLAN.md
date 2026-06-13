# PLAN.md — Portfolio Decision Engine (MVP build plan)

**Status:** awaiting approval. No code until PLAN.md is approved (per CLAUDE.md).
**Source of truth:** `docs/mvp-hld-and-build-spec.md` (primary), `docs/design-v2.md` (why), `docs/target-architecture.md` (context only — do NOT build Target features).

This plan maps 1:1 to the spec's §8 build order and CLAUDE.md's build-order/checkpoints. Each slice is a vertical, runnable, checkable increment. I stop at the marked checkpoints; between them I proceed.

---

## 1. Stack confirmation (decided — flagging, not changing)

- **Python 3.11+** (3.13.9 present). Package/venv via `pip` + `venv` unless you prefer `uv`/`poetry`.
- **LangGraph** orchestration: pipeline = graph; 3 human gates = `interrupt()`; resume via `Command(resume=…)`; state via a checkpointer (SQLite for MVP, in-memory for tests).
- **Gemini** default model (Flash workhorse, Pro for synthesis) **behind a provider interface** — model id in env var, never hard-coded in a node. Interface shaped so a swap to Claude/GPT is a config change.
- **Secrets in `.env`** via `python-dotenv`; never committed. `.gitignore` covers `.env`, `runs/`, caches.
- **Retrieval = search-to-discover + fetch-full-page-content** (not snippets), because the `Claim` locator points into cached *content*. Full content is fetched once and cached per run; `verify` re-reads cached bytes.

### Dependencies (INSTALLED via `uv` — versions pinned in `uv.lock`)

| Dep | Version | Purpose |
|---|---|---|
| `langgraph` | 1.2.5 | graph, `interrupt()` gates, checkpointer-backed resume |
| `langgraph-checkpoint-sqlite` | 3.1.0 | SQLite checkpointer (MVP) |
| `google-genai` | 2.8.0 | Gemini SDK — structured output via `response_schema` + `response_mime_type` |
| `pydantic` | 2.13.4 | `Claim` / `profile` schemas + structured-output contracts |
| `python-dotenv` | 1.2.2 | load `.env` |
| `ddgs` | 9.14.4 | **DuckDuckGo** search-to-discover (no key; per your call) |
| `httpx` | 0.28.1 | fetch full page content |
| `trafilatura` | 2.1.0 | extract main text from fetched HTML (clean content for locators) |
| `pytest` (dev) | 9.0.3 | unit tests + regression harness |

Not added: `jinja2` — the single self-contained `report.html` is hand-templated in Python (lean deps, deterministic output). `tavily` — dropped per your call (no key).

### Component reuse decision (researched per your ask — reuse before rebuild)
- **Adopt as primitives:** the deps above. These are the commodity layer.
- **Do NOT adopt a deep-research framework** (`gpt-researcher`, langchain `open_deep_research`): they ship their own citation/grounding model and open-web research loop that **conflict with our load-bearing invariants** (`grounded_claim`'s closed-evidence cache, locator+verify, four-path lenses). Adopting them means fighting them. We borrow their *scoping-prompt ideas* as reference only.
- **Verified API surface** (against installed SDKs, not web summaries): `langgraph.types.{interrupt, Command}`, `langgraph.checkpoint.sqlite.SqliteSaver`; `google.genai` structured output = `GenerateContentConfig(response_mime_type="application/json", response_schema=<PydanticModel>)` → `response.parsed`.
- **Schema-default caveat (drives the Claim design):** Gemini structured output is finicky with Pydantic default values. So the **LLM emits a minimal `ClaimDraft`** (`text`, `sources[url, display_quote]`, `dimension`) — **no** `id`/`status`/`cost_tagged`/`locator`. Code constructs the full `Claim`. This dodges the SDK quirk *and* enforces invariant #2 (author can never set `status`). See Q1.

---

## 2. Architecture invariants I'm building to (restating so we agree before code)

These are the IP per CLAUDE.md; every slice below preserves them:

1. **Two skills are real module boundaries** (`grounded_claim`, `schema_stage`), built + unit-tested in isolation FIRST.
2. **Author can never set `status`.** `assert_claim` → `UNVERIFIED`, rejects empty sources + URLs not in cache. Only `verify` sets SUPPORTED/PARTIAL/UNSUPPORTED, by re-reading **cached** content.
3. **Source fetched once, cached per run.** `verify` reads cached bytes; the cache IS the closed evidence pool.
4. **Four paths only** (build, buy, buy-then-extend, adopt-and-self-host). No acquire, anywhere.
5. **Paths are synthesis lenses over two evidence pools** (BUILD, BUY), not separate research agents.
6. **Qualitative only** — no scores/weights/numeric confidence.
7. **Every node body idempotent** via the input-hash guard (§4) — this also defuses LangGraph's "re-enter from top on resume" footgun.
8. **Case-agnostic** — no domain hardcoding; intake elicits compliance/sensitivity as general fields.

---

## 3. Vertical slices (mapped to spec §8 / CLAUDE.md build order)

> **STOP-for-review checkpoints** (per CLAUDE.md): after **PLAN.md**, **CP1**, **CP2**, **CP4**, **CP5**.
> Note: intake (CP3 in build-order numbering) is NOT a stop point — I proceed through it.

### Slice 0 — Scaffold (pre-work, fast)
Repo layout per design §9.5 (`/skills`, `/agents`, `/rubric`, `/eval`, `/runs`, `graph.py`), `requirements.txt`, `.env.example`, `.gitignore`, `git init`.
**Acceptance:** tree exists; `pip install -r requirements.txt` succeeds; `import langgraph, google.genai` works.

### Slice 1 — `rubric/metrics.json` + `rubric/paths.json` (the spine) — §8.1
- `paths.json`: exactly the §3.3 shape (build/buy/buy_then_extend/adopt_self_host → pools, gate, note).
- `metrics.json`: the 14 dimensions (ids `m1…m14`) each with `question` + per-track ("BUILD"/"BUY") "what to look for" list, per spec §6 and design §3.3. Cost dimensions = `m3,m4,m5` (drive `cost_tagged`).
**Acceptance:** both files load + validate against a small schema check; `paths.json` references only the four paths and the two pools.

### Slice 2 — `grounded_claim` skill + source cache — §8.2 → **CHECKPOINT 1 (STOP)**
- `Claim` pydantic model exactly per §3.1 (content-addressed `id`, sources with locator + `display_quote`, `dimension`, `track`, `cost_tagged`, `status`).
- Source cache: `sources/<sha256(url)>.{content,meta}`; fetch-once.
- `assert_claim(text, sources, dimension, track)` → UNVERIFIED; **rejects** empty sources, URLs not in cache, and cost-tagged claims missing `source_date`.
- `verify(claim)` → reads **cached** content via locator, independently judges SUPPORTED/PARTIAL/UNSUPPORTED (separate LLM call via provider interface; never trusts `display_quote`).
- `filter(claims, policy)` → drops UNSUPPORTED (logged), keeps+flags PARTIAL, applies `stale_cost` (>12mo) and `price_conflict` flags.
- **Provider interface** (`llm/provider.py`) built here since `verify` needs it: `complete(prompt, schema, model_id)` behind an interface, Gemini impl, model id from env.
- **Load-bearing smoke test (per CLAUDE.md):** confirm Gemini reliably returns the structured `Claim`/locator shape before research is built on it. If it doesn't → I stop and raise it as a design conversation.
**Acceptance (CP1):** `pytest` green on grounded_claim in isolation — assert rejects unsourced/uncached/undated-cost; verify labels a planted SUPPORTED, a PARTIAL, and an UNSUPPORTED correctly against fixture cached content; filter drops/flags correctly; status is unsettable by the author. **I show you green tests + the smoke-test output, then stop.**

### Slice 3 — `schema_stage` skill + graph skeleton + hash guard — §8.3 → **CHECKPOINT 2 (STOP)**
- `schema_stage.run(stage_name, inputs, prompt, output_contract, render, run_dir)` — load→LLM→validate→persist `.json`+`.md`→update `run.json` (status + recorded_hash). Render direction per §3.2 (json-truth for intake/research; md-truth for synthesis).
- `run.json` manifest + **input-hash guard** per §4: `current_hash = hash(input_files + prompt_file + rubric_files + model_id + engine_version)`; node skips body + reuses artifact iff `status==done AND recorded_hash==current_hash`.
- LangGraph graph skeleton: 4 nodes + 3 `interrupt()` gates + SQLite checkpointer. Node bodies idempotent (hash guard) → defuses re-enter-from-top footgun.
**Acceptance (CP2):** a trivial 1-node graph **parks at `interrupt()` and resumes** via `Command(resume=…)`; re-running an unchanged node **no-ops** (hash match, no second LLM call — proven by a call counter); changing an input invalidates + re-runs. **I demo park/resume + skip behavior, then stop.**

### Slice 4 — Stage 1 intake → `profile.{md,json}` — §8.4 (CP3 — proceed, no stop)
- `/agents/intake.md`: case-agnostic interview prompt (need, intent, resources, constraints, customization, **soft_steer** — no numbers, no domain cues).
- `profile.json` schema (§5.1) + **code** validator (required `need` fields, enums in range, `soft_steer` present; fail → halt with precise error).
- Wired as graph node 1 with gate-1 `interrupt()` surfacing `profile.md`.
**Acceptance:** an intake run on an arbitrary need produces schema-valid `profile.json`; validator rejects a malformed profile; gate-1 parks for review. Proceed to Slice 5.

### Slice 5 — Stage 2 research (parameterized track) + verify/filter — §8.5 → **CHECKPOINT 4 (STOP)**
- One parameterized `research_agent(track)`; `/agents/research_build.md` + `/agents/research_buy.md` scoping prompts (the schedule risk — I pre-write/test these). Covers the §5.2 BUILD/BUY checklists.
- Search-to-discover → fetch-full-content → cache → `assert_claim` per claim → `verify` (re-reads cache) → `filter`. Emits `build-research.{md,json}` then `buy-research.{md,json}` + `verify-report.json`. `.md` generated from filtered json.
- Run **BUILD and BUY in parallel** as separate LangGraph branches; a join node assembles `verify-report.json`; gate-2 `interrupt()` surfaces both docs + verify report.
**Acceptance (CP4):** a live research run on the intake need produces real cited claims, each with a resolvable cached source; verify independently labels them; filter drops UNSUPPORTED and flags PARTIAL/stale/conflict. **I show you real cited output with live citations, then stop.** (This is the schedule-risk checkpoint.)

### Slice 6 — Stage 3 synthesis + challenger → `strategy.{md,json}` — §8.6 → **CHECKPOINT 5 (STOP)**
- `/agents/synthesis.md`: four-path lenses over the two pools per `paths.json`; per-path dossier (pros/cons/risks/**reversibility**), recommendation + thesis, **decisive factors**, **open questions**. Each factual claim cites a verified `Claim`.
- `/agents/challenger.md`: sees pools + recommendation, makes strongest **cited** counter-case → runner-up + "wins when". **Degradable** to single-pass (first thing to drop).
- Deterministic `assemble` (code) validates every cited claim id, requires one dossier per canonical path, then writes `strategy.md` (truth) + `strategy.json` (section manifest + claim-ids). Gate-3 `interrupt()`; editing soft_steer re-runs synthesis only (hash guard), research skipped.
**Acceptance (CP5):** first **end-to-end** run produces `strategy.md` with all required sections, four dossiers, runner-up, decisive factors, open questions — every factual claim resolving to a SUPPORTED/PARTIAL Claim. **I show you the first end-to-end `strategy.md`, then stop.**

### Slice 7 — Stage 4 `report.html` — §8.7 (proceed)
Deterministic Python renderer → single self-contained HTML (inline CSS/JS, opens offline): recommendation banner, 4 dossiers, runner-up + conditions, decisive factors, expandable cited evidence w/ clickable URLs, visually-distinct flags (partial/stale/conflict), open-questions panel, **stubbed** portfolio-reuse panel. Reads only `strategy.json` + claim sidecars; no LLM.
**Acceptance:** `report.html` opens offline with no external assets; flags visually distinct; evidence expandable.

### Slice 8 — Eval regression harness — §8.8 (degradable; first to drop)
`/eval/regression.py` on a golden fixture: (a) skeleton (path→pool mapping respected, sections present, claims resolve), (b) stability (re-run synthesis over same cached pool N times — path must not flip), (c) leakage (zero UNSUPPORTED reach deliverable).
**Acceptance:** harness passes on a golden fixture; a deliberately-broken fixture fails it.

### Slice 9 — One clean end-to-end run, cached for offline demo — §8.9
Full live run; cache it so the source cache replays offline (demo safety).
**Acceptance:** offline re-run reproduces the same assessment from cached evidence.

---

## 4. Degradation order (if time runs short — per spec/CLAUDE.md)
1. Drop eval harness (Slice 8) entirely.
2. Degrade challenger (Slice 6) to single-pass synthesis — runner-up still produced.
3. Drop HTML report (Slice 7) to styled markdown strategy.
Never leave the core pipeline (Slices 1–6 minus challenger) broken end-to-end.

---

## 5. Questions / ambiguities for you (NOT resolving silently)

**Q1 — `locator` mechanism (load-bearing; determines `assert_claim` signature).** The `Claim` shows `locator: {type: char_span, start, end}` pointing into cached content, plus `display_quote` (<15 words). LLMs cannot reliably emit character offsets. **My proposed resolution:** the research author emits the verbatim `display_quote` + url; `assert_claim` **computes** the `char_span` deterministically by locating that quote in the cached content (exact match, then a fuzzy fallback); if it can't be located → reject the claim. `verify` then re-reads the cached content around that span and judges support **independently** (it does not trust `display_quote`). This keeps "verify reads the bytes, not the author's quote." **Confirm this interpretation, or tell me you want the LLM to emit offsets directly.**

**Q2 — Gemini API access. [RESOLVED]** Defaults set to `gemini-3.5-flash` / `gemini-3.1-pro-preview` in `.env.example` and code; override via env if needed.

**Q3 — Search provider. [RESOLVED]** DuckDuckGo (`ddgs`), no key, per your call. (Demo-safety comes from the per-run source cache replaying offline, not from the search provider.)

**Q4 — `metrics.json` shape.** The spec names its contents (14 dimensions, question + per-track "what to look for") but doesn't pin the JSON shape. I'll author the shape derived from design §3.3. Flagging that I'm authoring it; will show it at Slice 1 for a glance.

**Q5 — Git. [RESOLVED]** `git init` done; `old/` git-ignored (never committed). Will commit per slice with messages mapping to build-order items.

**Q6 — Doc-path mismatch. [RESOLVED]** The three architecture/design docs now live under `/docs`: `docs/mvp-hld-and-build-spec.md`, `docs/design-v2.md`, and `docs/target-architecture.md`.

**Q7 — Env tooling. [RESOLVED]** `uv` (synced; `pyproject.toml` + `uv.lock` in place).
