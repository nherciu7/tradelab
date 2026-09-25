# 53 backtest traps

Every item on this list produced a wrong result in this project at least once: a fake edge, a hidden loss, or a test that could not fail. The list is checked against every new result. Numbering is stable; the code refers to it (for example "backtest trap #30").

## Execution and look-ahead

1. **Retrying a later setup when an earlier limit order did not fill.** The engine knew, at setup time, that the earlier order would expire unfilled, because it had looked ahead to the fill deadline. This manufactured an intraday "edge" at t = 5.74 that was really zero ([case study](case_studies/01_ict_fake_edge.md)). Replay each day in time order: one working order, replaced by newer setups, decided only on information known at that bar.
2. **Deleting trades where the stop was touched "before the fill".** For a long limit order, price must pass through the limit to reach the stop, so that bar is a fill plus a stop-out: a full loss.
3. **Counting the profit target on the fill bar.** Its extreme may have printed before the fill. Only the stop can count on the fill bar.
4. **Fills on a touch.** Require a trade-through of one tick.
5. **A stop on the wrong side of the entry** (a bug booked guaranteed wins). The engine must raise an error if this ever happens.
6. **An exit walk that began before the trade existed.**
7. **Aligning two series by integer position instead of by date.**

## Costs and returns

8. **Control groups built as −(net return).** This flips the sign of the cost.
9. **Costs applied wrongly:** one instrument's cost charged to another, costs omitted and the result labelled "net", costs charged once per leg thousands of times.
10. **Carry inside total-return series.** An ETF's total return accrues coupons that a futures position never receives. Strip it before comparing.
11. **A "duration-neutral" pair that was 99% one leg.** It was just the risk-free rate.

## Data and calendars

12. **Calendar filters that leave holes** (keeping days 24–31 and 1–4 of each month built accidental four-week holds).
13. **Time zones.** Minute data arrived in UTC without a zone. Convert once, DST-aware, and verify with a known event (the US-open volume spike moves between 13:30 and 14:30 UTC).

## Simulation and statistics

14. **A ratio-of-averages income metric.** Use total paid ÷ total months.
15. **A gate in the simulation tied to the parameter under test.**
16. **Independent sampling of legs that co-move.** Draw all legs from the same calendar month; date-align overlapping legs instead of concatenating them.
17. **Treating several accounts as independent** when one signal set feeds them all.
18. **R-multiples vs fixed notional.** An edge positive in basis points can be strongly negative in R (risk units): +3.38 bps per trade but −0.128 R; equity ×6.9 at fixed size vs ×0.016 at 0.5% fixed risk. Report both.
19. **End-of-day vs intraday drawdown.** A trailing drawdown rule is breached by the worst intraday excursion, not the closing mark (−$4,760 intraday vs −$3,293 at the close for one futures book).
20. **Assuming a failed attempt can be re-bought.** With one fee, ruin is absorbing. Optimise the chance of success, not the average income.
21. **Buffer-scaled sizing.** It cut blow-ups but stalled below the goal, lowering the chance of success from 46% to 28%.
22. **Labels.** "Harsh"/"lenient" and gross/net were swapped at least once. Check every label.

## Sources

23. **Aggregator and review sites** were wrong about firm rules repeatedly. Only a written answer from the source counts.
24. **Machine-generated research summaries** mix good citations with wrong figures. Verify every number at the primary source.

## Windows and signs

25. **The last day in the data labelled as a month-end.** An unfinished month produced a fake month-end window (a sample of 290 months was really 289). Take month-ends from the exchange calendar, never from the data.
26. **Summing simple returns across a window.** A tick up and back sums to a small positive, so a flat window counts as a win (a gross win rate of 76.2% was really 72.7%). Compound returns.
27. **A sign-agnostic pass bar.** Checking |t| > 2.8 let a trade losing money at t = −5.95 print PASS. Sign returns in the trade's direction and require t > +2.8.

## Stocks

28. **Survivorship bias.** A universe of stocks alive today. The universe on each date must be the stocks listed on that date, from a source that includes dead stocks.
29. **Missing delisting returns.** The series stops and the loss vanishes. Apply the Shumway convention (−30% NYSE/AMEX, −55% Nasdaq for performance delistings, −30% if unknown, 0% for mergers) and report results both ways.
30. **Fundamentals dated by the period end.** A December 10-K is public in February or March. Date values by the SEC acceptance time and trade at the next close.
31. **Restated numbers.** Use values as first reported, never later amendments or comparatives.
32. **Insider trade date vs filing date.** Insiders file days later, sometimes months. The signal date is the filing date.
33. **Earnings timing.** After-close vs pre-open releases: day 0 is the first session the news could be traded.
34. **Ticker reuse and changes.** Use the permanent company ID (SEC CIK) with a point-in-time ticker map.
35. **Mixing adjusted and unadjusted prices.** Ratios use unadjusted price × point-in-time shares; returns use total-return prices. Never divide an adjusted price by an unadjusted EPS.
36. **Pooled stock-level t-statistics.** Positions held in the same month are correlated; the t must come from the monthly calendar-time series with Newey-West errors.
37. **Bid-ask bounce in cheap stocks.** Use a $1 price floor ($5 as a check) and enter at the next close, not the signal day's close.
38. **Academic long-short vs long-only.** Much published profit sits in the short leg. Test what can actually be held.
39. **Academic portfolio vs implementable portfolio.** A 500-stock decile is not 10 names in a €400 account. Test the N-name version with real minimum commissions and spreads.
40. **The wrong benchmark.** The S&P 500 as a benchmark for microcaps mixes in the size effect. Use the size-matched universe and report factor alphas.
41. **Tuning a book's thresholds.** Published thresholds are frozen as written; any tuning is walk-forward and counted as extra variants.
42. **Currency.** Returns are in USD and the account funds in EUR: include conversion fees, report in USD.
43. **Stale prices.** Zero-volume days create fake flat returns. Require volume on entry and exit days.
44. **Regime.** A free fundamental sample starting in 2009–2011 sits in value investing's worst decade. Say so when a value test fails; do not relax the bar.

## Vendor data (found by the V0 validation gate; [case study](case_studies/03_v0_vendor_data.md))

45. **A vendor files each stock under its LAST ticker and exchange.** A bankrupt NYSE company's whole history sat under its later OTC ticker. Never filter a download by exchange label; take listing periods from SEC Form 25 filings.
46. **Duplicate series.** The same history under two codes. Detect by identical returns (within 0.2 percentage points in 90% of months), not by name.
47. **Splices and scale breaks.** Old and new shares glued together (+144,000% in a day), unadjusted reverse splits, "raw" closes back-adjusted by later splits ($2,099 for a $7 stock), placeholder prints ($1,000,000). Real collapses end in pennies.
48. **Market cap needs an independent check.** SEC share counts contain typos (317 trillion shares). Check against the 10-K public float, dollar turnover and total assets.
49. **Time zones in the SEC bulk submissions file are not all UTC**, despite the "Z". Use the Financial Statement Data Sets or the EDGAR filing header.
50. **Foreign IPOs file Form 424B4 too.** Domestic-company filters must use 10-K/10-Q/S-1 and exclude 20-F/40-F filers.
51. **One mis-weighted stock breaks a value-weighted check.** Look at the top contributors in the worst month first.
52. **Scripted edits can write invisible control characters.** A regex `\b` became a literal backspace and silently matched nothing. A test now scans every source file.
53. **A placebo whose dates are chosen relative to a future event.** Placebo dates were picked next to later earnings jumps, so the placebo's holding window contained them. It manufactured a fake lead at t = 6.0 ([case study](case_studies/02_placebo_lookahead.md)). Placebo dates may only use information known at the placebo date.
