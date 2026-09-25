# tradelab: a research lab built to make trading ideas fail honestly

**The write-up: https://nherciu7.github.io/tradelab/**

A one-person research project on a simple question: **can a retail investor with a few hundred euros find a mechanical trading edge that survives honest testing and real costs?**

**139 documented ideas** (about 150 counting quick checks) were tested across futures, ETFs and US stocks. **Three survived.** This repository holds the stock-selection half of the work (the data pipeline, the validation gate, the test engine, every stock pre-registration and result), the 53 ways the project fooled itself, three case studies of fake edges that were caught, the exact rules of the three survivors, and the public website with its QA suite.

**AI-assisted.** I directed the research and made the decisions; Claude (Anthropic's AI) wrote most of the code and ran the tests. The protocol below, the trap list and the automated checks exist because an AI writes code fast and is sometimes confidently wrong. Every number on the site comes from files in the research repo and is checked by tests.

## The protocol

Every idea went through the same steps, in this order:

1. **Pre-registration.** Before any result is seen, the rule, universe, dates, entry and exit timing, costs, benchmark, placebo and pass bar are written down and committed (`docs/PREREGISTRATIONS.md`, and each script's docstring). Results are appended below the entry, never edited into it.
2. **The pass bar (all four, or the idea is dead):**
   - t > **+2.8** (signed in the trade's direction; Newey-West for overlapping holdings). The bar is high because many ideas were tested.
   - the same sign in **both halves** of the sample;
   - it beats **its own benchmark** (size-matched stocks, never cash);
   - the pre-registered **placebo fails** (shifted dates, fake windows, random portfolios of the same size on the same dates).
3. **Implementable, not academic.** The number that decides is the portfolio a small account could actually hold: 10 names, €400 plus €35 a month, bid-ask spreads, minimum commissions, FX fees, and a cap of 1% of daily dollar volume. The academic "all names, before costs" version is always reported next to it.
4. **Walk-forward for any parameter.** Parameters are chosen on past years only and tested on the next year; the probability of backtest overfitting (PBO, CSCV) is reported when many configurations are searched. Every variant counts in the tally.
5. **Audit anything too good.** A result with t > 5, a Sharpe above 2 or more than 30% a year is audited against the trap list before anyone sees it.

## Scoreboard

| | Documented ideas | Survivors |
|---|---|---|
| Futures, ETFs and calendar flows | 130 | 3 |
| US stocks (Round S: 8 tests; Round S2: 1 out-of-sample test) | 9 | 0 |
| **Total** | **139** (about 150 with quick checks) | **3** |

## The three that held up (exact rules)

Three rules kept passing: in both halves of the data, against their benchmarks, and against placebos. Every figure is a backtest, after costs, before taxes. All three are being paper-traded in public from now on (the scoreboard is on the site).

**A. Month-end Treasuries.** Bond indices add newly issued Treasuries at month end, so index funds and liability-matching investors must buy in the final days.
- Rule: at the close three trading days before the last trading day of the month (L−3, from the CBOT futures calendar), **sell one Micro 2-Year Yield future (2YY)** for the current contract month. It is quoted in yield, so selling it is long bond prices. It cash-settles at the 3:00 pm ET fixing on L: no exit order, no stop or target (disaster stop only). Flat the rest of the month. One contract per about €600 of equity.
- Backtest per contract ($2.50 round trip): Aug 2002 to Aug 2026, 289 months, **+$28.82 a month**, t 6.92, 66.1% of months positive, worst month −$175, worst intramonth dip −$278; median calendar year about €270, 1 of 23 years negative. Jun 1976 to Dec 2001 (never used to find the rule): +$24.42 a month, t 2.71, 10 of 25 years negative.
- Stop if the cumulative result per contract is below −$161 / −$123 / +$36 after 6 / 12 / 24 month-ends, or 4 or fewer winners of the first 12.

**B. Turn of the month in stock indices.** The cause is **not** known (five explanations were tested and failed).
- Rule: buy SPY, QQQ, IWM, Dow, DAX and Euro Stoxx 50 at the close of the last trading day of the month; sell at the close of the 4th trading day of the new month. Skip an index when its 21-day volatility is above the 80th percentile of its past 252 days. Stop at 0.75 × ATR(14) below the first day's open. Weight by inverse 60-day volatility. Code: `totm(before=1, after=3, vol_pctile=0.80, vol_len=21, sl_atr=0.75)`, weighted as in `sysb_mechanism.monthly()`.
- Backtest (4 bps each way): Feb 1991 to Sep 2026, 391 months, **+43.1 bps a month**, t 5.36, 50.1% of months positive, worst month −4.0%, deepest fall −12.7%.
- Stop if cumulative below −505 / −562 / −492 bps after 6 / 12 / 24 turns, or a drawdown worse than −19%.

**C. Russell reconstitution.** Index funds must hold the rebuilt Russell indices at the reconstitution close.
- Rule: from the close two sessions before the reconstitution close (last Friday of June), long IWM / short SPY in equal dollars; close at the reconstitution close. Then the reverse (short IWM / long SPY) until the close five sessions later. December 2026 (first semi-annual event): long Wed 9 Dec close to Fri 11 Dec close, reverse to Fri 18 Dec close.
- Backtest (8 bps per leg-trade): 27 June events, 2000 to 2026, **+58.8 bps per event** into the close, t 3.33, 70.4% positive, worst −76 bps. The unwind adds +55 bps on average but is not significant on its own (t 1.65).
- Stop if cumulative below −137 / −124 bps after 2 / 4 events.

Related research found afterwards is linked at the bottom of each system page. Full rules, risks and charts: [System A](https://nherciu7.github.io/tradelab/systems/a/) · [System B](https://nherciu7.github.io/tradelab/systems/b/) · [System C](https://nherciu7.github.io/tradelab/systems/c/).

## US stocks: nothing passed

2012–2026 (details in [`docs/RESULTS.md`](docs/RESULTS.md)):

| Test | Idea | All names, before costs | 10 names, after costs | Verdict |
|---|---|---|---|---|
| S8 | Stocks with the biggest one-day jump (lottery stocks) | −0.40%/month | −5.6% | FAIL (as the literature predicts) |
| S1 | Clusters of insider purchases | +0.16% | −0.41% | FAIL |
| S3 | Post-earnings drift in microcaps | +0.64% (t 3.3) | −0.64% | FAIL |
| S4 | Graham net-nets | +0.98% (t 1.1) | +0.02% | FAIL (closest call) |
| S5 | Graham: P/E ≤ 7 | −0.05% | −0.54% | FAIL |
| S2 | "Opportunistic" insiders | −0.28% | −1.58% | FAIL |
| S7 | Piotroski F-score among cheap stocks | −0.07% | −0.58% | FAIL |
| S6 | Graham's enterprising-investor screen | −0.82% | −0.83% | FAIL (underpowered) |
| L1 | Microcap continuation after big moves, **out of sample 2000–2011** | −0.45% | −1.73% | FAIL |

Also descriptive: of US stocks priced $1–5, 12.6% doubled within a year and 23.2% halved; the median lost 7% ([`docs/figures/s9a_base_rates.png`](docs/figures/s9a_base_rates.png)).

## 53 backtest traps

[`docs/BACKTEST_TRAPS.md`](docs/BACKTEST_TRAPS.md) lists every way this project produced a wrong result at least once: look-ahead in order logic, costs with the wrong sign, a sign-agnostic pass bar, survivorship bias, fundamentals dated by the period end, vendor splices, placebos with look-ahead, and more. Each fix is in the code, and most have a test.

## Case studies

1. [A t = 5.74 intraday "edge" that was a look-ahead bug](docs/case_studies/01_ict_fake_edge.md). The engine peeked at the fill deadline; the placebos passed too; walk-forward out-of-sample t was +0.90.
2. [A placebo that manufactured a fake lead](docs/case_studies/02_placebo_lookahead.md). The placebo dates were chosen next to future earnings jumps; the tradable rule lost money in and out of sample.
3. [Eleven vendor-data problems found by a validation gate](docs/case_studies/03_v0_vendor_data.md). The pipeline had to reproduce Ken French's CRSP numbers before any strategy could run; the first run correlated 0.47, the last 0.984.

## The website (`site/`)

A static Next.js site (App Router, TypeScript, Tailwind), exported to plain HTML and deployed to GitHub Pages by `.github/workflows/site.yml`. The text lives in `site/content/*.md` and every number in `site/data/*.json`, so the copy can be edited without touching code. Numbers appear in the Markdown as tokens such as `{{a_typical_year}}`, defined in `site/content/numbers.yml`.

```bash
cd site
npm ci
npm run build                     # static export to site/out (BASE_PATH=/tradelab by default)
npm run serve                     # http://localhost:4173/tradelab/
npm run preview:copy              # the Markdown with numbers filled in, in content/_preview/
npm run scan:copy                 # style scan of the Markdown (banned words, em dashes, ...)
npx playwright install chromium   # once
npx playwright test               # the QA suite, against the built site
```

`site/data/*.json` is exported from the private research repo by `scripts/site/export_site_data.py`, and a pytest there checks each exported number against its source. Only derived results are exported: monthly strategy results per contract, per-event results and summary tables, never raw prices.

The Playwright suite (`site/tests/`) checks, on every build:
- every number rendered with a `data-testid` equals its value in `site/data`, plus a second hand-written check of the headline numbers;
- the built HTML contains none of the banned words and patterns from the style guide, at most one em dash per page, no emoji (allow-list with a reason per entry: `site/qa/style-allowlist.json`);
- the AI-assisted line and the disclaimer on every page;
- all internal links and anchors resolve; no console errors or failed requests; no cookies or third-party requests;
- Open Graph and Twitter tags, and the 1200×630 preview image;
- no horizontal scroll at 375 px, with full-page screenshots at 375 and 1280 px kept as test artifacts;
- WCAG 2.1 AA with axe-core (including colour contrast) in light and dark mode; every chart has alt text and a data table;
- the money calculators for three fixed inputs (checked against numbers the Python exporter computed), and the multi-year projection;
- no invisible control characters in the site's source files (backtest trap #52).

The deploy job runs only if the research tests, the copy scan, the build and the Playwright suite all pass. Known and accepted: `npm audit` reports a moderate issue in `fflate` inside `satori`, which only runs at build time on the site's own font files.

## Reproduce the research

```bash
pip install -r requirements.txt
python -m pytest -q                      # 42 tests, synthetic data, no downloads needed
```

The full pipeline needs about 10 GB of disk:

```bash
# 1. free data: SEC (bulk files), FRED, Ken French. The SEC requires a name and an e-mail.
export SEC_USER_AGENT="Your Name you@example.com"
python scripts/stocks/fetch_free.py french fred sec --user-agent "$SEC_USER_AGENT"
python scripts/stocks/build_sec.py submissions fsds insider companyfacts

# 2. prices: survivorship-free daily prices are licensed data and are NOT included.
#    Bring your own in the format described in docs/DATA.md.

# 3. build the security master and panels, then run the validation gate (V0)
python scripts/stocks/build_panel.py spans secmaster panel
python scripts/stocks/v0_validate.py        # -> reports/stocks/v0_summary.json, v0_counts.png

# 4. one stock test (S8, the lottery-stock test; needs only prices and SEC data)
python scripts/stocks/s8_max_lottery.py     # -> reports/stocks/s8_results.json
```

The fundamental tests (S4–S7) also need `python -c "from tradelab.stocks import fundamentals; fundamentals.build()"`.

## Code map

```
tradelab/stocks/
  french.py fred.py            Ken French and FRED readers
  sec_fsds.py                  SEC Financial Statement Data Sets -> first-reported values, dated by acceptance
  sec_insider.py               SEC insider Forms 3/4/5 -> transactions and a point-in-time ticker map
  sec_submissions.py           SEC filing history (8-K items, merger filings, Form 25)
  sec_companyfacts.py          point-in-time share counts and public float
  secmaster.py                 price series -> company, listing periods, duplicates, delistings
  panel.py                     cleaned daily and monthly panels (splices, bad prints, market-cap checks)
  universe.py                  the pre-registered universe and size buckets
  costs.py                     spread estimators (Abdi-Ranaldo, Corwin-Schultz) and broker costs
  portfolio.py                 calendar-time and implementable (small account) engines
  evaluate.py                  one evaluation path for every test: benchmark, placebo, alpha, verdict
  stats.py                     Newey-West t, factor regressions, the pass bar
  fundamentals.py rules.py     point-in-time fundamentals, trailing-12-month flows, Graham-style holding rules
scripts/stocks/                downloads, builds, V0, and one script per test (pre-registration in each docstring)
tests/stocks/                  pytest: statistics vs statsmodels, spread estimators on simulated markets,
                               engine timing, data-cleaning rules, point-in-time and first-reported logic
docs/                          pre-registrations and results, V0 report, traps, case studies
```

## What is not here

- **Licensed price data** (EODHD, Dukascopy, Yahoo) and the downloader for it. The site only carries results derived from it.
- **The futures and ETF research code.** The rules of the three survivors are published above; the code that found them stays private.
- Anything personal: accounts, brokers, keys. The site's scoreboard shows only the paper trades' dates and results.

## Disclaimer

Research code and results, published to show a method. Not investment advice and not a recommendation to trade; I'm not a licensed adviser. Every number is a backtest unless it says "paper": hypothetical, before taxes and currency costs, and past results don't guarantee future results. I hold no positions in these instruments as of 26 September 2026.
