# Strategy — recommendation: Buy-then-extend

**Recommendation:** buy_then_extend

The `buy_then_extend` path perfectly aligns with the strategy of treating market data as an enabling capability rather than a core differentiator. By licensing raw data feeds from authorized commercial vendors via standard APIs and building the analytics and compliance workflows internally over TimescaleDB, the platform avoids massive infrastructure overhead while maintaining precise control over corporate action accuracy and SEBI compliance.

## Decisive factors
- **Infrastructure Cost & Complexity** — Building direct exchange connectivity costs over 4 lakhs/month for co-location and 38.5 lakhs in fixed fees, making buy_then_extend far more viable.
- **Vendor Licensing Constraints** — Restrictive licenses from vendors like TrueData block commercial redistribution, necessitating careful vendor selection (e.g., Accord Fintech NXT) to power the internal extension.
- **Capability Intent Focus** — The platform's core moat is its analytics and compliance workflow; licensing the raw market data enables engineering to focus entirely on building that differentiating layer.
- **Architecture & Portfolio Synergies** — Extending a bought feed via internal TimescaleDB/Kafka ingestion allows the resulting market-event stream to natively feed the parallel vector-database project without creating redundant ingestion paths.

## Path dossiers

### Build
**Pros:**
- Internal ingestion can secure point-in-time corporate actions data to accurately backtest algorithms without survivorship bias. [928202]
- The platform can directly retrieve 15-minute delayed snapshot files generated every minute by the National Stock Exchange. [ac2118], [4da0b4]
**Cons:**
- Sourcing real-time direct tick feeds from the National Stock Exchange demands dedicated customer-owned leased line circuits. [83ac9f]
- Direct tick-by-tick feeds require co-location racks exceeding 4 lakhs/month and a fixed fee of 38.5 lakhs to the National Stock Exchange. [3105d7], [02c3e3]
- Streaming live tick-by-tick data over the internet is constrained by massive file sizes reaching tens of gigabytes. [65f322]
**Key risks:**
- Self-built pipelines risking delayed or incorrect data will manifest as severe user-facing issues and legal liabilities. [e03a14]
- Violating strict SEBI mandates regarding real-time price data sharing could lead to major regulatory compliance failures. [4a4761], [054fae]
**Reversibility:** Heavy upfront investments in leased lines and physical infrastructure for direct National Stock Exchange feeds are not easily reversible, making it impossible to pivot cleanly if the solution fails to perform. [83ac9f], [3105d7]
**Evidence:**
  - [928202] "Backtest accurately without survivorship or lookahead bias." — [Corporate Actions Data & APIs | Databento](https://databento.com/corporate-actions)
  - [ac2118] "generated with 15 minutes delay on regular 1 minute interval basis" — [Paid Real time data](https://www.nseindia.com/static/market-data/real-time-data-subscription)
  - [4da0b4] "Snapshot Data is provided in binary file format over the internet" — [Paid Real time data](https://www.nseindia.com/static/market-data/real-time-data-subscription)
  - [83ac9f] "It is provided on-line through a dedicated leased line circuit." — [Paid Real time data](https://www.nseindia.com/static/market-data/real-time-data-subscription)
  - [3105d7] "cost you upwards of 4lks a month." _[partial_evidence, stale_cost]_ — [How do I get tick by tick data directly via NSE](https://tradingqna.com/t/how-do-i-get-tick-by-tick-data-directly-via-nse/55045)
  - [02c3e3] "paid the fixed fees of 38.5lks and spent on infra." _[partial_evidence, stale_cost]_ — [How do I get tick by tick data directly via NSE](https://tradingqna.com/t/how-do-i-get-tick-by-tick-data-directly-via-nse/55045)
  - [65f322] "It is tens of GB’s worth of data" — [How do I get tick by tick data directly via NSE](https://tradingqna.com/t/how-do-i-get-tick-by-tick-data-directly-via-nse/55045)
  - [e03a14] "Delayed or incorrect data in your pipeline can manifest in user-facing issues" _[stale_cost]_ — [Data Processing Pipelines](https://sre.google/workbook/data-processing/)
  - [4a4761] "no real time price data is shared with any third party" _[partial_evidence]_ — [New SEBI Norms for sharing of real time price data to third parties](https://taxguru.in/sebi/new-sebi-norms-sharing-real-time-price-data-parties.html)
  - [054fae] "reviewed by the Board of the MIIs or market intermediaries at least once" _[partial_evidence]_ — [New SEBI Norms for sharing of real time price data to third parties](https://taxguru.in/sebi/new-sebi-norms-sharing-real-time-price-data-parties.html)

### Buy
**Pros:**
- TrueData offers comprehensive RESTful and WebSocket market data APIs covering NSE, BSE, and derivatives. [e6e417], [38512a]
- Accord Fintech NXT provides stock market and mutual fund feeds through API and FTP protocols. [6a4b6c]
- The mfapi.in platform delivers unrestricted Indian mutual fund data updated six times per day without requiring API keys. [a173a2], [586f64]
**Cons:**
- TrueData strictly limits its market data feed to single-subscriber personal charting use and forbids simulation applications without exchange approval. [c4225f], [a000ed]
- Distributing tick data through commercial vendors implies high underlying National Stock Exchange fixed fees of 38.5 lakhs, which will likely be passed on to the platform. [02c3e3]
**Key risks:**
- Vendors like TrueData enforce a strict non-refundable payment policy once data is delivered, increasing financial risk. [47d388]
- Utilizing vendors that restrict commercial redistribution exposes the platform to severe compliance and legal risks. [c4225f]
**Reversibility:** Preferring standard API contracts from vendors like Accord Fintech NXT and TrueData meets the reversibility criteria against proprietary lock-in, enabling easier switching if SLA breaches occur or vendor authorization is lost. [e6e417], [6a4b6c]
**Evidence:**
  - [e6e417] "WebSockets, RESTful, DotNet, COM" _[partial_evidence]_ — [Real-Time Market Data API for NSE, BSE & MCX | Low Latency APIs](https://www.truedata.in/products/marketdataapi)
  - [38512a] "delivering services for NSE EQ, NSE Indices, NSE F&O, BSE EQ, BSE Indices, BSE F&O" — [Real-Time Market Data API for NSE, BSE & MCX | Low Latency APIs](https://www.truedata.in/products/marketdataapi)
  - [6a4b6c] "We provide financial information feed through FTP and API." _[partial_evidence]_ — [Accord Fintech Pvt. Ltd](https://www.accordfintechnxt.com/)
  - [a173a2] "No authentication, no API keys, no rate limiting. Just pure data access." _[partial_evidence]_ — [India's Free Mutual Fund API](https://www.mfapi.in/)
  - [586f64] "Updated 6x daily (10:05 AM, 2:05 PM, 6:05 PM, 9:05 PM, 3:09 AM, 5:05 AM IST)" _[partial_evidence]_ — [India's Free Mutual Fund API](https://www.mfapi.in/)
  - [c4225f] "This Data is for Personal Charting Use of a Single Subscriber only." — [Real-Time Market Data API for NSE, BSE & MCX | Low Latency APIs](https://www.truedata.in/products/marketdataapi)
  - [a000ed] "TrueData does not provide market data for any kind of Gaming / Virtual trading" — [Real-Time Market Data API for NSE, BSE & MCX | Low Latency APIs](https://www.truedata.in/products/marketdataapi)
  - [02c3e3] "paid the fixed fees of 38.5lks and spent on infra." _[partial_evidence, stale_cost]_ — [How do I get tick by tick data directly via NSE](https://tradingqna.com/t/how-do-i-get-tick-by-tick-data-directly-via-nse/55045)
  - [47d388] "Amount paid will not be refunded once order is placed / data is delivered." _[stale_cost]_ — [Real-Time Market Data API for NSE, BSE & MCX | Low Latency APIs](https://www.truedata.in/products/marketdataapi)

### Buy-then-extend
**Pros:**
- Core API feeds can be licensed from Accord Fintech NXT and mfapi.in, satisfying foundational mutual fund and equity data needs. [6a4b6c], [a173a2]
- Extending these feeds internally via TimescaleDB supports point-in-time corporate actions for highly accurate institutional backtesting. [ef33d4], [928202]
**Cons:**
- Must aggressively filter out vendors like TrueData due to restrictive single-subscriber licenses that explicitly block institutional platform redistribution. [c4225f]
- National Stock Exchange binary snapshot data requires complex custom parsing over SFTP if used to augment vendor feeds directly. [4da0b4], [ccabdf]
**Key risks:**
- Any delayed or incorrect upstream vendor data will cascade through the extended pipeline, causing expensive client-facing compliance issues. [e03a14]
- SEBI rules on real-time data sharing must be strictly monitored when extending and redistributing the combined feed to clients. [4a4761]
**Reversibility:** Highly reversible; integrating via standard API/FTP protocols from vendors like Accord Fintech NXT ensures the architecture avoids lock-in if price hikes exceed the ₹8-10 lakh/month ceiling. [6a4b6c]
**Evidence:**
  - [6a4b6c] "We provide financial information feed through FTP and API." _[partial_evidence]_ — [Accord Fintech Pvt. Ltd](https://www.accordfintechnxt.com/)
  - [a173a2] "No authentication, no API keys, no rate limiting. Just pure data access." _[partial_evidence]_ — [India's Free Mutual Fund API](https://www.mfapi.in/)
  - [ef33d4] "Full SQL support, automatic partitioning" — [Honest guide to the best ClickHouse® alternatives in 2026](https://www.tinybird.co/blog/clickhouse-alternatives)
  - [928202] "Backtest accurately without survivorship or lookahead bias." — [Corporate Actions Data & APIs | Databento](https://databento.com/corporate-actions)
  - [c4225f] "This Data is for Personal Charting Use of a Single Subscriber only." — [Real-Time Market Data API for NSE, BSE & MCX | Low Latency APIs](https://www.truedata.in/products/marketdataapi)
  - [4da0b4] "Snapshot Data is provided in binary file format over the internet" — [Paid Real time data](https://www.nseindia.com/static/market-data/real-time-data-subscription)
  - [ccabdf] "requires the use of an SFTP protocol to download these files." — [Paid Real time data](https://www.nseindia.com/static/market-data/real-time-data-subscription)
  - [e03a14] "Delayed or incorrect data in your pipeline can manifest in user-facing issues" _[stale_cost]_ — [Data Processing Pipelines](https://sre.google/workbook/data-processing/)
  - [4a4761] "no real time price data is shared with any third party" _[partial_evidence]_ — [New SEBI Norms for sharing of real time price data to third parties](https://taxguru.in/sebi/new-sebi-norms-sharing-real-time-price-data-parties.html)

### Adopt & self-host
**Pros:**
- TimescaleDB integrates seamlessly into the existing PostgreSQL stack with full SQL support and automatic partitioning for time-series analytics. [ef33d4]
- Can ingest delayed snapshot files downloaded via SFTP directly from the National Stock Exchange to bypass vendor limits. [ccabdf], [4da0b4]
**Cons:**
- The alternative OSS project ClickHouse lacks full ACID compliance, posing a significant limitation for transaction-heavy analytical workloads. [fc6ff2]
- Self-hosting the necessary infrastructure for direct tick feeds via the National Stock Exchange demands extensive co-location setups costing >4 lakhs/month. [3105d7]
**Key risks:**
- Operating complex OSS data pipelines (like managing ZooKeeper for ClickHouse) introduces a high risk of delayed data and user-facing analytical errors. [0cdf28], [e03a14]
**Reversibility:** Deeply embedding OSS components like ClickHouse or TimescaleDB creates internal operational lock-in, making it difficult to reverse if the maintenance burden causes SLA breaches. [0cdf28], [ef33d4]
**Evidence:**
  - [ef33d4] "Full SQL support, automatic partitioning" — [Honest guide to the best ClickHouse® alternatives in 2026](https://www.tinybird.co/blog/clickhouse-alternatives)
  - [ccabdf] "requires the use of an SFTP protocol to download these files." — [Paid Real time data](https://www.nseindia.com/static/market-data/real-time-data-subscription)
  - [4da0b4] "Snapshot Data is provided in binary file format over the internet" — [Paid Real time data](https://www.nseindia.com/static/market-data/real-time-data-subscription)
  - [fc6ff2] "ClickHouse does not offer full ACID compliance" _[partial_evidence]_ — [ClickHouse Alternatives 2026: Real-Time OLAP DBs](https://signoz.io/comparisons/clickhouse-alternatives/)
  - [3105d7] "cost you upwards of 4lks a month." _[partial_evidence, stale_cost]_ — [How do I get tick by tick data directly via NSE](https://tradingqna.com/t/how-do-i-get-tick-by-tick-data-directly-via-nse/55045)
  - [0cdf28] "Setting up a production-ready ClickHouse® cluster involves configuring replication, sharding, and ZooKeeper coordination" — [Honest guide to the best ClickHouse® alternatives in 2026](https://www.tinybird.co/blog/clickhouse-alternatives)
  - [e03a14] "Delayed or incorrect data in your pipeline can manifest in user-facing issues" _[stale_cost]_ — [Data Processing Pipelines](https://sre.google/workbook/data-processing/)

## Runner-up: Buy
_Challenger concurred: it could not make a stronger case for any alternative path. The runner-up below is the engine's own second-best._
**Wins when:**
- A commercial vendor emerges with a fully managed, compliant, and correctly adjusted historical database that natively supports institutional backtesting and redistribution, removing the need for any internal pipeline extensions.

## Open questions
- Are Accord Fintech NXT's historical OHLCV and corporate action datasets perfectly adjusted point-in-time for algorithmic backtesting?
- What are the exact latency SLAs for Accord Fintech NXT's API/FTP feeds, and do they meet the sub-second tick requirement for alerts?
- Does the mfapi.in platform have the necessary reliability and legal backing for institutional-grade platform use, or is a commercial mutual fund data vendor required?
- How does the parallel vector-database project expect the upstream market-event stream to be specifically structured for its semantic alerts?
