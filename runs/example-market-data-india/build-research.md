# BUILD research

22 verified claims.

## m13
- The open-source database Dolt achieves a median PR merge time of roughly 30 minutes. (PARTIAL) _[partial_evidence]_
  > "Dolt stands out with the fastest PR merge times (~30 min median)." — [Git for Data Applied](https://motherduck.com/blog/git-for-data-part-2/)
- The open-source project lakeFS demonstrated broad community engagement with 178 total PR creators in February 2026. (SUPPORTED)
  > "lakeFS leads in total PR creators (178), reflecting a broad contributor base." — [Git for Data Applied](https://motherduck.com/blog/git-for-data-part-2/)
- DuckLake achieved general availability in April 2026. (SUPPORTED)
  > "DuckLake reached GA in April 2026" — [Git for Data Applied](https://motherduck.com/blog/git-for-data-part-2/)

## m14
- The market-data-warehouse system uses DuckDB as its local query engine for research and backtesting. (SUPPORTED)
  > "DuckDB is the local query engine for research and backtesting" — [market-data-warehouse/CLAUDE.md at main · joemccann/market-data-warehouse](https://github.com/joemccann/market-data-warehouse/blob/main/CLAUDE.md)
- ClickHouse is used within the market-data-warehouse project for production benchmarking. (SUPPORTED)
  > "ClickHouse for production benchmarking" — [market-data-warehouse/CLAUDE.md at main · joemccann/market-data-warehouse](https://github.com/joemccann/market-data-warehouse/blob/main/CLAUDE.md)
- Ingesting data within the market-data-warehouse requires a running instance of IB Gateway. (SUPPORTED)
  > "You need a running IB Gateway for ingestion." — [GitHub - joemccann/market-data-warehouse: A local-first financial data warehouse for universe-scale market data.](https://github.com/joemccann/market-data-warehouse)
- On a single machine, DuckDB often matches or exceeds ClickHouse performance when querying local data. (SUPPORTED)
  > "On a single machine with local data, DuckDB often matches or exceeds ClickHouse" — [ClickHouse vs DuckDB 2026: Analytical Database Comparison | Tasrie IT Services](https://tasrieit.com/blog/clickhouse-vs-duckdb-2026)
- ClickHouse is designed as a distributed columnar database for real-time analytics. (SUPPORTED)
  > "ClickHouse is a distributed columnar database" — [ClickHouse vs DuckDB 2026: Analytical Database Comparison | Tasrie IT Services](https://tasrieit.com/blog/clickhouse-vs-duckdb-2026)
- ClickHouse can scale across multiple nodes. (SUPPORTED)
  > "ClickHouse scales across multiple nodes" — [ClickHouse vs DuckDB 2026: Analytical Database Comparison | Tasrie IT Services](https://tasrieit.com/blog/clickhouse-vs-duckdb-2026)
- Unlike client-server architectures, DuckDB is an in-process engine with zero external dependencies. (PARTIAL) _[partial_evidence]_
  > "Zero external dependencies" — [ClickHouse vs DuckDB 2026: Analytical Database Comparison | Tasrie IT Services](https://tasrieit.com/blog/clickhouse-vs-duckdb-2026)
- The StockHouse streaming market analytics app optimizes query times by using ClickHouse materialized views to pre-aggregate data at ingestion. (SUPPORTED)
  > "StockHouse uses materialized views to pre-aggregate data as it's ingested." — [Building StockHouse: Real-time market analytics with ClickHouse](https://clickhouse.com/blog/building-stockhouse)
- The default Apache Superset installation does not include a ClickHouse driver. (SUPPORTED)
  > "By default apache doesn't come with Clickhouse driver installed" — [Building a Real-time Data Pipeline with Go, Kafka, ClickHouse, and Apache Superset](https://www.artigencetech.com/post/building-a-real-time-data-pipeline-with-go-kafka-clickhouse-and-apache-superset)

## m3
- Running the IB Gateway on a Hetzner CPX11 VPS costs approximately $4 to $6 per month. (SUPPORTED) _[stale_cost]_
  > "IB Gateway runs on a Hetzner CPX11 VPS (~$4-6/mo)" — [market-data-warehouse/CLAUDE.md at main · joemccann/market-data-warehouse](https://github.com/joemccann/market-data-warehouse/blob/main/CLAUDE.md)
- DuckDB is free and open source. (SUPPORTED)
  > "Free and open source" — [ClickHouse vs DuckDB 2026: Analytical Database Comparison | Tasrie IT Services](https://tasrieit.com/blog/clickhouse-vs-duckdb-2026)

## m8
- In the market-data-warehouse architecture, Parquet serves as the system of record rather than DuckDB. (SUPPORTED)
  > "Parquet is the system of record, not DuckDB" — [market-data-warehouse/CLAUDE.md at main · joemccann/market-data-warehouse](https://github.com/joemccann/market-data-warehouse/blob/main/CLAUDE.md)

## m9
- Indian market data is licensed rather than owned, remaining the intellectual property of the stock exchanges. (SUPPORTED)
  > "All market data remains the intellectual property of the exchanges" — [Market Data API | Live, SnapChat, Options Chain, Option Greeks](https://www.truedata.in/market-data-apis)
- Redistributing, reselling, or sharing market data publicly is prohibited without explicit written authorization. (SUPPORTED)
  > "Redistribution, resale, or public sharing of data is not allowed" — [Market Data API | Live, SnapChat, Options Chain, Option Greeks](https://www.truedata.in/market-data-apis)
- Investment advisors in India are governed under the SEBI (Investment Advisers) Regulations, 2013. (SUPPORTED)
  > "Securities and Exchange Board of India (Investment Advisers) Regulations, 2013" — [SEBI | Regulations](https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=3&smid=0)
- Research analysts in India are governed under the SEBI (Research Analysts) Regulations, 2014. (PARTIAL) _[partial_evidence]_
  > "Securities and Exchange Board of India (Research Analysts) Regulations, 2014" — [SEBI | Regulations](https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=3&smid=0)
- SEBI's 2024 New Circular outlines a standardized policy for Market Infrastructure Institutions (MIIs) sharing data for academic and research publications. (PARTIAL) _[partial_evidence]_
  > "standardized policy for MIIs to share separate data specifically for research" — [SEBI Data Sharing Policy 2024](https://www.metalegal.in/post/sebi-data-sharing-policy-2024)
- Under the New Circular, SEBI segments market data into two distinct categories. (PARTIAL) _[partial_evidence]_
  > "This policy divides the data into two categories:" — [SEBI Data Sharing Policy 2024](https://www.metalegal.in/post/sebi-data-sharing-policy-2024)
- Restricted data contains sensitive information and is not permitted to be shared under SEBI's guidelines. (PARTIAL) _[partial_evidence]_
  > "Restricted Data (Second Basket)- This includes non-public data that cannot be shared" — [SEBI Data Sharing Policy 2024](https://www.metalegal.in/post/sebi-data-sharing-policy-2024)

## Dimension coverage
- ✗ m1 Strategic differentiation / moat — 0 claim(s)
- ✗ m2 Proprietary-data generation — 0 claim(s)
- ✓ m3 Total cost — build ★ — 2 claim(s)
- ✗ m4 Total cost — maintenance (the bloat curve) ★ — 0 claim(s)
- ✗ m6 Time-to-value ★ — 0 claim(s)
- ✗ m7 Resource & talent availability — 0 claim(s)
- ✓ m8 Reversibility / switching cost — 1 claim(s)
- ✓ m9 Data ownership / sensitivity / compliance ★ — 7 claim(s)
- ✗ m10 Customization need vs. availability — 0 claim(s)
- ✗ m11 Focus / core-value alignment — 0 claim(s)
- ✓ m13 Vendor viability / lock-in risk — 3 claim(s)
- ✓ m14 Integration complexity ★ — 9 claim(s)

## Coverage gaps
- fetch failed: https://altinity.com/webinarspage/using-dlt-to-move-data-from-duckdb-to-clickhouse (HTTPStatusError)
- thin content: https://www.reddit.com/r/dataengineering/comments/1ao16gb/who_uses_duckdb_for_real/
- fetch failed: https://towardsdev.com/building-a-financial-data-pipeline-with-alpha-vantage-and-clickhouse-5860d1e5a4be (HTTPStatusError)
- fetch failed: https://medium.com/@keshavagrawal/building-a-real-time-data-pipeline-with-go-kafka-clickhouse-and-apache-superset-02a4d9c1529d (HTTPStatusError)
- fetch failed: https://www.wikiwand.com/en/articles/Stock_exchange (HTTPStatusError)
- fetch failed: https://wiki2.org/en/Stock_exchange (HTTPStatusError)
- fetch failed: https://parthamajumdar.org/tag/india/page/34/ (HTTPStatusError)
- thin content: https://www.bseindia.com/downloads1/SEBI_circular_Policy_Sharing_Data.pdf
- no evidence for priority dimension m4 (Total cost — maintenance (the bloat curve))
- no evidence for priority dimension m6 (Time-to-value)