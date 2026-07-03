# Capability need

## The company and what we're building

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

## The specific capability we need to buy or build

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

## Why this is genuinely hard in India

1. **Regulatory licensing**: NSE and BSE data is exchange-proprietary. SEBI's
   policies require that any commercial product redistributing market data must
   obtain exchange authorisation. You cannot legally scrape NSE or use screen-
   scraping workarounds for a commercial product. This constraints the BUILD path:
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

## Team

- 4 engineers: 2 senior (Python, distributed systems), 2 mid (Python/SQL)
- 1 dedicated data engineer (experience with Kafka, Airflow, TimescaleDB)
- No quant/data science in-house yet

## Existing stack

- Backend: Python/FastAPI on AWS EKS (Kubernetes)
- Data store: PostgreSQL + TimescaleDB for time-series, S3 for cold storage
- Streaming: Kafka (MSK) for real-time events
- Compute: AWS (ap-south-1, Mumbai region — important for data residency)
- Orchestration: Airflow for batch pipelines

## Budget and runway

- Series A funded: ~$3.2M raised, 22 months of runway
- Data infrastructure budget: we can spend ₹3–5 lakh per month (~$3,600–6,000/month)
  at launch, scaling to ₹8–10 lakh/month (~$9,600–12,000/month) as AUM grows.
  Bloomberg Terminal is out of scope at these prices.
- We have no existing data vendor contracts. Starting from zero.

## Constraints

- **Regulatory**: Must use SEBI/exchange-authorised data sources only for any
  commercial redistribution of price data. Vendors must have NSE/BSE data
  licensing agreements.
- **Data residency**: Prefer data storage and processing in AWS ap-south-1
  (Mumbai). Some enterprise clients will ask for this in contracts.
- **Lock-in sensitivity**: High. We do not want to be locked into a single
  vendor where switching cost is a multi-month data migration. Prefer vendors
  with portable, standard API contracts (REST/WebSocket) rather than proprietary
  SDKs that embed vendor logic deep in our code.
- **Sensitivity**: Price data itself is not sensitive, but client portfolio data
  (mapped to prices) is. We need to know how each vendor handles data ingested
  into their platforms — do they train models on it? What are their data
  processing agreements?

## Timeline

- **4 weeks**: Must have historical OHLCV + corporate actions working in staging.
  Wealth manager onboarding begins in week 6 and client P&L needs to be live.
- **3 months**: Real-time/delayed feed stable in production.
- **6 months**: Tick-level intraday data for alerts feature.

## What a good outcome looks like

We want to walk away with a clear recommendation: which vendor(s) to contract,
what it will cost at launch vs. at ₹10,000 crore AUM, and what we would need to
build ourselves versus buy. If there is a viable "adopt open-source + self-host"
path that satisfies the regulatory constraint, we want to understand it honestly
including the ongoing maintenance burden. We are not trying to save money by
cutting corners on data quality — one wrong IRR figure shown to a wealth manager
client costs us the contract.

## Additional context
(none provided)

run_id: 20260615-021109-7a9aae
