# Capability need — market data infrastructure for Indian equities

## The capability

We are a Series A fintech startup (Bengaluru, founded 2023) building an
institutional-grade portfolio analytics and compliance platform for Indian wealth
managers — primarily boutique investment advisory firms, family offices, and
SEBI-registered investment advisors (RIAs) managing between ₹50 crore and ₹2,000
crore in client AUM.

Our platform needs to do three things reliably:

1. **Real-time portfolio P&L and attribution** — aggregate client holdings across
   NSE/BSE-listed equities, ETFs, and mutual funds, compute intraday P&L per
   security and sector, push live alerts when a position breaches a threshold.
2. **Historical performance and backtesting** — wealth managers want to show
   clients 10–15 year trailing returns, run attribution analysis (alpha vs. benchmark,
   factor decomposition), and backtest rebalancing strategies. This requires
   point-in-time adjusted historical prices that correctly account for splits,
   bonus issues, rights offerings, and dividend stripping — not just raw close
   prices. A single wrong corporate action cascades into wrong IRR figures shown
   to clients. This is a legal liability risk for our customers.
3. **SEBI/AMFI compliance reporting** — generate model-portfolio reports and
   client-level suitability logs that satisfy SEBI's Research Analyst and Investment
   Advisor regulations.

This is enabling infrastructure, not our product's moat — our differentiation is
the analytics and compliance workflow built on top of it — but the accuracy bar is
unusually high because a data error becomes a client-facing legal liability, not
just an internal bug.

### What we need specifically

A **market data infrastructure layer** that provides:

- **Historical OHLCV data** — NSE + BSE equities, all listed (including delisted),
  daily and intraday (1-min bars minimum). At least 20 years of history for equity,
  15 years for F&O.
- **Corporate actions** — dividends, splits, bonuses, rights, mergers, delistings.
  Must be machine-readable with ex-date, record date, ratio, and cash value.
  Accuracy here is non-negotiable: wrong corporate action = wrong client P&L.
- **Indices** — NIFTY 50, NIFTY 500, NIFTY Midcap 150, sector indices, plus
  custom index composition history (which stocks were in NIFTY 50 on date X?).
- **Real-time / delayed feed** — 15-minute delayed is acceptable for the MVP,
  sub-second tick data needed for the intraday alerts feature (Q3 roadmap).
- **Mutual fund NAVs** — AMFI daily NAV feed plus scheme metadata. This part is
  probably self-built (AMFI publishes free) but needs to be confirmed.
- **F&O market data** (lower priority) — options chain snapshots, OI, volume,
  PCR for derivatives analytics features (6–12 month roadmap item).

### Why this is genuinely hard in India

1. **Regulatory licensing**: NSE and BSE data is exchange-proprietary. SEBI's
   policies require that any commercial product redistributing market data must
   obtain exchange authorisation. You cannot legally scrape NSE or use screen-
   scraping workarounds for a commercial product. This constrains the BUILD path:
   we cannot simply "build our own ingestion" without becoming an authorised
   exchange data vendor ourselves, which is a years-long regulatory process.
2. **Corporate actions data quality**: Every Indian data vendor has gaps. Some
   have accurate dividend data but wrong bonus ratios. Some handle delisted
   companies differently. Building clean corporate actions from scratch requires
   reconciling across NSE, BSE, and SEBI filings — an ongoing maintenance
   problem, not a one-time ETL job.
3. **Historical depth**: Many Indian data vendors only carry 5–10 years of
   clean, adjusted history. For wealth management clients comparing performance
   over 20-year cycles, we need further back — ideally to 2000 for large caps.
4. **Tick data cost and latency**: Real-time NSE tick feeds are sold by
   authorised data vendors at significant premiums. We will need to evaluate
   whether we need co-location proximity or whether a cloud-hosted vendor feed
   is adequate for our latency requirements (live P&L alerts, not HFT).

## Team & resources

- Engineers available: 4 (2 senior — Python, distributed systems; 2 mid — Python/SQL)
- Relevant skills on the team: 1 dedicated data engineer (Kafka, Airflow,
  TimescaleDB); no quant/data science in-house yet
- Budget: ₹3–5 lakh/month (~$3,600–6,000/month) at launch, scaling to ₹8–10
  lakh/month (~$9,600–12,000/month) as AUM grows. Bloomberg Terminal is out of
  scope at these prices. No existing data vendor contracts — starting from zero.
- Runway: Series A funded, ~$3.2M raised, 22 months of runway
- Expected scale: dozens of RIA/family-office clients at launch (each ₹50cr–2,000cr
  AUM), platform-wide AUM scaling toward ₹10,000 crore over 18 months — the
  point at which the budget ceiling above steps up
- Procurement process: no formal procurement function yet — the CTO signs off
  directly on vendor contracts once a shortlist exists; expect roughly 1–2 weeks
  from shortlist to signed agreement at this stage

## Constraints

- Compliance regimes that apply: SEBI Research Analyst and Investment Adviser
  regulations; AMFI norms for mutual fund NAV distribution
- Data sensitivity: raw price/index data itself is not sensitive, but client
  portfolio data mapped to those prices is. We need to know how each vendor
  handles data ingested into their platforms — do they train models on it? What
  are their data processing agreements?
- Data residency requirements: prefer data storage and processing in AWS
  ap-south-1 (Mumbai) — some enterprise clients will ask for this in contracts
- Required certifications a vendor must already have: current NSE/BSE
  authorisation as a commercial real-time/historical data vendor (NSE and BSE
  each publish and maintain an authorised-vendor list — e.g. TrueData, Global
  Datafeeds, and Accord Fintech's ACE Datafeed are current examples) plus
  demonstrated SEBI-compliant market-data redistribution terms. ISO 27001 is
  preferred for any vendor touching client-portfolio-linked data but not yet a
  hard contractual requirement.
- Existing stack this must fit into: Python/FastAPI on AWS EKS (Kubernetes);
  PostgreSQL + TimescaleDB for time-series; S3 for cold storage; Kafka (MSK) for
  real-time events; Airflow for batch pipelines; AWS ap-south-1 (Mumbai)
- Systems/APIs this must integrate with: REST/WebSocket ingestion feeding Kafka
  (MSK) topics, landing in TimescaleDB for time-series queries, with
  Airflow-orchestrated batch jobs for corporate-actions reconciliation
- Timeline hard stop: **8 weeks** — historical OHLCV + corporate actions must be
  working in staging. Wealth manager onboarding begins in week 10 and client P&L
  needs to be live by then. 3 months: real-time/delayed feed stable in
  production. 6 months: tick-level intraday data for the alerts feature.

## Customization

Medium. The data itself is standard market data serving every wealth-manager
client identically — no per-tenant customization of the data. But corporate
actions and index-composition history need to be mapped cleanly into our
internal TimescaleDB schema and Kafka event contracts, which is real
integration work regardless of vendor.

## What matters most

Data quality and accuracy over cost. We are not trying to save money by cutting
corners on data quality — one wrong IRR figure shown to a wealth manager client
costs us the contract and is a legal liability for them. If there is a viable
"adopt open-source + self-host" path that satisfies the regulatory constraint,
we want to understand it honestly, including the ongoing maintenance burden —
not just the sticker price.

## Reversibility

What would make us switch: a pattern of corporate-actions errors surfaced by
clients, an SLA breach on uptime or latency for the intraday-alerts path, the
vendor losing its NSE/BSE authorisation or falling out of SEBI compliance, or a
pricing jump that breaks our ₹8–10 lakh/month ceiling as AUM scales. Lock-in
sensitivity is high — we do not want a switch to be a multi-month data
migration, so we prefer vendors with portable, standard API contracts
(REST/WebSocket) over proprietary SDKs that embed vendor logic deep in our code.

## Portfolio / reuse

The same market-event stream (corporate actions, earnings, rating changes) that
this ingestion pipeline produces is also the input to the semantic-alerts
feature in our vector-database work (see `input-vector-db-fintech.md`) — that
feature embeds these events for nearest-neighbour matching against client
portfolios. Whatever we build or buy here should be reusable as that pipeline's
upstream source rather than standing up a second, parallel ingestion path.
