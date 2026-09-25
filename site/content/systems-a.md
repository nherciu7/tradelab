---
title: "System A: month-end bonds"
summary: "Hold 2-year US government bonds for the last three trading days of each month. The strongest of the three, and the first one I'm paper-trading."
description: "The exact rules of System A (month-end Treasury buying, traded with the Micro 2-Year Yield future), what it made and lost per contract in the backtest, what could break it, and when I'd stop."
---

[[money:a]]

## Who has to trade

The US government borrows by selling [bonds](/glossary/#bond) called [Treasuries](/glossary/#treasury). Big bond indices add the newly issued ones at the end of every month, so the index gets a little longer. Every fund that tracks those indices has to buy more bonds in the last days of the month to keep up, and insurers and pension funds that follow the same indices do the same. The buying is set by the calendar, not by anyone's view on interest rates.

## The rules

1. Find L, the last trading day of the month, on the CBOT futures calendar. Use the exchange's calendar, never the last date in a data file.
2. At the close three trading days before L (call it L−3), sell one Micro 2-Year Yield future ([2YY](/glossary/#2yy)) for the current contract month. It's quoted as an interest rate ([yield](/glossary/#yield)), so selling it is a bet that bond prices rise.
3. Do nothing else. The contract settles in cash at the 3:00 pm New York price on L, so there's no exit order. No [stop](/glossary/#stop) and no profit target, apart from an emergency stop for a disaster.
4. Stay out for the rest of the month.
5. Size: one contract per about €594 of account ([margin](/glossary/#margin) plus the worst dip in 24 years).
6. Special days: if L falls on a day the bond market closes early (31 December, the Friday after Thanksgiving) or near Good Friday, check the settlement rules with the exchange before trading that month.

## The backtest

[[chart:system-a]]

Per contract, after $2.50 of costs per [round trip](/glossary/#round-trip), before taxes. 2002 to 2026 is modelled on SHY, an [ETF](/glossary/#etf) that holds 1–3 year Treasuries, scaled to the contract, with the fund's interest income removed, since a future doesn't earn it. 1976 to 2001 uses the Federal Reserve's daily 2-year yields, and I never looked at that period when choosing the rule.

The older period is weaker (t {{a_old_t}}, just under my 2.8 bar) and lost money in {{a_old_losing_years}} of {{a_old_years}} years. I show it because it's the fairer test. Try it in the calculator on the [main page](/#what-an-amount-could-have-become): the difference is large.

[[table:a-evidence]]

## Checking that it's month end

The same three-day hold, moved to every other point in the month, earns a fraction of it. If the effect were just bonds going up over time, every window would earn about the same.

[[chart:windows]]

[[table:a-windows]]

## Capital

One contract needs {{a_capital_eur}}: the broker's maintenance margin ({{a_margin}}) plus the worst dip inside a month in 2002 to 2026 ({{a_worst_dip}}), converted at 1.08 dollars per euro. On the 1976 to 2001 data the worst dip was bigger, and the same rule would have needed {{a_old_capital_eur}}. One contract moves like about $50,000 of bonds, so this is [leverage](/glossary/#leverage): gains and losses are large compared with the money in the account.

## What could break it

- The index providers change how they add new bonds at month end.
- Settlement is at 3:00 pm New York time, not the 4:00 pm close the backtest uses. A good part of the move happens on the last day, so the last hour matters.
- The price at the close may be thin, so the real cost could be higher than $2.50.
- You need a broker that gives access to CBOT futures.
- Early-close days and holidays near month end need checking with the exchange each time.

## When I'd stop

Written before any live result, and not changed since:

[[kill:a]]

Plus practical checks: don't start (or stop) if the gap between the buying and selling price at 15:45 New York time is wider than 3 ticks on two checks, or if the average all-in cost goes above $10 per round trip over 6 trades. And every September I rerun the window check; if month end no longer comes first, it's time to stop.

## Questions

Message me on [LinkedIn](https://www.linkedin.com/in/nichita-herciu/) if you want to go through the rules or the numbers. The paper-trading results are on the [scoreboard](/#paper-trading-scoreboard).

Later, reading around, I found that researchers have written about similar month-end patterns in Treasuries: Hartley and Schwarz, [Predictable End-of-Month Treasury Returns](https://www.kristaschwarz.com/EOM.pdf) (2019).
