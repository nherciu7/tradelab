# Data

## Free sources (downloaded by `scripts/stocks/fetch_free.py`)

| Source | What | Used for |
|---|---|---|
| SEC Financial Statement Data Sets (quarterly zips, 2009q2+) | Every XBRL 10-K/10-Q number as filed, with its acceptance time | Fundamentals as first reported, dated by acceptance |
| SEC Insider Transactions Data Sets (quarterly zips, 2006q1+) | Forms 3/4/5 | Insider tests; a point-in-time ticker ↔ company map |
| SEC bulk `submissions.zip` | Every company's filing history (form, date, 8-K items) | Earnings dates, merger filings, Form 25 delistings, company metadata |
| SEC `companyfacts.zip` | All XBRL facts per company | Point-in-time share counts and public float |
| SEC `company_tickers_exchange.json` | Current tickers | Company matching |
| Ken French Data Library | FF5 and momentum factors, NYSE size breakpoints, size and momentum portfolios | Benchmarks, size buckets, the V0 gate |
| FRED | Moody's AAA yield, CPI, T-bill, EUR/USD | Graham screens, deposits in EUR |

The SEC asks every automated client to send a `User-Agent` with a name and an e-mail and to stay under 10 requests a second; the downloader does both (set `SEC_USER_AGENT` or pass `--user-agent`).

## Prices: bring your own

The tests need **survivorship-free** daily prices, meaning dead stocks included with their full history. That is licensed data and is not redistributed here. The original work used EODHD's "EOD Historical Data" plan; CRSP (via WRDS) is the academic standard. Any source works if it is converted to this layout under `data/stocks/raw/prices/`:

- `candidates.csv`: one row per series, with columns `Code, Name, Exchange, Type, delisted, Isin`. `Code` is the file name; `delisted` is 0 or 1.
- `eod/{Code}.csv.gz`: daily rows `Date, Open, High, Low, Close, Adjusted_close, Volume`. `Close` and `Volume` are **raw** (unadjusted); `Adjusted_close` is adjusted for splits and dividends.
- An `IBM` series must be present: it serves as the NYSE trading calendar.

Survivorship matters more than any other choice: a dataset of today's stocks (for example free Yahoo data) makes every backtest look better than it was (backtest trap #28), so no test may run on one. The V0 gate (`scripts/stocks/v0_validate.py`) checks that a price source reproduces Ken French's CRSP universe and momentum returns before any test runs.
