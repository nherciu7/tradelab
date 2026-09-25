# tradelab: a research lab built to make trading ideas fail honestly

A one-person research project on a simple question: **can a retail investor with a few hundred euros find a mechanical trading edge that survives honest testing and real costs?**

About **150 pre-registered ideas** were tested across futures, ETFs and US stocks. **Three survived.** This repository holds the stock-selection half of the work: the data pipeline, the validation gate, the test engine, every stock pre-registration and result, the 53 ways the project fooled itself, and three case studies of fake edges that were caught.

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

| | Ideas | Survivors |
|---|---|---|
| Futures, ETFs and calendar flows | ~143 | 3 |
| US stocks (Round S: 8 tests; Round S2: 1 out-of-sample test) | 9 | 0 |
| **Total** | **~152** | **3** |

The three survivors are all **forced flows**: someone must trade because of a rule, a mandate or an index method, regardless of price. In general terms:
- **A. Month-end Treasury index flow.** 289 months, net t 7.25.
- **B. Turn-of-month equity flow.** 391 months, t 5.36.
- **C. Russell index reconstitution flow.** 27 events, t 3.33.

Their exact rules are not published here. They are being paper-traded forward before any money is used.

**US stocks, 2012–2026** (details in [`docs/RESULTS.md`](docs/RESULTS.md)):

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

## Reproduce

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

- **Licensed price data** and the downloader for it.
- **The futures and ETF research code**, and the exact rules of the three surviving systems.
- Anything personal: accounts, brokers, the paper-trading log.

## Disclaimer

Research code, published to show a method. Nothing here is investment advice or a recommendation to trade. Every number is a backtest unless it says otherwise.
