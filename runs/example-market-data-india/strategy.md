# Strategy — recommendation: Buy-then-extend

**Recommendation:** buy_then_extend

Given the strict 4-week timeline and severe legal liability regarding adjusted corporate actions, licensing a commercial API for compliant market data ingestion is necessary. The startup can securely satisfy SEBI and NSE data regulations by buying the raw feed, and then extend this foundation by building its proprietary institutional-grade analytics using local query engines over portable data formats.

## Decisive factors
- **Timeline and Staging Deadlines** — A 4-week hard stop renders building direct, compliant exchange feeds from scratch impossible; a commercial API is needed immediately to populate the data warehouse.
- **Regulatory Licensing and Data Accuracy** — SEBI and NSE strictly prohibit unauthorized market data redistribution. Paying for an authorized API prevents legal liability regarding inaccurate, scraped corporate actions.
- **Architectural Decoupling** — The buy-then-extend approach allows the startup to cleanly decouple the purchased API feed from their proprietary analytics logic by storing the ingested data in an open Parquet format.

## Path dossiers

### Build
**Pros:**
- Building in-house analytics with DuckDB leverages a free, open-source local query engine that has zero external dependencies. [5d773c], [5e8677], [ffd90a]
- Running the IB Gateway on a Hetzner VPS allows for extremely cost-efficient direct data ingestion at roughly $4 to $6 per month. [e58a3e], [461520]
**Cons:**
- Indian market data is licensed rather than owned, and redistributing or sharing it publicly without explicit written authorization is prohibited. [49305c], [24da7d]
- Native data ingestion requires the operational overhead of managing a running IB Gateway instance. [461520]
**Key risks:**
- Relying on homegrown pipelines without explicit vendor data agreements risks violating SEBI's regulations for investment advisors and restricted data sharing policies. [ef96f5], [9f8c49]
**Reversibility:** Moderate to difficult; custom ingestion infrastructure built around IB Gateway represents a sunk engineering investment if regulatory compliance later forces a pivot to licensed feeds. [461520]
**Evidence:**
  - [5d773c] "Free and open source" — [ClickHouse vs DuckDB 2026: Analytical Database Comparison | Tasrie IT Services](https://tasrieit.com/blog/clickhouse-vs-duckdb-2026)
  - [5e8677] "Zero external dependencies" _[partial_evidence]_ — [ClickHouse vs DuckDB 2026: Analytical Database Comparison | Tasrie IT Services](https://tasrieit.com/blog/clickhouse-vs-duckdb-2026)
  - [ffd90a] "DuckDB is the local query engine for research and backtesting" — [market-data-warehouse/CLAUDE.md at main · joemccann/market-data-warehouse](https://github.com/joemccann/market-data-warehouse/blob/main/CLAUDE.md)
  - [e58a3e] "IB Gateway runs on a Hetzner CPX11 VPS (~$4-6/mo)" _[stale_cost, price_conflict]_ — [market-data-warehouse/CLAUDE.md at main · joemccann/market-data-warehouse](https://github.com/joemccann/market-data-warehouse/blob/main/CLAUDE.md)
  - [461520] "You need a running IB Gateway for ingestion." — [GitHub - joemccann/market-data-warehouse: A local-first financial data warehouse for universe-scale market data.](https://github.com/joemccann/market-data-warehouse)
  - [49305c] "All market data remains the intellectual property of the exchanges" — [Market Data API | Live, SnapChat, Options Chain, Option Greeks](https://www.truedata.in/market-data-apis)
  - [24da7d] "Redistribution, resale, or public sharing of data is not allowed" — [Market Data API | Live, SnapChat, Options Chain, Option Greeks](https://www.truedata.in/market-data-apis)
  - [ef96f5] "Securities and Exchange Board of India (Investment Advisers) Regulations, 2013" — [SEBI | Regulations](https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=3&smid=0)
  - [9f8c49] "Restricted Data (Second Basket)- This includes non-public data that cannot be shared" _[partial_evidence]_ — [SEBI Data Sharing Policy 2024](https://www.metalegal.in/post/sebi-data-sharing-policy-2024)

### Buy
**Pros:**
- Commercial APIs like EODHD provide ready-to-use endpoints for mutual fund fundamentals, adjusted close prices, and EOD OHLCV data across over 60 global exchanges. [388b7c], [c72106], [e70d8d]
- Alpha Vantage is an officially licensed market data provider for US exchanges like NASDAQ. [0b3263]
**Cons:**
- SEBI rules strictly prohibit market intermediaries from sharing real-time price data with third parties unless formal agreements are in place. [904a1c], [9aa35d]
- Trading members are explicitly prohibited by the NSE data policy from redistributing market data without formal permission. [2f5382]
**Key risks:**
- Even with a paid feed, NSE data cannot be used to build custom or composite financial indices without obtaining a completely separate license, which could block the startup's core platform value. [7b83f1]
**Reversibility:** High; adopting a commercial vendor like EODHD solely for data ingestion makes it relatively simple to swap providers if data quality or licensing terms become unfavorable. [c72106]
**Evidence:**
  - [388b7c] "Retrieves comprehensive fundamental data for mutual funds via EODHD API." — [EODHD APIs for AI agents — 11 tools, one platform | Definable](https://definable.ai/apps/eodhd_apis/)
  - [c72106] "Returns OHLCV (Open, High, Low, Close, Volume) data plus adjusted close prices" — [EODHD APIs for AI agents — 11 tools, one platform | Definable](https://definable.ai/apps/eodhd_apis/)
  - [e70d8d] "provides affordable access to global equities across 60+ exchanges" — [EODHD Provider¶](https://ml4trading.io/docs/data/providers/eodhd/)
  - [0b3263] "NASDAQ celebrates Alpha Vantage as its officially licensed US market data provider" — [Free Stock APIs in JSON & Excel](https://www.alphavantage.co/)
  - [904a1c] "prohibiting stock market participants from sharing real-time price data with third parties" — [New SEBI Rules on Sharing Real-time Stock Market Data](https://www.truedata.in/blog/sebi-norms-on-sharing-real-time-price-data)
  - [9aa35d] "they must do so by entering into formal agreements with those entities." — [New SEBI Rules on Sharing Real-time Stock Market Data](https://www.truedata.in/blog/sebi-norms-on-sharing-real-time-price-data)
  - [2f5382] "Trading Members and Subscribers shall not be permitted to redistribute any Market Data" — [NSE Data Sharing & Usage Policy](https://www.nseindia.com/static/market-data/nse-data-policy)
  - [7b83f1] "use Market Data, in whole or in part to create any financial index" — [NSE Data Sharing & Usage Policy](https://www.nseindia.com/static/market-data/nse-data-policy)

### Buy-then-extend
**Pros:**
- The startup can license EODHD's APIs to ingest compliant adjusted close and mutual fund data, while maintaining analytical independence by using Parquet as the system of record. [388b7c], [c72106], [d282cb]
- The differentiating portfolio analytics layer can be aggressively optimized by extending the ingested data using ClickHouse for production benchmarking or DuckDB for local querying. [a18c10], [ffd90a]
**Cons:**
- Commercial APIs impose rate limits (EODHD limits paid users to 100,000 calls/day; Alpha Vantage caps free users at 500 calls/day), which may bottleneck historical data backfills for staging. [52d0ba], [0ea9ac]
- There is a notable conflict in vendor pricing tiers, ranging from EODHD at $19.99/month to Alpha Vantage scaling up to $249.99/month. [f834a5], [797767]
**Key risks:**
- Building analytical models and custom indices on top of the purchased API feed still legally requires acquiring a separate index creation license from the NSE. [7b83f1]
**Reversibility:** Moderate; relying on APIs for raw materials while cleanly abstracting the storage layer into Parquet means the core portfolio logic is portable across future data providers. [c72106], [d282cb]
**Evidence:**
  - [388b7c] "Retrieves comprehensive fundamental data for mutual funds via EODHD API." — [EODHD APIs for AI agents — 11 tools, one platform | Definable](https://definable.ai/apps/eodhd_apis/)
  - [c72106] "Returns OHLCV (Open, High, Low, Close, Volume) data plus adjusted close prices" — [EODHD APIs for AI agents — 11 tools, one platform | Definable](https://definable.ai/apps/eodhd_apis/)
  - [d282cb] "Parquet is the system of record, not DuckDB" — [market-data-warehouse/CLAUDE.md at main · joemccann/market-data-warehouse](https://github.com/joemccann/market-data-warehouse/blob/main/CLAUDE.md)
  - [a18c10] "ClickHouse for production benchmarking" — [market-data-warehouse/CLAUDE.md at main · joemccann/market-data-warehouse](https://github.com/joemccann/market-data-warehouse/blob/main/CLAUDE.md)
  - [ffd90a] "DuckDB is the local query engine for research and backtesting" — [market-data-warehouse/CLAUDE.md at main · joemccann/market-data-warehouse](https://github.com/joemccann/market-data-warehouse/blob/main/CLAUDE.md)
  - [52d0ba] "100,000 calls/day" _[stale_cost]_ — [EODHD Provider¶](https://ml4trading.io/docs/data/providers/eodhd/)
  - [0ea9ac] "Alpha Vantage caps you at 500 API calls per day on the free tier." — [Alpha Vantage vs FCS API — Best Free Forex Crypto Stock Market Data API 2026 - FCSAPI](https://fcsapi.com/blog/alpha-vantage-vs-fcs-api-best-free-forex-crypto-stock-market-data-api-2026)
  - [f834a5] "EOD All World | $19.99/mo" _[partial_evidence, stale_cost]_ — [EODHD Provider¶](https://ml4trading.io/docs/data/providers/eodhd/)
  - [797767] "Pricing ranges from $49.99/mo to $249.99/mo" _[price_conflict]_ — [Best Stock Market Data APIs of 2026 | Abstract API](https://www.abstractapi.com/guides/other/best-stock-apis)
  - [7b83f1] "use Market Data, in whole or in part to create any financial index" — [NSE Data Sharing & Usage Policy](https://www.nseindia.com/static/market-data/nse-data-policy)

### Adopt & self-host
**Pros:**
- The platform can leverage the free, open-source DuckDB engine for local analysis, or scale real-time analytics using a distributed open-source ClickHouse architecture. [5d773c], [c838ba], [2b475a]
- Git-like versioning and community-backed primitives can be integrated by adopting open-source tools such as Dolt, lakeFS, or DuckLake. [ac073a], [6ea050], [a43f09]
**Cons:**
- Self-hosting analytics pipelines requires significant setup time, such as configuring ClickHouse materialized views to optimize ingestion times. [5879dd]
- While tools like DuckDB are free and open-source, the evidence does not highlight any managed commercial twins to alleviate the operational burden of self-hosting them at scale. [5d773c]
**Key risks:**
- Self-hosting robust database software does not circumvent the fundamental prohibition against sharing real-time price data without SEBI compliant formal agreements. [904a1c], [9aa35d]
**Reversibility:** Hard; hardening a distributed database like ClickHouse natively requires a steep operations investment that cannot be easily unwound to meet a 4-week staging deadline. [c838ba]
**Evidence:**
  - [5d773c] "Free and open source" — [ClickHouse vs DuckDB 2026: Analytical Database Comparison | Tasrie IT Services](https://tasrieit.com/blog/clickhouse-vs-duckdb-2026)
  - [c838ba] "ClickHouse is a distributed columnar database" — [ClickHouse vs DuckDB 2026: Analytical Database Comparison | Tasrie IT Services](https://tasrieit.com/blog/clickhouse-vs-duckdb-2026)
  - [2b475a] "ClickHouse scales across multiple nodes" — [ClickHouse vs DuckDB 2026: Analytical Database Comparison | Tasrie IT Services](https://tasrieit.com/blog/clickhouse-vs-duckdb-2026)
  - [ac073a] "Dolt stands out with the fastest PR merge times (~30 min median)." _[partial_evidence]_ — [Git for Data Applied](https://motherduck.com/blog/git-for-data-part-2/)
  - [6ea050] "lakeFS leads in total PR creators (178), reflecting a broad contributor base." — [Git for Data Applied](https://motherduck.com/blog/git-for-data-part-2/)
  - [a43f09] "DuckLake reached GA in April 2026" — [Git for Data Applied](https://motherduck.com/blog/git-for-data-part-2/)
  - [5879dd] "StockHouse uses materialized views to pre-aggregate data as it's ingested." — [Building StockHouse: Real-time market analytics with ClickHouse](https://clickhouse.com/blog/building-stockhouse)
  - [904a1c] "prohibiting stock market participants from sharing real-time price data with third parties" — [New SEBI Rules on Sharing Real-time Stock Market Data](https://www.truedata.in/blog/sebi-norms-on-sharing-real-time-price-data)
  - [9aa35d] "they must do so by entering into formal agreements with those entities." — [New SEBI Rules on Sharing Real-time Stock Market Data](https://www.truedata.in/blog/sebi-norms-on-sharing-real-time-price-data)

## Challenger's counter-recommendation: Buy
_The engine's own second-best and the challenger independently converged on this path._
**Wins when:**
- if meeting the strict 4-week timeline by piping data directly into the existing TimescaleDB stack is prioritized over the architectural overhead of building custom data warehouse extensions

A pure 'buy' approach avoids the engineering overhead of building a custom data warehouse extension, cleanly meeting the strict 4-week staging deadline. By licensing a commercial API like EODHD, the startup gains immediate access to global equities across more than 60 exchanges [e70d8d], mutual fund fundamentals [388b7c], and end-of-day OHLCV data with pre-adjusted close prices [c72106]—directly solving the corporate action liability risk. With up to 100,000 API calls per day on paid tiers [52d0ba], the team can simply ingest this managed feed into their existing PostgreSQL and TimescaleDB infrastructure rather than taking on the burden of engineering new local query capabilities.
  - [e70d8d] "provides affordable access to global equities across 60+ exchanges" — [EODHD Provider¶](https://ml4trading.io/docs/data/providers/eodhd/)
  - [388b7c] "Retrieves comprehensive fundamental data for mutual funds via EODHD API." — [EODHD APIs for AI agents — 11 tools, one platform | Definable](https://definable.ai/apps/eodhd_apis/)
  - [c72106] "Returns OHLCV (Open, High, Low, Close, Volume) data plus adjusted close prices" — [EODHD APIs for AI agents — 11 tools, one platform | Definable](https://definable.ai/apps/eodhd_apis/)
  - [52d0ba] "100,000 calls/day" _[stale_cost]_ — [EODHD Provider¶](https://ml4trading.io/docs/data/providers/eodhd/)

## Open questions
- Does EODHD possess explicit NSE/BSE authorization allowing its customers to redistribute corporate actions and historical OHLCV data to wealth management end-clients?
- Are there specific vendor data processing agreements available with EODHD to protect client portfolio data when mapping against historical prices?
- What is the exact financial and timeline cost to acquire an NSE license for creating custom financial indices out of vendor-supplied data?
