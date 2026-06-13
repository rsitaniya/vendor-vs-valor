"""CHECKPOINT 4: a live intake + research run on a runtime need, producing real
cited, verified claims. Writes inspectable artifacts under runs/<id>/.

Run: uv run python scripts/cp4_demo.py
"""

from __future__ import annotations

import json
import sys

from engine.runstore import RunStore
from llm import flash_model, get_provider
from stages.intake import run_intake
from stages.research import merge_verify_reports, run_research

NEED = (
    "We need a vector database to power semantic search over our product catalog. "
    "Small platform team (3 engineers), cost-conscious, data is not especially "
    "sensitive, and we want to stay flexible rather than locked into one vendor."
)


def _show_research(res) -> None:
    print(f"\n=== {res.track} research: {len(res.kept)} verified claims "
          f"({len(res.dropped)} dropped, {len(res.assert_rejected)} rejected at assert) ===")
    for c in res.kept:
        flags = f"  [{', '.join(c.flags)}]" if c.flags else ""
        src = c.sources[0]
        print(f"\n• ({c.dimension}/{c.status.value}){flags} {c.text}")
        print(f"    \"{src.display_quote}\"")
        print(f"    -> {src.url}  (dated: {src.source_date})")
    for gap in res.coverage_gaps:
        print(f"  gap: {gap}")


def main() -> int:
    provider, model = get_provider(), flash_model()
    store = RunStore.new("runs", model_id=model)
    print(f"run dir: {store.dir}\nmodel: {model}")

    print("\n[1/3] intake (live)...")
    intake = run_intake(NEED, str(store.dir), run_id=store.dir.name, provider=provider, model=model)
    profile = json.loads(intake.json_path.read_text())
    print(f"  capability: {profile['need']['capability']}")
    print(f"  intent: {profile['intent']['core_value_proximity']} | "
          f"customization: {profile['customization_need']}")
    print(f"  soft_steer: {profile['soft_steer']}")

    print("\n[2/3] BUILD research (live: search -> fetch -> assert -> verify -> filter)...")
    build = run_research("BUILD", str(store.dir), provider=provider, model=model)
    _show_research(build)

    print("\n[3/3] BUY research (live)...")
    buy = run_research("BUY", str(store.dir), provider=provider, model=model)
    _show_research(buy)
    merge_verify_reports(str(store.dir))

    total = len(build.kept) + len(buy.kept)
    print(f"\nartifacts: {store.dir}/*.md, *-research.json, verify-report.json, sources/")
    if total == 0:
        print("WARN: no verified claims produced — inspect coverage gaps above.")
        return 1
    print(f"CP4 PASS: {total} verified, cited claims across both tracks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
