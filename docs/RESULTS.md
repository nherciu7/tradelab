# Round S report: long-only US stock selection (25 Sep 2026)

**Verdict: nothing passed. 0 of 8 pre-registered tests cleared the bar.** One idea came close (Graham net-nets, S4) and is worth paper-trading, not money. (Round S2 below: the stock hunt has ended.)

Everything was run on survivorship-free prices (50,879 live and dead US stocks from EODHD, cleaned and validated by V0: `docs/stocks/V0_REPORT.md`) and SEC filings dated by when they became public. Each test was pre-registered in `docs/PREREG.md` (Round S) before it ran. Main sample: Feb 2012 – Aug 2026 (size-matched benchmarks need market caps, which the free SEC data has from 2012).

## Results

Implementable = 10 names, €400 + €35 a month, zero-commission broker with 0.15% FX a side, half the bid-ask spread a side. Excess = monthly return over equal-weighted stocks of the same size, after costs.

| Test | Idea | Academic (all names, gross) | 10 names after costs | Verdict |
|---|---|---|---|---|
| S8 | Stocks that just jumped the most (lottery stocks) | −0.40% a month (t −1.4) | **−5.6%** (t −6.2) | FAIL, as the literature predicts: avoid them |
| S1 | 2+ insiders buying within 30 days | +0.16% (t 1.3) | −0.41% (t −1.2) | FAIL: real but tiny since 2012 |
| S3 | Microcap drift after strong earnings reactions | +0.64% (t 3.3) | −0.64% (t −1.4) | FAIL after costs (its placebo was flawed: see Round S2) |
| S4 | Graham net-nets (price < ⅔ of net current assets) | +0.98% (t 1.1) | +0.02% (t 0.0) | FAIL, closest call: see below |
| S5 | Graham P/E ≤ 7, sell at +50% or 2 years | −0.05% (t −0.3) | −0.54% (t −1.3) | FAIL: value exposure, no edge |
| S2 | "Opportunistic" insider purchases | −0.28% (t −1.2) | −1.58% (t −5.6) | FAIL: monthly churn costs ~1% a month |
| S7 | Piotroski F-score 8–9 among cheap stocks | −0.07% (t −0.2) | −0.58% (t −2.4) | FAIL: low scores did better |
| S6 | Graham's enterprising-investor screen | −0.82% (t −1.5) | −0.83% (t −1.9) | FAIL, underpowered (25 stocks in 11 years) |

The pass bar was t > +2.8 on the 10-name portfolio after costs, positive in both halves, beating the size-matched benchmark, and failing placebos.

## What it means in euros

- **No test here earns more than a broad basket of similar-sized stocks after costs.** At €400–2,000, the best implementable result (S4, +0.02% a month over its benchmark) is worth about €0–0.40 a month. That is noise.
- **The costs are mostly spreads, not commissions.** IBKR and the zero-commission broker gave nearly identical results, because small stocks cost 0.5–2% to get in and out. Anything that trades monthly loses about 1% a month to that alone (S2).
- **Buying the stocks that just "exploded" is the fastest way to lose money here.** In the S8 test, $7,632 of deposits over 14 years ended at $356.

## The closest call: Graham net-nets (S4)

- Net-nets beat random stocks of the same size over the same holding periods (+24% vs +12% per holding, p = 0.015), and the cheapest were best (dose-response +2.0%, +0.6%, +0.5% a month).
- But t = 1.1 over the full sample: the first half (2012–2019) was negative and everything came in 2019–2026. There are only about 6 net-nets in a typical month, so a 10-name portfolio sits partly in cash, and it fell −61% at its worst.
- **Suggestion:** log it forward on paper (no money) and re-test when more years exist.

## Leads for the next round (not results)

1. ~~Microcap continuation after big moves without news~~: **withdrawn.** It came from a flaw in S3's placebo, and it failed when tested (Round S2, L1).
2. **Earnings-surprise (SUE) drift in microcaps** (S3 secondary): +1.45% a month, t 3.3, academic. Forward log only (no earlier data to test it on).

## Things this round fixed or learned

- V0 found eleven data problems in the vendor data (the eight worst are now mistakes #45–#52 in `docs/BACKTEST_TRAPS.md`). Running the first test found three engine bugs: a same-day exit, an unpaid delisting, and a biased event placebo. All are fixed and covered by tests (42 in `tests/stocks/`).

---

# Round S2 (25 Sep 2026): the final stock round

**Verdict: L1 failed out of sample, so the stock hunt has ended.** The only surviving work is two paper screens in the forward log (no money).

## S9 Part A: what happens to $1–5 stocks (descriptive)

1.4 million stock-months, 2000–2025, outcomes within 12 months (delisting returns included):

| | < $1 | **$1–5** | $5+ |
|---|---|---|---|
| Doubled | 14.4% | **12.6%** | 4.0% |
| Halved | 37.1% | **23.2%** | 9.0% |
| Delisted | 15.6% | 8.2% | 4.7% |
| Median return | −26% | **−7%** | +5% |

About one $1–5 stock in eight doubles within a year, but one in four halves, and the typical one loses 7%. Young ones (listed under 3 years) are worse: median −19.5%, 32.5% halved. As a group, $1–5 stocks earned no more than $5+ stocks (+0.09% a month, t 0.33). Chart: `reports/stocks/s9a_base_rates.png`.

## L1: microcap continuation after big moves without news

**The lead came from my own mistake.** S3's placebo picked, for each big earnings reaction, the nearest big non-news move, often in the weeks *before* it. So the placebo's holding window often contained the later earnings jump. Those events earned +6.6% a month (t 10.2); all the other placebo events lost money. Now mistake #53 in `docs/BACKTEST_TRAPS.md`.

**Audit, 2012–2026 (in-sample), event types by SEC filings within 3 days:**

| Event type | Events | Excess / month | t |
|---|---|---|---|
| M&A filing | 1,770 | −1.11% | −2.34 |
| Other 8-K | 3,782 | −0.39% | −1.57 |
| No filing | 11,190 | −0.50% | −2.11 |
| Frozen rule (M&A out, volume on signal and entry days) | 15,865 | −0.51% | −2.24 |

The alpha on FF5 + momentum + 52-week-high is −0.48% (t −3.11).

**Out-of-sample, 2000–2011 (run once, after V0 checks passed; microcaps by a dollar-volume proxy that matches the market-cap definition on 89% of stock-months):**

| Version | Events | Months | Mean excess / month | t | Win % | Halves | FF5+UMD alpha (t) | Cost drag | Names | Worst DD |
|---|---|---|---|---|---|---|---|---|---|---|
| Academic (all events) | 16,638 | 144 | −0.45% | −1.41 | 42% | −0.19 / −0.71 | −0.24% (−1.20) | – | – | −72% |
| **10 names, zero-commission** | 16,638 | 144 | **−1.73%** | −2.65 | 40% | −1.85 / −1.61 | −1.76% (−2.52) | 0.61% | 9.8 | −96% |
| 10 names, IBKR | 16,638 | 144 | −1.86% | −2.83 | 40% | −2.05 / −1.67 | −1.88% (−2.67) | 0.68% | 9.8 | −97% |

By event type out of sample: no filing −0.54% (t −1.63); other 8-K +0.05% (t 0.09); M&A excluded by the rule (316 events had a filing only after the signal).

**In euros:** buying microcaps after a big jump would have lost money in both periods. The 10-name version turned €400 + €35 a month (about $6,500 deposited, 2000–2011) into about $3,700.

**S9 Part B** (the composite test for $1–5 stocks): **not run, hunt closed.**

## What continues (paper only)

- **Graham net-nets:** a quarterly screen, logged with prices, re-tested in 2029.
- **SUE drift in microcaps:** a quarterly screen, logged only, never tested (2012–2026 is used up and the free SEC data starts in 2009).
- Both run as private quarterly paper screens (not part of this repository).
