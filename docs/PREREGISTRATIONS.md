# Pre-registrations and results: US stock rounds (Round S, Round S2)

Each entry was written and committed before its script ran; results are appended below each entry, never edited into it. Earlier rounds (futures, prop-firm rules) are not part of this public copy.

---

# Round S: long-only US stock selection (Phase S; registered 25 Sep 2026)

Plan: `docs/stocks/STOCK_PLAN.md`. Data validated by V0 (`docs/stocks/V0_REPORT.md`). Every S-test is evaluated by the same code, `tradelab/stocks/evaluate.py`, with these rules, fixed before any S-test is run:

**Data and universe.** EODHD survivorship-free daily prices (live and dead US common stocks) and SEC filings. Universe as in `tradelab/stocks/universe.py` and STOCK_PLAN s3.3: listed on NYSE / Nasdaq / NYSE American, a US reporting company (10-K/10-Q or S-1 in the prior 400 days, no 20-F/40-F), not a blank-check company, month-end close ≥ $1, 20-day median dollar volume ≥ $100k, ≤ 20% zero-volume days, one share class per company. Size buckets from Ken French's NYSE breakpoints (micro < p20 ≤ small < p50 ≤ large).

**Timing.** Information up to a month-end close; bought at the close of the next trading day; held while selected; sold at the close of the first trading day after the last selected month. Event tests trade at the close of the first trading day after the public date (Form 4 filing date, 10-K/10-Q acceptance date, 8-K filing date).

**Costs, both scenarios reported:** (a) IBKR tiered, $0.0035/share, min $0.35, max 1% of value, plus $0.002/share fees; (b) zero commission + 0.15% FX on each buy and each sell. Both pay half the Abdi–Ranaldo spread a side (floored at 0.05%, 1% if missing), the SEC fee on sales, and are capped at 1% of 20-day median dollar volume. **(b) is the pass case.**

**Implementable portfolio:** N ∈ {5, 10, 20} slots (primary N = 10), €400 at the start + €35 on the first trading day of each month at the historical EUR/USD rate (FRED DEXUSEU), fractional shares, delisting returns by the Shumway convention (primary) and the actual-price variant (reported). Monthly time-weighted returns.

**Benchmark:** the size-matched equal-weighted universe (each month, the EW next-month return of each size bucket, weighted by the portfolio's own bucket mix at formation). Market caps exist from about 2012, so **the primary sample for size-matched tests starts with formation month 2012-01** (holding months Feb 2012 – Aug 2026, 175 months), unless a test states otherwise.

**Pass bar (all four):** (1) signed Newey-West t of the monthly excess (implementable after costs, scenario b, primary N) > +2.8, lags = holding months (≥ 1); (2) positive mean excess in both halves; (3) mean excess > 0 (beats the size-matched benchmark); (4) the random-portfolio placebo fails: the real gross excess beats at least 95% of 1,000 random portfolios with the same bucket mix on the same dates (p < 0.05), plus any test-specific placebo.

**Always reported:** the academic all-names version, FF5 + UMD alpha (over the T-bill and of the excess; alpha t < 2 = "known factor exposure"), names held, % of months invested, cost drag, worst drawdown, months underwater, both cost scenarios, N = 5 / 10 / 20.

**Tally.** Round S continues the docs/BACKTEST_TRAPS.md count (about 143 ideas, 3 survivors). Each S-test is one idea; every variant run is listed in its entry.

## S8: "stocks that might explode" (the MAX / lottery test) (registered 25 Sep 2026)

**Source checked:** Bali, Cakici & Whitelaw (2011), JFE 99, 427–446 (`data/raw/papers/bali_cakici_whitelaw_2011_max.pdf`). NYSE/Amex/Nasdaq, Jul 1962 – Dec 2005: high-minus-low MAX decile **−1.03% a month VW (t −2.83)**, four-factor alpha −1.18% (t −4.71); **EW −0.65% (t −1.83)**, alpha −0.66% (t −2.31).

**Prediction (from the literature):** the top-MAX stocks *underperform*. This test exists to show, on our data, whether buying the stocks that "might explode" works. Reported honestly either way.

**Rule.** Each month m, MAX = the largest daily total return during m (cleaned daily data). Among stocks eligible at the end of m, the **top MAX decile** is selected.
- Academic: the whole top decile, equal-weighted, held month m+1.
- Implementable: the N stocks with the highest MAX (N = 5, 10, 20), bought at the next close, held while they stay in the monthly top N.

**Sample:** formation months 2012-01 to 2026-07 (holding Feb 2012 – Aug 2026). Pass bar and benchmark as in the Round S rules (size-matched EW).

**Placebo:** random portfolios of the same size mix on the same dates (Round S rule 4).

**Secondary, reported, not deciding:**
1. Academic top-minus-bottom MAX decile (EW), 2012–2026 and 2000–2026 (the latter against the all-eligible EW universe, since size buckets don't exist before 2012).
2. $5 price floor instead of $1.
3. Actual-price delisting returns instead of Shumway.
4. The **filter** for later tests: whether dropping the top-MAX decile improves S1–S7 is tested inside each of those tests (pre-registered there), not here.

**Variants counted:** 3 N × 2 cost scenarios + academic + 3 secondaries = 1 idea, 10 variants.

**S8 result (run 25 Sep 2026, `scripts/stocks/s8_max_lottery.py`, `reports/stocks/s8_results.json`): FAIL, in the predicted direction: the top-MAX stocks lose money.**

Two engine bugs were found and fixed before this run was accepted (both invalidated earlier runs of this script; the numbers below are the only valid ones): (1) a stock selected at the end of month m was given an exit on the same day as its entry, so almost no trades happened; (2) a held stock that stopped trading on a zero-volume exit day was never paid out (NaN equity counted as 0% months). Tests added: `tests/stocks/test_evaluate.py`, `test_portfolio.py::test_stock_that_stops_on_a_zero_volume_exit_day_is_paid_out`.

Holding months Feb 2012 – Aug 2026 (175), size-matched EW benchmark, Shumway delisting returns:

| Version | Mean excess / month | NW t | Win % | Halves | FF5+UMD alpha of excess (t) | Cost drag / month | Names | Worst DD |
|---|---|---|---|---|---|---|---|---|
| Academic: whole top decile (EW, gross) | −0.40% | −1.44 | 46% | −0.20 / −0.59 | −0.44% (−2.28) | – | ~330 | – |
| N = 10, (b) zero commission (primary) | **−5.62%** | −6.20 | 22% | −2.89 / −8.32 | −5.37% (−5.57) | 1.96% | 9.6 | −100% |
| N = 10, (a) IBKR | −6.32% | −6.90 | 22% | −3.22 / −9.38 | −6.05% (−6.24) | 2.65% | 9.6 | −100% |
| N = 5, (b) | −6.13% | −5.14 | 31% | −2.39 / −9.84 | −5.76% (−4.27) | 1.95% | 4.8 | −100% |
| N = 20, (b) | −4.98% | −7.63 | 24% | −2.83 / −7.11 | −4.68% (−6.82) | 2.04% | 19.2 | −100% |

- Gross (before costs) the 10 highest-MAX stocks returned −2.6% a month on average (median −1.6%) against a benchmark of +1.05%. Placebo p = 1.0 (random portfolios did better every time).
- Secondary: top-minus-bottom decile −0.24% / month (t −0.46) in 2012–26 and −0.52% (t −1.04) in 2000–26; top decile vs all eligible 2000–26 −0.52% (t −1.75). $5 floor: primary −4.09% (t −5.54). Actual-price delisting returns: −5.59% (t −6.12).
- The academic decile matches the verified equal-weighted literature result (−0.65%, t −1.83, 1962–2005) in sign and size; the extreme top 10 are far worse, and worse after 2019 (2021 −9.6%, 2024–26 −6% to −10% a month raw).
- Audit (|t| > 5): the biggest losers are real collapses (Mallinckrodt, Zynex, Diamond Offshore and PHI bankruptcies, LongFin fraud, Adagio/Invivyd −80% on Omicron). One pick (QXO, Jun 2024) has doubtful vendor data; 1 of 1,750 picks.
- **Plain meaning:** buying the stocks that just jumped the most lost almost all the money deposited: $7,632 of deposits (€400 + €35/month) ended at $356 in the primary version. Long-only, this is not usable; it is a list of stocks to avoid (the filter is tested inside S1–S7).

## S1: insider purchase clusters (registered 25 Sep 2026, before any S1 number was computed)

**Sources checked:** Lakonishok & Lee (2001, RFS 14:79–111): the information is in purchases, mainly in smaller firms; sales predict nothing. Cohen, Malloy & Pomorski (2012; NBER w16454 read). Alldredge & Blank (2019, *Journal of Financial Research*, not JFQA; abstract only): clustered purchases are followed by abnormal returns above 2% in the next month (1986–2014). Leads, not expectations: the sample here is 2012–2026, after publication.

**Data:** SEC Insider Transactions Data Sets, original Forms 4 only (amendments dropped), `built/insider_trans.parquet`.

**Qualifying purchase:** transaction code P (open-market or private purchase), acquired; the filing's reporting owners include an officer or a director (10%-owner-only filings excluded); security title contains "common" or "ordinary" and not preferred / warrant / option / note / unit; price > 0; trade date ≤ filing date and ≥ filing date − 365 days; **≥ $10,000 per insider per filing** (lines of one filing summed). One filing = one insider, even if it lists several owners (a director and their trust are not two insiders). Lines are aggregated per filing, so pre-2009 line-by-line reporting cannot inflate counts.

**Cluster (primary):** at each qualifying filing of an issuer, count the distinct insiders with qualifying purchases traded in the 30 calendar days up to this filing's latest trade date, using only filings already filed. The first filing at which the count reaches **2** completes a cluster. **Signal date = that filing's filing date** (never the trade date). Secondary: 3 insiders.

**Trade:** buy at the close of the first trading day after the signal date; hold **63 trading days** (primary; 21 and 126 secondary) and sell at that close. One event per issuer at a time: a new cluster at the same issuer before the holding ends is not a new event. The stock must be in the eligible universe at the end of the month before the signal (Round S universe), mapped CIK → security.

**Implementable:** N = 10 slots (primary; 5 and 20 reported), both cost scenarios, (b) decides. Same-day signals are taken by more insiders first, then larger dollar amount. **When the portfolio is full, new signals are dropped (oldest-signal-first: held positions are never replaced).**

**Sample and benchmark:** primary signals 2012-01-01 to 2026-05-31 (so every 63-day hold ends inside the data), size-matched EW benchmark on the names actually held each month; months with no position are compared with the all-eligible EW universe (cash drag counts). Halves: split at the middle month. Secondary: signals 2006–2026, academic version against the all-eligible EW universe (no size buckets before 2012), halves 2006–2015 / 2016–2026 as in the plan.

**Placebos (all must fail for a pass):**
- (a) Same firms, windows shifted back 252 trading days (same holding length): academic excess must have t < 2 and a mean below half the real one.
- (b) Sale clusters (same rules with code S, disposed): academic excess must not show positive drift (t < 2).
- (c) Random portfolios (Round S rule 4): p < 0.05.

**Pass bar:** Round S rules, NW lags = 3 (holding months).

**Secondary, reported only:** 3-insider clusters; holds of 21 and 126 days; excluding stocks in the top-MAX decile at formation (the S8 avoid-list); actual-price delisting returns.

**Variants counted:** 1 idea; 3 N × 2 costs + academic + 3 placebos + 5 secondaries.

**S1 result (run 25 Sep 2026, `scripts/stocks/s1_insider_clusters.py`, `reports/stocks/s1_results.json`): FAIL. The effect is positive but small after 2012, and the 10-name portfolio loses to its benchmark after costs.**

183,710 qualifying purchase filings (2006–2026); 9,844 cluster events in the primary sample (signals Jan 2012 – May 2026; about 220 open at any time). Size-matched benchmark, Shumway delisting returns, NW lags 3:

| Version | Mean excess / month | NW t | Win % | Halves | FF5+UMD alpha of excess (t) | Names | Worst DD |
|---|---|---|---|---|---|---|---|
| Academic, all events (EW, gross) | +0.16% | +1.27 | 56% | +0.17 / +0.14 | +0.12% (+0.80) | ~220 | – |
| N = 10, (b) (primary) | **−0.41%** | −1.24 | 46% | −0.90 / +0.08 | −0.45% (−1.26) | 9.8 | −51% |
| N = 10, (a) | −0.41% | −1.24 | 45% | −0.94 / +0.12 | −0.45% (−1.25) | 9.8 | −51% |
| N = 5, (b) | +0.30% | +0.55 | 53% | −0.42 / +1.02 | +0.24% (+0.41) | 4.9 | −49% |
| N = 20, (b) | −0.49% | −1.88 | 40% | −0.64 / −0.34 | −0.48% (−1.75) | 19.5 | −50% |

- Costs about 0.4% of equity a month; the 10-name portfolio took 6% of the signals (the rest arrived while it was full).
- Placebos behave: (a) same firms a year earlier −0.13% (t −1.02); (b) sale clusters +0.05% (t +0.65). (c) Random placebo, event-time version (added after this run because the monthly approximation counted whole entry months including pre-signal days and gave a biased p = 0.991; the verdict does not depend on it): 63-day return 5.26% vs 4.82% for random same-size stocks on the same dates, +0.44% per event, p = 0.07.
- Secondary: 3+ insiders +0.11% (t 0.66); 21-day hold +0.29% (t 1.70); 126-day hold +0.17% (t 1.64); without top-MAX stocks +0.04% (t 0.29); actual-price delisting returns +0.17% (t 1.35); 2006–2026 vs the all-eligible universe +0.25% (t 2.21, halves +0.22 / +0.28).
- **Plain meaning:** insiders buying together still tell you something, but only about 0.15–0.25% a month in 2012–2026, less than a small portfolio pays to trade it. Consistent with the literature fading after publication (Alldredge & Blank's >2% in the next month was 1986–2014).

## S3: post-earnings drift, microcaps only (registered 25 Sep 2026, before any S3 number was computed)

**Sources checked:** Martineau (2022, Critical Finance Review 11:613–646): drift non-existent for large stocks since 2006 and "only disappeared recently for microcap stocks" (abstract). Its Internet Appendix Table IA.1 (Compustat, days 2–15 after the announcement): microcap surprise rank still predicts returns in 2016–2019 (0.002 per decile rank, about 1.8% top vs bottom decile over two weeks); all-but-microcap zero or negative since 2011. So **the plan's premise ("persists in microcaps") holds only for a short window**; the plan's 60-day hold is kept as frozen, with days 2–15 as a secondary. Announcement-return drift (Chan, Jegadeesh & Lakonishok 1996; Brandt et al. 2008) is cited as background only; not re-verified.

**Announcement date (day 0 = D):** the filing date of an 8-K with Item 2.02 (original 8-K, not 8-K/A); a second 2.02 filing by the same company within 20 trading days is ignored. Companies with no 2.02 8-K in the 100 days before a 10-Q/10-K use that 10-Q/10-K filing date instead (later, so conservative). If D is not a trading day, the next trading day. **Acceptance times are not used** (the bulk submissions file stores some in the wrong time zone; V0); instead the return window spans both possibilities.

**Signal (primary, price only):** EAR = the stock's compounded return over days D−1, D, D+1 (close of D−2 to close of D+1) minus the equal-weighted return of all eligible microcaps over the same three days. Microcap = size bucket "micro" at the end of the month before D, and eligible (Round S universe). **Top decile = EAR at or above the 90th percentile of microcap EARs in the previous calendar quarter** (point in time; the current quarter's own distribution would use announcements not yet made).

**Trade:** buy at the close of **D+2** (after the whole return window), hold **60 trading days**, sell at that close. One event per company at a time.

**Implementable:** N = 10 (5, 20 reported), costs (a) and (b), (b) decides; same-day signals by larger EAR first; a full portfolio drops new signals.

**Sample:** announcements 2012-04-01 to 2026-06-15 (breakpoints from 2012 Q1 onward; every hold ends inside the data). Size-matched benchmark (micro EW for a micro portfolio), NW lags 3.

**Placebos (all must fail):**
- (a) **Non-announcement moves:** for each event, the same stock on the nearest date (within ±250 trading days) that is at least 20 trading days from any announcement and whose 3-day EAR is at or above the same threshold; entry 2 days later, 60-day hold. Academic excess must have t < 2 and mean below half the real one. (Separates earnings news from short-term momentum or reversal.)
- (b) Event-time random placebo (same dates, random same-bucket stock): p < 0.05.

**Diagnostic (reported):** the same rule in non-microcaps should show about zero (Martineau).

**Secondary, reported only:** days 2–15 hold (13 days from D+2); Friday announcements; SUE = (EPS_q − EPS_{q−4}) / standard deviation of that change over the prior 8 quarters (≥ 6), EPS as first reported (FSDS, 10-Q quarters; Q4 = annual minus the first three), day 0 = the 10-Q/10-K acceptance date, top decile by previous-quarter breakpoint; EAR and SUE both in their top decile; excluding top-MAX stocks.

**Variants counted:** 1 idea; 3 N × 2 costs + academic + 2 placebos + diagnostic + 5 secondaries.

## S4: Graham net-nets (registered 25 Sep 2026, before any S4 number was computed)

**Sources:** Graham, 1976 interview (FAJ) and *The Intelligent Investor* (first technique); Oppenheimer (1986) reported about 28.5% a year gross in the 1970s–early 1980s with a median market cap of about $4M. Cited from the plan; not re-verified (thresholds are Graham's own and frozen, so the paper's figure is context only).

**Definition (frozen as written):** NCAV = current assets − total liabilities − preferred stock (preferred includes redeemable preferred held as temporary equity). Values from the latest 10-K/10-Q accepted on or before the month-end (first reported; `tradelab/stocks/fundamentals.py`). **Buy if market cap < ⅔ × NCAV** (NCAV > 0).

**Universe:** Round S eligible stocks, **excluding financials** (SIC 6000–6999: no classified balance sheet).

**Trade:** checked at each month-end; a qualifying stock not already held is bought at the close of the next trading day. **Sell when market cap ≥ NCAV** (checked at month-ends with the latest NCAV and price; sold at the next close) **or after 2 years** (504 trading days), whichever first. It may be bought again later if it qualifies again.

**Implementable:** N = 10 (5, 20 reported), costs (a) and (b), (b) decides; same-day candidates by lowest market cap / NCAV first; a full portfolio takes no new names. Months with fewer than N names hold cash, and the cash drag counts.

**Sample:** formation months 2012-01 to 2026-07; size-matched benchmark (in practice micro). Also reported: IWM (a practical alternative, measurement only). NW lags 12 (average holding about a year).

**Dose-response (pre-registered, reported):** academic monthly returns of stocks at market cap / NCAV < 0.67, 0.67–1.0, 1.0–1.5 should be monotonic (cheapest best).

**Placebo:** event-time random placebo (same entry and exit dates, random same-bucket stock), p < 0.05.

**Secondary, reported only:** positive trailing-12-month earnings; excluding companies with a business address in China or Hong Kong (SEC state codes F4, K3); names per month; excluding top-MAX stocks.

**Regime note (mistake #44):** 2012–2026 lies mostly in value's worst decade; a failure is reported as such, with no relaxation.

**Variants counted:** 1 idea; 3 N × 2 costs + academic + dose-response + 3 secondaries.

## S5: Graham's 1976 "simplified approach", P/E ≤ 7 (registered 25 Sep 2026, before any S5 number was computed)

**Source:** Graham, FAJ 1976 interview (second technique): buy groups of stocks at P/E ≤ 7 on trailing reported earnings; sell at +50% or after 2 years (the lower ends of his 50–100% and 2–3-year ranges); he cited studies of 1925–1975 showing about 15% a year or more. Cited from the plan; thresholds frozen as written.

**Rule (primary, literal):** at each month-end, P/E = market cap / trailing-12-month net income (identical to price / EPS, but immune to splits between the filing and the month end: mistake #35), net income > 0, from the latest filing accepted by the month end (first reported). **Buy if P/E ≤ 7.** Only the Round S universe filters apply; **financials are kept** (literal rule).

**Trade:** bought at the close of the next trading day; **sold when the total return since the formation month-end close reaches +50%** (checked at month ends, sold at the next close) **or after 2 years** (504 trading days), whichever first. May be bought again later.

**Implementable:** N = 10 (5, 20), costs (a)/(b), (b) decides; same-day candidates by **lowest P/E first**; a full portfolio takes no new names.

**Sample:** formation 2012-01 to 2026-07; size-matched benchmark; NW lags 12.

**Placebo:** event-time random placebo, p < 0.05.

**Likely outcome (stated in advance):** heavy loading on the value factor (HML); an insignificant FF5+UMD alpha is reported as "known factor exposure", not a new edge.

**Secondary, reported only:** +100% / 3 years; Graham's alternatives instead of P/E: dividend yield > 7% (TTM dividends per share × weighted shares / market cap), book equity > 120% of market cap; adding total debt < equity; the Graham–Rea test earnings yield ≥ 2 × Moody's AAA yield (FRED AAA, the latest monthly value published by the month end, i.e. lagged one month); excluding top-MAX stocks.

**Variants counted:** 1 idea; 3 N × 2 costs + academic + 6 secondaries.

## S2: opportunistic vs routine insiders (registered 25 Sep 2026, before any S2 number was computed)

**Source checked:** Cohen, Malloy & Pomorski (NBER w16454 read; JF 2012). Routine = an insider who traded in the same calendar month in each of the prior years (three years shown in the paper); opportunistic = the other classified insiders. Their headline **82 bps a month (t 2.15) is value-weighted long-short** (opportunistic buys minus opportunistic sells), equal-weighted 180 bps (t 6.07), 1986–2007; routine about zero. Long-only will capture less.

**Classification (per insider and issuer, as of each calendar year Y):** trades = open-market purchases or sales (codes P, S) of common stock from original Forms 4, each insider identified by reporting-owner CIK (a joint filing counts once per listed owner). An insider is **classified** in year Y if they traded in each of Y−3, Y−2, Y−1. **Routine** if they traded in the same calendar month in each of those three years; **opportunistic** otherwise (classified but not routine). Unclassified insiders are excluded. Uses only past years.

**Signal:** firms with at least one opportunistic **purchase** by an officer or director (not 10%-owner-only filings) with a filing date in month m, no minimum size (as in the paper). Portfolio formed at the end of m, held month m+1 (bought at the next close), rebalanced monthly.

**Implementable:** N = 10 (5, 20), costs (a)/(b), (b) decides; ranked by the month's total opportunistic purchase value, largest first.

**Sample:** formation 2012-01 to 2026-07 (classification needs three years from 2006; size buckets from 2012). Size-matched benchmark, NW lags 1.

**Placebos (all must fail):** (a) **routine purchases**, same construction: excess must have t < 2 and mean below half the opportunistic one; (b) random portfolios (Round S rule 4), p < 0.05.

**Secondary, reported only:** opportunistic purchases with ≥ $10,000; excluding top-MAX stocks; 2009–2026 against the all-eligible EW universe.

**Variants counted:** 1 idea; 3 N × 2 costs + academic + 2 placebos + 3 secondaries.

## S7: Piotroski F-score among cheap stocks (registered 25 Sep 2026, before any S7 number was computed)

**Source:** Piotroski (2000, JAR supplement), building on Graham: within high book-to-market firms, high minus low F-score earned about 23% a year in 1976–1996. Cited from the plan; not re-verified (the rule is the standard 9 signals, frozen).

**F-score (9 binary signals, 10-K vs the previous 10-K, both as first reported, `fundamentals.py`):** (1) ROA = net income / beginning total assets > 0; (2) operating cash flow > 0; (3) ΔROA > 0; (4) accruals: operating cash flow > net income; (5) Δleverage < 0 (long-term debt / total assets fell); (6) Δcurrent ratio > 0; (7) no equity issuance (weighted shares did not rise); (8) Δgross margin > 0; (9) Δasset turnover > 0 (revenue / beginning assets). A missing input scores 0 for that signal.

**Trade:** at each month-end, stocks whose latest 10-K was accepted in that month (the signal is available from its acceptance), are eligible and non-financial, have book-to-market (equity / market cap) in the **top quintile** of eligible non-financial stocks that month, and **F ≥ 8** → bought at the next close, **held 12 months** (252 trading days).

**Implementable:** N = 10 (5, 20), costs (a)/(b), (b) decides; same-day candidates by higher F, then higher book-to-market. **Sample:** formation 2012-01 to 2025-08 (so holds end inside the data). Size-matched benchmark, NW lags 12.

**Placebos (all must fail):** (a) F ≤ 1 in the same quintile must not beat the benchmark (t < 2); (b) event-time random placebo p < 0.05.

**Secondary, reported only:** F-score ≥ 5 as a filter on S4 net-nets; F ≥ 8 without the value quintile; excluding top-MAX stocks.

**Variants counted:** 1 idea; 3 N × 2 costs + academic + 2 placebos + 3 secondaries.

## S6: Graham's *Intelligent Investor* screens (registered 25 Sep 2026, before any S6 number was computed)

**Enterprising investor (ch. 15), all six criteria, frozen as written:** current ratio ≥ 1.5; total debt ≤ 110% of net current assets (current assets − current liabilities); no annual loss in the last 5 fiscal years (5 annual 10-K net incomes, first reported, all > 0); some current dividend (TTM dividends per share > 0); latest annual EPS > EPS 5 years earlier; market cap < 120% of net tangible assets (equity − goodwill − intangibles). Non-financial, eligible.

**Trade:** **rebalanced annually**: every July (month-end of June as formation), all qualifying stocks are bought at the next close and held 12 months. Implementable N = 10 (5, 20), lowest price / net tangible assets first. **Sample:** formation June 2015 to June 2025 (5 years of 10-Ks exist from about 2010; 11 formations). Size-matched benchmark, NW lags 12. Pass bar as always; **stated in advance: about 11 years is underpowered, so this test can hardly pass on this data**.

**Placebo:** event-time random placebo p < 0.05.

**Defensive investor (ch. 14): data-blocked, not tested.** It needs 10 years of earnings and 20 years of dividends, which free SEC XBRL data (from 2009) cannot provide. Recorded in the graveyard as blocked, not as a failure.

**Not tested:** V = EPS × (8.5 + 2g) (needs a growth forecast, a free parameter); the Graham number is inside the defensive criteria.

**Variants counted:** 1 idea (enterprising); 3 N × 2 costs + academic.

**S3 result (run 25 Sep 2026, `scripts/stocks/s3_pead_microcaps.py`, `reports/stocks/s3_results.json`): FAIL. The drift exists in microcaps, but it is not an earnings effect (placebo a does not fail), and a 10-name portfolio loses after costs.**

411,935 announcement dates (253,795 from 8-K Item 2.02, 158,140 from 10-Q/10-K filings); 63,732 microcap announcements; 6,110 top-decile events (Apr 2012 – Jun 2026). Size-matched benchmark, NW lags 3:

| Version | Mean excess / month | NW t | Win % | Halves | FF5+UMD alpha of excess (t) | Names | Worst DD |
|---|---|---|---|---|---|---|---|
| Academic, all events (EW, gross) | +0.64% | +3.27 | 63% | +0.30 / +0.99 | +0.41% (+2.02) | – | −49% |
| N = 10, (b) (primary) | **−0.64%** | −1.40 | 49% | −0.16 / −1.11 | −0.59% (−1.26) | 9.4 | −66% |
| N = 10, (a) | −0.64% | −1.41 | 49% | −0.19 / −1.09 | −0.59% (−1.27) | 9.4 | −65% |
| N = 5, (b) | −1.36% | −2.02 | 40% | −1.16 / −1.55 | −1.13% (−1.55) | 4.7 | −91% |
| N = 20, (b) | +0.27% | +0.82 | 53% | −0.09 / +0.62 | +0.11% (+0.32) | 18.8 | −55% |

- **Placebo (a), non-announcement moves: +1.72% a month (t +6.00), stronger than the real events.** Big 3-day rises in the same microcaps on dates at least 20 trading days from any announcement drift as much or more. The effect is short-term continuation after big moves, not earnings information. Placebo (b), event-time random: 63-day return 5.06% vs 3.03% for random microcaps on the same dates (p = 0.001), consistent with a real continuation effect.
- Diagnostic, non-microcaps: −0.08% (t −0.63), as Martineau reports.
- Secondary: hold 13 days +1.09% (t 1.86); Friday announcements −0.69% (455 events); without top-MAX +0.60% (t 3.06); **SUE (earnings surprise vs own history) +1.45% (t 3.26, 2,060 events)**; EAR and SUE both +2.44% (t 3.50, 358 events).
- The implementable portfolio took 9% of the signals, paid about 0.5% of equity a month in costs, and chose by largest EAR first, which the S8 result warns against.
- **Leads, not results (need their own pre-registration and an independent period, e.g. 2000–2011):** (1) microcap continuation after large non-news 3-day rises; (2) SUE-based drift in microcaps. Both academic, gross, secondary.

**S4 result (run 25 Sep 2026, `scripts/stocks/s4_graham_netnets.py`, `reports/stocks/s4_results.json`): FAIL on t and halves. The closest call so far: positive, monotonic in cheapness, and it beats random same-size stocks, but it is all in 2019–2026 and a 10-name portfolio only matches its benchmark.**

165,558 eligible non-financial stock-months with NCAV; 1,704 net-net stock-months (median 6 a month, 0–44; many more in 2022–2026: 296, 211, 227, 351, 140 by year vs 26–75 before); 449 holdings. Size-matched benchmark, NW lags 12:

| Version | Mean excess / month | NW t | Win % | Halves | FF5+UMD alpha of excess (t) | Names | Worst DD | Months underwater |
|---|---|---|---|---|---|---|---|---|
| Academic, all net-nets (EW, gross) | +0.98% | +1.11 | 50% | −0.69 / +2.65 | +0.93% (+1.12) | ~10 | – | – |
| N = 10, (b) (primary) | **+0.02%** | +0.02 | 47% | −0.73 / +0.77 | +0.28% (+0.45) | 8.8 | −61% | 90 |
| N = 10, (a) | +0.00% | +0.00 | 47% | −0.76 / +0.76 | +0.27% (+0.43) | 8.8 | −62% | 90 |
| N = 5, (b) | −0.51% | −0.61 | 47% | −1.10 / +0.08 | +0.28% (+0.38) | 4.7 | −79% | 103 |
| N = 20, (b) | +0.17% | +0.32 | 47% | −0.68 / +1.02 | +0.34% (+0.76) | 14.0 | −45% | 65 |

- **Event-time placebo: net-nets returned +24.1% over their holding period vs +12.4% for random same-size stocks on the same dates (+11.8% per holding, p = 0.015). Passes that criterion.**
- **Dose-response (pre-registered): monotonic.** Market cap < ⅔ NCAV +2.02% a month (t 2.17, 10 names), ⅔–1 +0.60% (t 0.96, 14 names), 1–1.5 +0.52% (t 1.37, 32 names).
- vs IWM: +0.03% a month (t 0.04). The 10-name portfolio turned $7,632 of deposits into $24,569 (benchmark-like), with costs about 0.18% of equity a month.
- Secondary: positive TTM earnings +0.95% (t 1.02, 69 holdings); no China/HK address +1.14% (t 1.32); no top-MAX +1.25% (t 1.74, halves +0.48 / +2.03).
- Factor loadings of the 10-name portfolio: market 0.76, SMB 0.26, HML 0.0, RMW −0.70 (unprofitable firms).
- **Plain meaning:** Graham's net-nets still exist and the cheapest ones did better, but over 2012–2026 the edge is too noisy and too concentrated in the last seven years to count, and a small portfolio rides −60% drawdowns. Regime note (mistake #44): the sample sits in value's worst decade. **A candidate for forward paper-logging, not for money.**

**S5 result (run 25 Sep 2026, `scripts/stocks/s5_graham_pe7.py`, `reports/stocks/s5_results.json`): FAIL. P/E ≤ 7 with Graham's exits earned nothing over size-matched stocks in 2012–2026, and did worse than random same-size stocks on the same dates.**

24,401 stock-months at P/E ≤ 7 (median 113 names a month); 3,447 holdings. Size-matched benchmark, NW lags 12:

| Version | Mean excess / month | NW t | Win % | Halves | FF5+UMD alpha of excess (t) | Names |
|---|---|---|---|---|---|---|
| Academic, all holdings (EW, gross) | −0.05% | −0.26 | 45% | −0.35 / +0.25 | −0.16% (−1.34) | ~139 |
| N = 10, (b) (primary) | **−0.54%** | −1.34 | 43% | −0.89 / −0.19 | −0.30% (−0.79) | 10 |
| N = 10, (a) | −0.54% | −1.34 | 43% | −0.90 / −0.18 | −0.30% (−0.79) | 10 |
| N = 5, (b) | −0.60% | −1.23 | 43% | −0.69 / −0.50 | −0.35% (−0.82) | 5 |
| N = 20, (b) | −0.74% | −2.33 | 36% | −0.78 / −0.70 | −0.49% (−1.78) | 20 |

- Event-time placebo: holdings returned 19.2% vs 22.8% for random same-size stocks on the same dates (p = 0.98).
- Factor loadings (10 names, over T-bills): market 0.81, SMB 0.62, **HML 0.36**, RMW 0.07, CMA −0.32, UMD −0.26; alpha −0.39% (t −1.10). As stated in advance: value exposure, no alpha.
- Secondary (all academic): +100% / 3 years −0.01% (t −0.07); dividend yield > 7% −0.17% (t −0.93); book > 120% of market cap −0.07% (t −0.34); P/E ≤ 7 and debt < equity −0.01% (t −0.04); Graham–Rea earnings yield ≥ 2 × AAA −0.03% (t −0.22); without top-MAX −0.01% (t −0.04).
- Regime note (mistake #44): 2012–2026 is value's worst stretch; the result is reported as it is.

**S2 result (run 25 Sep 2026, `scripts/stocks/s2_opportunistic_insiders.py`, `reports/stocks/s2_results.json`): FAIL. Opportunistic insider purchases carried no long-only information in 2012–2026; the monthly-rebalanced 10-name version churns so much that costs alone take about 1% a month.**

126,475 classified insider-years (87,159 opportunistic, 39,316 routine); 5,700 firm-months with opportunistic purchases (about 33 firms a month). Size-matched benchmark, NW lags 1:

| Version | Mean excess / month | NW t | Win % | Halves | FF5+UMD alpha of excess (t) | Names |
|---|---|---|---|---|---|---|
| Academic, all firms (EW, gross) | −0.28% | −1.19 | 45% | −0.55 / −0.01 | −0.23% (−0.93) | ~33 |
| N = 10, (b) (primary) | **−1.58%** | −5.58 | 30% | −1.38 / −1.78 | −1.66% (−5.38) | 9.8 |
| N = 10, (a) | −1.64% | −5.81 | 31% | −1.53 / −1.74 | −1.72% (−5.59) | 9.8 |
| N = 5, (b) | −1.29% | −2.98 | 37% | −1.56 / −1.03 | −1.43% (−2.95) | 4.9 |
| N = 20, (b) | −1.40% | −5.69 | 32% | −1.37 / −1.44 | −1.43% (−5.82) | 18.2 |

- Audit (|t| > 5, in the losing direction): the 10 largest opportunistic purchases each month underperformed by −0.55% gross; only 10% of names carry over to the next month, so the portfolio turns over almost fully monthly and costs are about 1.0% of equity a month. Gross −0.55% + costs ≈ −1.58%. Not a bug.
- Placebo, routine purchases: −0.14% (t −0.70), flat as expected; random placebo p = 0.94 (the real picks did worse than random).
- Secondary: ≥ $10k purchases −0.14% (t −0.55); without top-MAX −0.35% (t −1.46); 2009–2026 vs the all-eligible universe −0.13% (t −0.65).
- **Plain meaning:** the paper's 82 bps a month was long-short and ended in 2007; long-only in 2012–2026 there is nothing, and a monthly-churning small portfolio bleeds costs.

**S7 result (run 25 Sep 2026, `scripts/stocks/s7_piotroski.py`, `reports/stocks/s7_results.json`): FAIL. High F-scores among the cheapest stocks did not beat size-matched stocks in 2012–2025; the low-F placebo did better (the wrong way round).**

5,227 10-K months in the top book-to-market quintile (F distribution 0–9: 24, 305, 657, 988, 1,086, 1,035, 642, 362, 116, 12); 124 holdings with F ≥ 8. Size-matched benchmark, NW lags 12:

| Version | Mean excess / month | NW t | Win % | Halves | FF5+UMD alpha of excess (t) | Names |
|---|---|---|---|---|---|---|
| Academic, all holdings (EW, gross) | −0.07% | −0.21 | 47% | −0.52 / +0.38 | −0.04% (−0.14) | ~9 |
| N = 10, (b) (primary) | **−0.58%** | −2.37 | 45% | −0.77 / −0.38 | −0.18% (−0.74) | – |
| N = 10, (a) | −0.58% | −2.36 | 45% | −0.78 / −0.37 | −0.18% (−0.74) | – |
| N = 5, (b) | −0.27% | −0.87 | 51% | −0.45 / −0.10 | −0.09% (−0.26) | – |
| N = 20, (b) | −0.70% | −3.03 | 37% | −0.80 / −0.59 | −0.14% (−0.72) | – |

- Placebo (a), F ≤ 1 in the same quintile: +0.80% (t 1.42, 306 holdings). It "fails" formally (t < 2), but the low-quality stocks did better than the high-quality ones, the opposite of Piotroski (1976–1996). Event-time random placebo: 14.1% vs 11.4% (p = 0.28).
- The implementable portfolio is often part cash (about 9 new names a year), so cash drag weighs on it.
- Secondary: F ≥ 8 at any book-to-market +0.14% (t 0.93, 1,036 holdings); without top-MAX −0.17% (t −0.49); F ≥ 5 filter on S4 net-nets +0.62% (t 0.46, 43 holdings, halves −1.99 / +3.19).

**S6 result (run 25 Sep 2026, `scripts/stocks/s6_graham_enterprising.py`, `reports/stocks/s6_results.json`): FAIL, and underpowered as stated in advance.** All six enterprising-investor criteria together leave 25 qualifying stock-years in 11 June formations (2016: 2, 2017: 2, 2019: 2, 2020: 5, 2022: 2, 2023: 4, 2024: 4, 2025: 4; none in 2015, 2018, 2021). Passing each criterion alone (of eligible non-financial stock-Junes): current ratio 17,401; debt ≤ 1.1 × NCA 14,214; no loss in 5 years 8,671; dividend 6,342; EPS growth over 5 years 9,412; price < 1.2 × net tangible assets 2,277.

| Version | Mean excess / month | NW t | Halves | FF5+UMD alpha of excess (t) |
|---|---|---|---|---|
| Academic (EW, gross), 99 months with holdings | −0.82% | −1.47 | −1.43 / −0.22 | −0.27% (−0.55) |
| N = 10, (b) (primary), 123 months incl. cash | **−0.83%** | −1.90 | −1.43 / −0.25 | +0.04% (+0.20) |
| N = 5, (b) | −0.59% | −1.51 | −1.12 / −0.06 | +0.24% (+0.85) |
| N = 20, (b) | −0.97% | −1.98 | −1.61 / −0.34 | −0.06% (−0.45) |

- Event-time placebo: 18.4% vs 31.6% for random same-size stocks on the same dates (p = 0.71).
- The portfolio sits mostly in cash (0–5 names), so the size-matched benchmark beats it; alphas near zero.
- **Defensive investor (ch. 14): data-blocked, not tested** (needs 10–20 years of history).

**Round S summary (25 Sep 2026): 8 tests (S8, S1, S3, S4, S5, S2, S7, S6; the defensive screen blocked), 0 passes.** Closest: S4 net-nets (positive, monotonic, beats random p 0.015, but t 1.11 and all in 2019–26). Leads for fresh pre-registration: microcap continuation after big non-news moves (S3 placebo, t 6.0); SUE drift in microcaps (S3 secondary, t 3.26).

---

# Round S2: final stock round (registered 25 Sep 2026)

Items: S9 Part A (descriptive), L1 (audit, then one out-of-sample test on 2000–2011), SUE to the forward log only, S4 net-nets as a quarterly paper screen. **If L1 fails, the stock hunt ends.** S9 Part B (the composite $1–5 test in STOCK_PLAN §5) is not part of this round.

**S9 Part B (the composite $1–5 test in STOCK_PLAN §5): not run, hunt closed (25 Sep 2026).** Not counted in the tally.

## S9 Part A: base rates for $1–5 stocks (descriptive; 0 ideas; registered before running)

As in STOCK_PLAN §5 (S9 Part A). No predictor from this part may be used in any test.
- **Stocks:** at each month end, listed US common stocks (Round S `common`, one share class per company), grouped by **unadjusted** month-end close: below $1 (context only), $1–5, $5 and up. No liquidity filter (a description of what is listed).
- **Formation months:** Jan 2000 – Aug 2025 for 12-month outcomes (Feb 2026 for 6-month).
- **Outcomes over the next 6 and 12 months**, compounding monthly total returns with Shumway delisting returns (the return stops at delisting): share that **doubled** (≥ +100%), **tripled** (≥ +200%), **halved** (≤ −50%), **delisted** (the listing ended inside the window, any reason, and performance-related separately); median and mean return.
- **Equal-weighted bucket return vs the $5+ bucket:** next-month EW return difference, mean and NW t (lag 1).
- **Splits:** young (listed less than 3 years at formation; formation from 2001, since the price data starts in Dec 1997) vs older; periods 2000–2008, 2009–2016, 2017–2025.
- Outputs: `reports/stocks/s9a_*.csv`, `s9a_base_rates.png`.

**S9 Part A result (run 25 Sep 2026, `scripts/stocks/s9a_base_rates.py`, `reports/stocks/s9a_*`; descriptive).** 1.40 million stock-months, Jan 2000 – Aug 2025.

| Within 12 months | < $1 (context) | **$1–5** | $5+ |
|---|---|---|---|
| Stock-months | 99,327 | 240,884 | 1,056,384 |
| Doubled | 14.4% | **12.6%** | 4.0% |
| Tripled | 7.9% | 4.9% | 0.8% |
| Halved | 37.1% | **23.2%** | 9.0% |
| Delisted (any reason) | 15.6% | 8.2% | 4.7% |
| Delisted, performance-related | 11.2% | 2.4% | 0.2% |
| Median return | −26.4% | **−6.7%** | +5.1% |
| Mean return | +27.3% | +16.9% | +9.0% |

- Within 6 months, $1–5: doubled 6.9%, halved 14.2%, median −4.7%.
- Equal-weighted next-month bucket return vs $5+: $1–5 +0.09% a month (t 0.33); < $1 +0.88% (t 1.43). No reliable premium for cheap stocks as a group.
- Young (< 3 years listed) $1–5 stocks: doubled 12.9%, **halved 32.5%**, median −19.5% (older: 12.7%, 21.0%, −4.0%).
- By period, $1–5: 2000–08 doubled 14.3% / halved 22.2%; 2009–16 11.5% / 16.4%; **2017–25 11.7% / 30.7%, median −20.3%**.
- **Plain meaning:** about one $1–5 stock in eight doubles within a year, but nearly one in four halves; the typical one loses 7%. The average looks good only because a few huge winners pull it up. Young cheap stocks and the last nine years are worse.

## L1: microcap continuation after big non-earnings moves (registered 25 Sep 2026, before any L1 number was computed)

**Origin:** S3 placebo (a): big 3-day rises in microcaps on non-announcement dates drifted +1.72% a month over 60 days (t 6.0, academic, gross, 2012–2026). t > 5 triggers the audit rule, so: audit on 2012–2026 first (in-sample, descriptive), then freeze the rule and test it **once** on 2000–2011 (out of sample). If L1 fails, the stock hunt ends.

### The rule (frozen form; applied identically in both periods)
- **Stocks:** Round S eligible microcaps at the end of the month before the signal. 2012–2026: size bucket "micro" (NYSE 20th percentile of market cap). 2000–2011: the dollar-volume proxy below.
- **Signal day t:** X_t = the stock's compounded return over t−1, t, t+1 minus the equal-weighted return of the same microcap universe over those days. **Big move: X_t ≥ T.** **T is one fixed number:** the pooled 90th percentile of microcap earnings-announcement EARs in S3 (announcements Apr 2012 – Jun 2026), rounded to 0.1 percentage point. It is computed from the announcement distribution only, not from any L1 return.
- **Non-earnings:** no 8-K Item 2.02 (Item 12 before Aug 2004) and no 10-Q/10-K filed by the company in trading days [t−20, t+1]. Only filings public by the signal's last day are used. The S3 placebo also excluded later announcements (look-ahead, acceptable in a placebo, not in a rule).
- **No M&A:** no 8-K Item 1.01 or 2.01 (old numbering: Items 1, 2), SC TO-T, SC 14D9, DEFM14A, PREM14A or SC 13E3 by the company in [t−3, t+1].
- **Not stale:** volume > 0 on day t+1 and on the entry day.
- **Trade:** buy at the close of **t+2**; hold **63 trading days**; one position per stock at a time.
- **Implementable:** N = 10 (5, 20), costs (a)/(b) with half-spreads, (b) decides; same-day signals by larger X first; a full portfolio drops new signals.

### Audit (2012–2026, in-sample, reported, not a test)
1. **Event type** by company filings in trading days [t−3, t+3]: M&A (the forms above), other 8-K, no filing. Academic excess for each type. Merger targets drifting to a deal price are merger arbitrage, not an edge.
2. **Stale prices:** with and without the volume rule; robustness entry at the close of t+3.
3. **Known effects:** alpha of the academic excess on FF5 + UMD + a 52-week-high factor (George & Hwang 2004; built here: each month, eligible stocks ranked by month-end price / highest daily total-return index of the prior 252 trading days; top 30% minus bottom 30%, equal-weighted, next month).
4. The frozen rule itself on 2012–2026 (for reference only; in-sample).

### Out-of-sample test (2000–2011): run once
- **V0 checks without market caps, 2000–2011 (must hold before the test):** monthly eligible stock counts are several thousand; Enron (2001), WorldCom (2002) and Lehman (2008) are present, listed, and show their collapses.
- **Microcap proxy (pre-registered):** s̄ = the average share of eligible stocks that are micro by market cap over 2012–2026. In each month, an eligible stock is a "microcap" if its 20-day median dollar volume is in the bottom s̄ of eligible stocks. Its agreement with the market-cap bucket on 2012–2026 is reported.
- **Sample:** signal days Jan 2000 – Sep 2011 (every hold ends by Dec 2011; formation from the 2000 panel). Benchmark: equal-weighted proxy microcaps (size-matched for a micro portfolio). NW lags 3. Halves split at the middle month.
- **Pass bar (Round S, all four):** t > +2.8 on the 10-name (b) excess after costs; both halves positive; mean excess > 0; the event-time random placebo (same dates, random proxy microcap) p < 0.05.
- **Also reported:** academic version, FF5 + UMD + 52-week-high alpha, N = 5 / 20, event types.

**Variants counted:** 1 idea (L1). Audit cells are descriptive; the out-of-sample run counts 3 N × 2 costs + academic.

**L1 audit result (run 25 Sep 2026, `scripts/stocks/l1_microcap_continuation.py --audit`, `reports/stocks/l1_audit.json`; in-sample 2012–2026, descriptive). The lead does not survive the audit: under a tradable rule, big non-earnings moves in microcaps are followed by UNDERperformance.**

T = +12.6% (pooled 90th percentile of S3's microcap announcement EARs). Signals Feb 2012 – May 2026, academic excess over the size-matched benchmark, NW lags 3; alpha on FF5 + UMD + 52-week-high factor (FH):

| Events | N | Excess / month | t | Halves | Alpha (t) | β UMD | β FH |
|---|---|---|---|---|---|---|---|
| All (no M&A or stale filter), by type in [t−3, t+3]: **M&A** | 1,770 | −1.11% | −2.34 | −1.00 / −1.22 | −0.69% (−1.60) | −0.02 | −0.46 |
| other 8-K | 3,782 | −0.39% | −1.57 | −0.91 / +0.14 | −0.39% (−1.47) | 0.17 | −0.29 |
| no filing | 11,190 | −0.50% | −2.11 | −0.89 / −0.11 | −0.47% (−2.80) | 0.09 | −0.31 |
| All together | 16,742 | −0.54% | −2.53 | −0.93 / −0.15 | −0.47% (−3.22) | 0.11 | −0.33 |
| Stale rule on (M&A kept) | 16,715 | −0.54% | −2.50 | −0.93 / −0.15 | −0.47% (−3.21) | | |
| **Frozen rule** (M&A out, stale rule on) | 15,865 | **−0.51%** | −2.24 | −0.96 / −0.06 | −0.48% (−3.11) | 0.14 | −0.33 |
| Frozen rule, entry at t+3 | 15,867 | −0.39% | −1.74 | −0.87 / +0.09 | −0.36% (−2.38) | | |

- Frozen rule, implementable (in-sample, reference): N = 10 (b) −1.24% a month (t −1.51, halves −1.51 / −0.97, worst DD −87%); N = 5 (b) −0.93%; N = 20 (b) −1.53% (t −3.17). Event-time placebo: 2.39% vs 3.61% for random microcaps on the same dates (p = 1.0).
- M&A events are not merger-arbitrage winners here (−1.11%); removing them changes little.

**Where the S3 placebo's +1.72% (t 6.0) came from (`scripts/stocks/l1_audit_placebo_origin.py`, hypothesis stated in its docstring before running):** S3 placebo (a) chose, for each top-decile earnings event, the nearest big non-announcement move within ±250 trading days, often BEFORE the real event, so its 60-day hold could contain the future earnings reaction. Split:

| S3 placebo events | N | Excess / month | t |
|---|---|---|---|
| Hold contains the real earnings reaction | 1,674 | **+6.59%** | +10.24 |
| Placebo after the event | 2,167 | −0.85% | −2.72 |
| Placebo before the event, no overlap | 792 | −2.45% | −5.85 |

**The lead was a look-ahead artifact of my placebo design** (dates chosen relative to a future event). New mistake #53. **Correction to S3:** its placebo (a) was biased upward, so "non-earnings jumps drift more" is withdrawn as the reason; S3 still FAILS on its implementable pass bar (10 names −0.64%, t −1.40), and its academic +0.64% (t 3.27) stands unexplained, not refuted.

Per the pre-registration, the frozen rule is still tested once on 2000–2011.

**L1 out-of-sample result (run once, 25 Sep 2026, `l1_microcap_continuation.py --oos`, `reports/stocks/l1_oos.json`): FAIL, in the losing direction. The stock hunt ends here.**

- V0 without market caps, 2000–2011: **passed** (eligible stocks 2,681–3,888 a month; Enron listed to Nov 2004, low $0.26 in 2001; WorldCom low $0.10 in 2002; Lehman low $0.13 in 2008).
- Microcap proxy: s̄ = 36.1% (bottom 36.1% of eligible stocks by 20-day median dollar volume); agreement with the market-cap bucket on 2012–2026 88.9% (micro recall 83.5%, precision 85.6%).
- 16,638 events (Jan 2000 – Sep 2011; types in [t−3, t+3]: 13,653 no filing, 2,669 other 8-K, 316 M&A that were not excluded because their filing came after t+1).

| Version | Mean excess / month | NW t | Win % | Halves | FF5+UMD alpha (t) | Names | Worst DD | Cost drag |
|---|---|---|---|---|---|---|---|---|
| Academic, all events (EW, gross) | −0.45% | −1.41 | 42% | −0.19 / −0.71 | −0.24% (−1.20) | – | −72% | – |
| N = 10, (b) (primary) | **−1.73%** | −2.65 | 40% | −1.85 / −1.61 | −1.76% (−2.52) | 9.8 | −96% | 0.61% |
| N = 10, (a) | −1.86% | −2.83 | 40% | −2.05 / −1.67 | −1.88% (−2.67) | 9.8 | −97% | 0.68% |
| N = 5, (b) | −2.08% | −2.44 | 38% | −3.20 / −0.96 | −1.90% (−1.91) | 4.9 | −99% | 0.63% |
| N = 20, (b) | −1.65% | −3.26 | 35% | −1.37 / −1.93 | −1.49% (−2.78) | 19.7 | −94% | 0.62% |

- By event type (academic): no filing −0.54% (t −1.63); other 8-K +0.05% (t 0.09).
- Alpha on FF5 + UMD + 52-week-high: −0.28% (t −1.49); β UMD 0.00, β FH −0.17.
- Event-time placebo: 0.05% vs 1.80% for random microcaps on the same dates (p = 1.0).
- The 10-name portfolio turned $6,510 of deposits (€400 + €35 a month, 2000–2011) into $3,664.
- **Plain meaning:** buying microcaps after a big jump with no news loses money, in 2000–2011 as in 2012–2026. The "lead" came from a flaw in my own placebo, and the out-of-sample test confirms there is nothing here.
