# V0 validation gate: report (25 Sep 2026)

**Verdict: PASS on all five pre-registered criteria**, after fixing eleven data problems V0 exposed. One limitation matters for the test queue: market caps (and so the size buckets) exist only from about **2012**, because the free SEC share counts start with XBRL.

Script: `scripts/stocks/v0_validate.py` (criteria in its docstring, written before the first run). Outputs: `reports/stocks/v0_*.csv`, `v0_counts.png`, `v0_summary.json`.

## Results

| # | Check | Bar | Result | |
|---|---|---|---|---|
| 1 | Eligible stocks per month | several thousand, falling over the 2000s | 2,700–3,800 (3,406 in Dec 2000, 2,899 in Dec 2012, 3,414 in Dec 2025) | PASS, qualified (see below) |
| 2 | Our equal-weighted universe vs French's EW CRSP universe | corr > 0.95 | **0.984** (2000–26), 0.987 (2012–26); mean gap +0.03% a month | PASS |
| | Value-weighted universe vs French's market (reported) | – | 0.996; mean gap −0.10% a month | |
| 3 | 12-2 momentum, top minus bottom decile, NYSE breakpoints, VW, vs UMD | corr > 0.8 | **0.836** (2000–26), 0.839 (2012–26) | PASS |
| | Same, vs French's own VW decile spread (same construction) | – | 0.951 / 0.971 | |
| | EW decile spread vs French's EW decile spread | – | 0.940 / 0.855 | |
| 4 | Delisting rate per year | roughly 5–10% | 4.2%–9.1% (2001–2025) | PASS |
| | Eight known collapses present | all | 8 of 8 (below) | PASS |
| 5 | 20 random first-reported fundamentals | value and date correct | values 20/20 (19 via SEC companyfacts, 1 checked by hand in the filing: Technical Communications, equity $937,008 at 30 Jun 2020); acceptance times 20/20 vs the EDGAR filing header; 20/20 after the period end | PASS |

Note on check 3: even French's own decile spread correlates only 0.844 with UMD, because UMD is built differently (2×3 size × 30/70 sort). Ours tracks the same-construction series at 0.95–0.97.

**The eight collapses** (security, listed period, delisting class, last month's return with the Shumway delisting return):

| Company | Listed | Lowest close in the year | Last month |
|---|---|---|---|
| Lehman Brothers | 1997 → 17 Sep 2008 | $0.13 | −99.4% |
| Washington Mutual | 1997 → 24 Nov 2008 | $0.02 | −53% |
| General Motors (old) | 1997 → Mar 2011 (OTC from Jun 2009) | $0.39 in 2009 | −60% |
| Sears Holdings | 2003 → 25 Nov 2018 | $0.16 | −30% delisting return (the stock itself bounced +97% in Nov 2018, checked day by day) |
| Frontier Communications | 1980 → 29 Apr 2020 | $0.18 | −52% |
| Bed Bath & Beyond | 1992 → 20 Jul 2023 | $0.08 | −7% |
| SVB Financial | 1987 → 12 May 2023 (OTC prices after 10 Mar) | $0.01 | −31% |
| Silvergate Capital | 2003 → 12 Jul 2023 | $0.38 | −50% |

**Why check 1 is "qualified".** The CRSP count falls from 6,109 to 3,554 between 2000 and 2012; ours falls from 3,406 to 2,899. CRSP's decline was mostly penny and illiquid stocks, which our pre-registered filters (price ≥ $1, $100k daily volume) exclude by design; the returns agree closely (check 2), so the composition matches where it matters. A direct search for missed listings found 30–45 stocks a year (about 1–1.5% of the universe) that traded above $1 with real volume but ended OTC without an electronic Form 25 (exchange-filed forms start in 2006). They are mostly later failures, so the benchmark is very slightly optimistic, equally for strategies and benchmark.

**Coverage.**
- 95–98% of listed stock-months are matched to an SEC company.
- Market cap is known for 96–98% of eligible stocks **from 2012**, 63% in 2011, 6% in 2009, and **none before 2009** (no XBRL share counts). Size buckets (micro / small / large) therefore start around 2012. Tests that start earlier (S1 from 2006, S2 from 2009) need a pre-registered alternative benchmark for those years, or start in 2012.

## Data problems V0 found and fixed (each is now a rule in the code, with a test)

1. **EODHD files each stock under its last ticker and exchange.** WaMu's NYSE years are under `WAMUQ` (OTC). Downloading only NYSE/Nasdaq-labelled stocks would have dropped the bankruptcies. All 50,879 common-stock series were downloaded; listing periods come from SEC Form 25 filings.
2. **Duplicates:** EODHD keeps old-ticker series next to a series with the same history (1,849 same-company, 868 more by identical returns). Counting both would double-count firms and book fake delistings.
3. **Ticker changes** start new series; same-company series are chained (32 cases) and returns stitched with raw closes.
4. **Splices:** old and new equity glued together after a bankruptcy (Weatherford: $0.017 → $24.50 in one day). Cut into two securities (782 cuts).
5. **Missed reverse splits:** EODHD's split list lacks many small-cap reverse splits; a ×10 jump from a penny price is corrected (4,338 cases).
6. **Scale breaks:** Whiting Petroleum's series jumps from $2,099 to $7. A one-day 90% fall that lands above $1 is a vendor error; falls that end in pennies (Lehman) are kept.
7. **Bad prints:** placeholders like First Guaranty Bancshares at $1,000,000 for weeks; alternating prices of two securities (Terra Industries). Removed if they revert (67,024 days).
8. **Wrong market caps:** SEC share-count typos (Seagate with 317 trillion shares) and back-adjusted "raw" closes. Market cap is checked against the 10-K public float, dollar turnover and total assets; failures leave the universe.
9. **Wrong company matches:** Overstock's history was filed under `BBBY`; old GM's series overlaps new GM. Fixed by voting on the ticker only when it was in use, and by excluding a recycled ticker's current owner.
10. **SEC bulk submissions file stores some acceptance times in Eastern time while labelling them UTC** (4–5 hour errors). Fundamentals use the Financial Statement Data Sets (checked against EDGAR headers: 20/20); 8-K timing must use filing dates only.
11. **Foreign IPOs slipped in through form 424B4** (BioNTech with a 227-billion share typo). The universe now requires 10-K/10-Q or S-1 filings and no 20-F/40-F.

Tests: `python -m pytest tests/stocks -q` (35 tests).
