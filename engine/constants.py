"""Central registry for all tunable constants and flag strings (PR-001).

Single source of truth — import from here instead of scattering magic numbers
across files. Organised by concern so the impact of each change is obvious.
"""

# ---------------------------------------------------------------------------
# Source cache / fetch
# ---------------------------------------------------------------------------
MIN_CONTENT_CHARS = 400          # below this a fetched page is "thin content"

# ---------------------------------------------------------------------------
# Research stage — source pool sizing
# ---------------------------------------------------------------------------
MAX_SOURCES = 25                 # max URLs admitted to the closed evidence pool
PER_QUERY = 6                    # DuckDuckGo results requested per query
MAX_PER_DOMAIN = 2               # domain-diversity cap (stops one site dominating)

# ---------------------------------------------------------------------------
# Research stage — excerpt / cost-window budgets passed to the author LLM
# ---------------------------------------------------------------------------
EXCERPT_CHARS = 6000             # head-of-content budget per source
COST_WINDOW_BUDGET = 2500        # extra budget for pulled-forward cost/price windows
COST_WINDOW_PAD = 140            # chars of context around each cost/date hit

# ---------------------------------------------------------------------------
# Research stage — entity discovery (Phase 0)
# ---------------------------------------------------------------------------
ENTITY_DISCOVERY_QUERIES = 3     # broad discovery queries to generate
ENTITY_DISCOVERY_MAX_SOURCES = 5 # pages to fetch for curation (listicles welcome)

# ---------------------------------------------------------------------------
# Grounded-claim skill — verification
# ---------------------------------------------------------------------------
STALE_DAYS = 365                 # cost claims older than this get stale_cost flag
VERIFY_CONTEXT_CHARS = 200       # window around the locator span given to verifier

# ---------------------------------------------------------------------------
# Claim flags (kept here so models.py, claim.py, synthesis.py, report.py
# all reference the same string values)
# ---------------------------------------------------------------------------
PARTIAL_EVIDENCE = "partial_evidence"
STALE_COST = "stale_cost"
UNDATED_COST = "undated_cost"    # cost claim whose source has no publication date
PRICE_CONFLICT = "price_conflict"  # set by synthesis when sources disagree on price
