# BUILD research

10 verified claims.

## m1
- Point-in-time corporate actions data enables developers to backtest algorithms accurately without survivorship or lookahead bias. (SUPPORTED)
  > "Backtest accurately without survivorship or lookahead bias." — [Corporate Actions Data & APIs | Databento](https://databento.com/corporate-actions)

## m13
- TimescaleDB provides PostgreSQL users with automatic partitioning and full SQL support for time-series analytics. (SUPPORTED)
  > "Full SQL support, automatic partitioning" — [Honest guide to the best ClickHouse® alternatives in 2026](https://www.tinybird.co/blog/clickhouse-alternatives)
- ClickHouse is not fully ACID compliant, which is an important operational limitation to consider for transaction-heavy workloads. (PARTIAL) _[partial_evidence]_
  > "ClickHouse does not offer full ACID compliance" — [ClickHouse Alternatives 2026: Real-Time OLAP DBs](https://signoz.io/comparisons/clickhouse-alternatives/)

## m14
- The National Stock Exchange provides real-time data online through dedicated leased line circuits owned by the customer. (SUPPORTED)
  > "It is provided on-line through a dedicated leased line circuit." — [Paid Real time data](https://www.nseindia.com/static/market-data/real-time-data-subscription)
- NSE offers 15-minute delayed snapshot data files generated on a regular 1-minute interval basis. (SUPPORTED)
  > "generated with 15 minutes delay on regular 1 minute interval basis" — [Paid Real time data](https://www.nseindia.com/static/market-data/real-time-data-subscription)

## m4
- Setting up a self-hosted production ClickHouse cluster requires managing configuration of replication, sharding, and ZooKeeper coordination. (SUPPORTED)
  > "Setting up a production-ready ClickHouse® cluster involves configuring replication, sharding, and ZooKeeper coordination" — [Honest guide to the best ClickHouse® alternatives in 2026](https://www.tinybird.co/blog/clickhouse-alternatives)
- Delayed or incorrect data in data pipelines can manifest as expensive and time-consuming user-facing issues. (SUPPORTED) _[stale_cost]_
  > "Delayed or incorrect data in your pipeline can manifest in user-facing issues" — [Data Processing Pipelines](https://sre.google/workbook/data-processing/)

## m9
- SEBI mandates that no real-time price data be shared with third parties except for orderly market functioning or regulatory requirements. (PARTIAL) _[partial_evidence]_
  > "no real time price data is shared with any third party" — [New SEBI Norms for sharing of real time price data to third parties](https://taxguru.in/sebi/new-sebi-norms-sharing-real-time-price-data-parties.html)
- Agreements for sharing real-time price data with third parties must be reviewed by the MII or intermediary Board annually. (PARTIAL) _[partial_evidence]_
  > "reviewed by the Board of the MIIs or market intermediaries at least once" — [New SEBI Norms for sharing of real time price data to third parties](https://taxguru.in/sebi/new-sebi-norms-sharing-real-time-price-data-parties.html)
- SEBI guidelines allow market price data to be shared for investor education only with a one-day lag. (PARTIAL) _[partial_evidence]_
  > "with a lag of 1 day." — [New SEBI Norms for sharing of real time price data to third parties](https://taxguru.in/sebi/new-sebi-norms-sharing-real-time-price-data-parties.html)

## Dimension coverage
- ✓ m1 Strategic differentiation / moat — 1 claim(s)
- ✗ m2 Proprietary-data generation — 0 claim(s)
- ✗ m3 Total cost — build ★ — 0 claim(s)
- ✓ m4 Total cost — maintenance (the bloat curve) ★ — 2 claim(s)
- ✗ m6 Time-to-value ★ — 0 claim(s)
- ✗ m7 Resource & talent availability — 0 claim(s)
- ✗ m8 Reversibility / switching cost — 0 claim(s)
- ✓ m9 Data ownership / sensitivity / compliance ★ — 3 claim(s)
- ✗ m10 Customization need vs. availability — 0 claim(s)
- ✗ m11 Focus / core-value alignment — 0 claim(s)
- ✓ m13 Vendor viability / lock-in risk — 2 claim(s)
- ✓ m14 Integration complexity ★ — 2 claim(s)

## Coverage gaps
- thin content: https://www.bseindia.com/downloads1/Information_Products_Pricing_Sheet.pdf
- thin content: https://marketdata.bseindia.com/
- fetch failed: https://niftyindices.com/offerings/data-subscription (ReadTimeout)
- thin content: https://www.sebi.gov.in/legal/circulars/may-2024/norms-for-sharing-of-real-time-price-data-to-third-parties_83572.html
- fetch failed: https://nsdl.co.in/downloadables/pdf/2024-0067-Policy-SEBI_Circular_on_Norms_for_sharing_of_real_time_price_data_to_third_parties.pdf (TooManyRedirects)
- thin content: https://www.cdslindia.com/downloads/Publications/Communique/DP-282-SEBI-CIR-NORMS-FOR-SHARING-OF-REAL-TIME-PRICE-DATA-TO-THIRD-PAR-TIES.pdf
- fetch failed: https://medium.com/@writeronepagecode/engineering-a-stock-prediction-pipeline-building-a-robust-trading-pipeline-with-python-and-ta-lib-8a72400ef726 (HTTPStatusError)
- fetch failed: https://pandorafms.com/blog/best-databases/ (HTTPStatusError)
- thin content: https://www.reddit.com/r/programming/comments/1bvzfhr/how_weve_saved_98_in_cloud_costs_by_writing_our/
- thin content: https://www.youtube.com/watch?v=yjZagoLekWc
- no evidence for priority dimension m3 (Total cost — build)
- no evidence for priority dimension m6 (Time-to-value)