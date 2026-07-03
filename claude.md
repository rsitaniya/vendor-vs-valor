# Vendor vs Valor — working agreement for Claude Code

## Ground truth
The three docs in `/docs` are authoritative. In order of build-relevance:
1. `docs/mvp-hld-and-build-spec.md`: PRIMARY. Contracts (§3 `grounded_claim`, `schema_stage`; §4 run dir + hash guard; §5 stages), build order (§8).
2. `docs/design-v2.md`: the why, the decision model, the engine rules (§6).
3. `docs/target-architecture.md`: CONTEXT ONLY. Do not build Target features. Use it only to keep MVP seams clean.

If code and docs disagree, the docs win. If the docs are ambiguous, ASK: do not silently resolve.
Do not rescope, "improve," or add features beyond the MVP without flagging first.

## Stack (decided — do not change without asking)
- Python 3.11+.
- **LangGraph** for orchestration: the pipeline is a graph; the 3 human gates are `interrupt()` points; resume via `Command(resume=…)`; state via a checkpointer (InMemory/SQLite for MVP).
- **Gemini** is the default model (Flash workhorse, Pro for synthesis), accessed **behind a provider interface** with the model id in an env var. Never hard-code a provider inside a node. The interface must make swapping to Claude/GPT a config change.
- Secrets in `.env` (`python-dotenv`); never commit keys.
- Retrieval: search to discover + fetch full page content (not just snippets): the `Claim` locator points into cached *content*, so full content must be fetched and cached.

## Architecture invariants (these are the IP — violating them breaks the engine)
- **The two skills are real module boundaries**, not inlined helpers: `grounded_claim` (Claim + assert/verify/filter) and `schema_stage` (load→LLM→validate→persist wrapper). Build and unit-test them FIRST, in isolation, before any stage uses them.
- **Author can never set a Claim's `status`.** `assert_claim` creates UNVERIFIED and rejects empty sources + URLs not in the cache. Only `verify` sets SUPPORTED/PARTIAL/UNSUPPORTED, by re-reading CACHED content via the locator, never by trusting the author's quote.
- **Source is fetched once, content cached per run.** `verify` reads cached bytes, not the live web. The cache IS the closed evidence pool.
- **Four paths, never five.** build, buy, buy-then-extend, adopt-and-self-host. Acquire does not exist anywhere.
- **Paths are synthesis lenses over two evidence pools**, not separate research agents. Two research tracks (BUILD, BUY); synthesis frames four paths per `rubric/paths.json`.
- **Qualitative output only.** No scores, no weights, no numeric confidence. Recommendation + runner-up + "wins when" + per-path dossiers + decisive factors + open questions.
- **Every node body is idempotent** via the input-hash guard (spec §4). This is also what defuses LangGraph's "re-enter from top on resume" behavior: a re-run node recomputes its hash, finds its artifact, and no-ops. Get this right or resume will double-call the LLM.
- **Case-agnostic.** No domain hardcoding anywhere (no "if HIPAA…"). Intake elicits compliance/sensitivity as general fields; synthesis reasons over them.

## Build order (vertical slices — each must be runnable + checkable before the next)
Follow spec §8. Summary:
1. `rubric/metrics.json` + `rubric/paths.json` (the spine).
2. `grounded_claim` skill + source cache: unit-tested in isolation. **[CHECKPOINT 1]**
3. `schema_stage` skill + LangGraph graph skeleton (nodes, `interrupt()` gates, checkpointer, hash guard): prove a trivial 1-node graph parks and resumes. **[CHECKPOINT 2]**
4. Stage 1 intake → validated `profile.json` (case-agnostic prompt). **[CHECKPOINT 3]**
5. Stage 2 research (one parameterized track, run BUILD and BUY in parallel) wired through `grounded_claim`; verify+filter. **[CHECKPOINT 4: this is the schedule risk; show me real cited output]**
6. Stage 3 synthesis (four-path lenses) + challenger (degradable). **[CHECKPOINT 5]**
7. Stage 4 HTML report.
8. Eval regression harness (degradable, skeleton/stability/leakage on a golden fixture).
9. One clean end-to-end run; cache it for offline demo safety.

## Checkpoints — STOP and show me, do not steamroll
Stop for my review after: PLAN.md; CHECKPOINT 1 (grounded_claim tests green); CHECKPOINT 2 (graph parks/resumes); CHECKPOINT 4 (first real research output with live citations); CHECKPOINT 5 (first end-to-end strategy.md). Between checkpoints, proceed without asking.

## How to work
- **Plan before coding.** Use extended thinking for the contracts (grounded_claim, the hash guard, the graph wiring): these have subtle invariants.
- **Use subagents** to investigate in parallel where it helps: e.g. one to probe the Gemini structured-output API and one to probe LangGraph checkpointer/interrupt patterns, while you draft the skill interfaces. Build slices remain ordered, but the Stage 2 BUILD and BUY research branches run in parallel.
- **Test as you go.** The two skills get real unit tests. The pipeline gets the §8.8 regression harness (skeleton/stability/leakage). Don't defer all testing to the end.
- **Smoke-test the load-bearing risk early:** confirm Gemini reliably returns the structured `Claim` shape with locators BEFORE building the research stage on top of it. If it doesn't, tell me: that's a design conversation, not a thing to hack around.
- **Commit per slice** with clear messages mapping to the build-order item.
- **Keep artifacts human-inspectable:** every stage writes `.md` + `.json` to the run dir, per spec §4. I want to be able to open any intermediate.

## Degradation order (if time runs short)
1. Drop the eval harness (item 8) entirely.
2. Degrade the challenger (item 6) to single-pass synthesis: runner-up still produced.
3. Drop the HTML report (item 7) to a styled markdown strategy.
Never leave the core pipeline (1–6 minus challenger) broken end-to-end. A working narrow pipeline beats a broken wide one.

## What NOT to do
- Don't build any Target-Architecture feature (portfolio memory service, intra-track research fan-out, structural-at-emission grounding, confidence scoring, provider routing, served dashboard). Stubs/interfaces only where the MVP spec says so.
- Don't hard-code a model provider or a demo scenario.
- Don't add scoring/weights/numeric confidence: they were deliberately removed.
- Don't reintroduce the acquire path.
- Don't use browser localStorage/sessionStorage anywhere.
- Don't resolve a doc ambiguity by guessing: ask.
