---
title: "System B: turn of the month in stock indices"
summary: "Buy the big stock indices on the last day of the month, sell on the fourth day of the next. It held up over 35 years of data, and I still don't know why."
description: "The exact rules of System B (turn of the month in six stock indices), what it made and lost in the backtest, the five explanations that failed, what could break it, and when I'd stop."
---

[[money:b]]

## Why it works: I don't know

I tried to find out. I tested five explanations, and each one failed its own prediction:

- Pension contributions at the start of each quarter. Quarter starts were the weakest months, not the strongest.
- Funds that target a fixed level of risk and rebalance. The effect was there all month and weakest exactly at the turn.
- Trend-following funds changing their positions.
- Companies pausing their share buybacks before earnings. The pattern ran backwards.
- A scramble for cash before month end. The dip it predicts wasn't there.

So this is a rule that works without a known cause. That makes it harder to trust, and it's why System B comes second.

## The rules

1. At the close of the last trading day of the month, buy each [stock index](/glossary/#stock-index) in the basket: S&P 500 (SPY), Nasdaq-100 (QQQ), Russell 2000 (IWM), Dow Jones, DAX and Euro Stoxx 50.
2. Skip an index that month if it has been unusually jumpy: its 21-day [volatility](/glossary/#volatility) is above the 80th percentile of its own past year.
3. Put more money in the calmer indices: weight each by 1 ÷ its 60-day volatility.
4. Stop: 0.75 × [ATR](/glossary/#atr)(14) below the open of the first day of the new month.
5. Otherwise, sell at the close of the fourth trading day of the new month.

Costs in the backtest: 4 [basis points](/glossary/#basis-point) each way. Code: `totm(before=1, after=3, vol_pctile=0.80, vol_len=21, sl_atr=0.75)`, weighted as in `sysb_mechanism.monthly()`.

## The backtest

[[chart:system-b]]

Results are in basis points of the amount traded (0.01% each), after costs, before taxes, without borrowing. The history starts in February 1991; until about 1993 only the DAX has enough past data for the volatility filter, so the early years are a one-index version.

Much of the return is simply being in stocks for four days a month, so its losses come with market falls: the worst month was March 2009. On the S&P 500 alone, the plain turn of the month (without the filter and stop) is no stronger than days 9 to 12 of the month. The full rule still passes in both 2002 to 2013 and 2014 to 2026.

[[table:b-evidence]]

## Capital

With futures, one Micro S&P 500 contract ([MES](/glossary/#mes)) needs {{b_mes_margin}} of maintenance [margin](/glossary/#margin), so realistically €3,000 to €5,000 of account for one contract through a bad month. One contract also means one index, a weaker version of the six-index rule above.

## What could break it

- Nobody knows the cause, so there's no way to see a change in the cause coming.
- It's in stocks for four days a month. A crash in those days hits it fully.
- With one contract, it's a single-index version with bigger swings than the backtest basket.

## When I'd stop

[[kill:b]]

Also: don't start with real money if the MES overnight margin rises above $3,000, or if the account is below 1.5 times the margin.

## Questions

Message me on [LinkedIn](https://www.linkedin.com/in/nichita-herciu/) if you want to go through the rules or the numbers. The paper-trading results are on the [scoreboard](/#paper-trading-scoreboard).

Later I found that a turn-of-the-month pattern in stocks has been written about for a long time, for example by Ariel ([A monthly effect in stock returns](https://econpapers.repec.org/RePEc:eee:jfinec:v:18:y:1987:i:1:p:161-174), 1987) and Lakonishok and Smidt ([Are seasonal anomalies real?](https://academic.oup.com/rfs/article-abstract/1/4/403/1566965), 1988).
