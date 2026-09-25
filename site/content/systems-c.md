---
title: "System C: the Russell rebuild"
summary: "Long small companies against large ones into the Russell index rebuild, then the reverse. Once a year until now, twice a year from December 2026."
description: "The exact rules of System C (Russell reconstitution, IWM vs SPY), 27 years of events, the December 2026 paper trade, what could break it, and when I'd stop."
---

[[money:c]]

## Who has to trade

Every June, FTSE Russell rebuilds its US stock indices: companies move between the Russell 1000 (large companies) and the Russell 2000 (small ones), or join and leave. [Index funds](/glossary/#index-fund) that track them must hold the new lists at the closing price on rebuild day, whatever that price is. Thousands of names change hands at once, in small companies that don't trade much.

The move arrives at the deadline; it isn't anticipated. Holding the same pair from the ranking date in late April, or from a month or two weeks before, was no better than luck (t between 0.46 and 0.83). Only the last two sessions carry it reliably.

## The rules (June)

1. Rebuild day is the last Friday of June (FTSE Russell publishes the date months ahead; check it each May).
2. At the close two trading days before it, buy small companies (IWM, an [ETF](/glossary/#etf) of the Russell 2000) and [short](/glossary/#long-and-short) large ones (SPY, the S&P 500), equal amounts.
3. Close both at the rebuild-day close.
4. At that same close, open the reverse: short IWM, long SPY, equal amounts.
5. Close the reverse at the close five trading days later.

Costs in the backtest: 8 [basis points](/glossary/#basis-point) for each leg-trade, both ETFs together.

## December 2026: the first paper trade

From 2026, Russell rebuilds twice a year. The first December rebuild takes effect after the close on Friday 11 December 2026.

- Long IWM / short SPY from the close of Wednesday 9 December to the close of Friday 11 December.
- Then short IWM / long SPY from the Friday 11 December close to the close of Friday 18 December.

Expect it to be smaller than June. In FTSE Russell's November 2025 trial run, Russell 2000 turnover was about half of June's, and December will add buffers that cut it further. There's no December history to backtest, so this one is paper only.

## The backtest (June, 2000 to 2026)

[[chart:system-c]]

Per event, in basis points (0.01%) of the amount on each side, after costs, before taxes, without borrowing. One event a year means {{c_events}} data points in total, so there's no honest way to split them into years for finding the rule and years for testing it. The first leg clears my bar (t {{c_into_t}}). The unwind doesn't on its own (t {{c_unwind_t}}), so I treat it as a bonus.

[[table:c-evidence]]

## What could break it

- FTSE Russell changes the method so fewer companies move. Twice-yearly rebuilds and buffers both reduce it.
- It's a small sample. Twenty-seven years is all there is.
- The unwind is noisy: its worst year lost {{c_unwind_worst}} basis points.
- Shorting SPY needs a broker account that allows it.

## When I'd stop

[[kill:c]]

Also: stop if FTSE Russell changes the method so that the share of the index that changes falls below about 5%.

## Questions

Message me on [LinkedIn](https://www.linkedin.com/in/nichita-herciu/) if you want to go through the rules or the numbers. The December paper trade will be on the [scoreboard](/#paper-trading-scoreboard).

Later I found that researchers have studied price moves around the Russell rebuild, for example Madhavan, [The Russell Reconstitution Effect](https://www.tandfonline.com/doi/abs/10.2469/faj.v59.n4.2545) (2003).
