---
title: "Glossary"
summary: "Every trading and testing word on this site, in plain language."
description: "Plain-language definitions of the trading and statistics terms used on tradelab: bonds, futures, margin, basis points, t-statistic, placebo, backtest and more."
---

## Money and markets

### Stock index

A basket of companies tracked as one number. The S&P 500 follows 500 large US companies; the Russell 2000 follows 2,000 small ones; the DAX follows 40 large German ones. When people say "the market went up", they usually mean an index.

### ETF

Exchange-traded fund: a fund you can buy like a share, which holds a whole index for you. SPY holds the S&P 500, QQQ the Nasdaq-100, IWM the Russell 2000, SHY short-term US government bonds.

### Index fund

A fund whose job is to hold exactly what its index holds. When the index changes, the fund has to trade, whatever the price. Two of the three systems on this site live off those forced trades.

### Bond

A loan you can buy and sell. A government or company borrows money and pays interest until it pays the loan back. When interest rates fall, existing bonds become worth more, and the other way round.

### Treasury

A bond issued by the US government. A 2-year Treasury pays back its loan after two years. Treasuries are among the most traded things in the world.

### Yield

The interest rate a bond pays, given its current price. Price and yield move in opposite directions: if the price goes up, the yield goes down.

### Futures contract

An agreement to buy or sell something later at a price fixed today. Traders use futures to bet on a price moving without paying the full value up front. You only put down a deposit (the margin).

### 2YY

The Micro 2-Year Yield future, a small futures contract on the 2-year US Treasury yield, traded on the CBOT exchange in Chicago. Each 0.01% move in the yield is worth $10 per contract. Because it is quoted in yield, selling it is a bet that bond prices will rise. System A trades it.

### MES

The Micro E-mini S&P 500 future: a small futures contract on the S&P 500 index.

### Margin

The deposit your broker holds while you have a futures position open. It is not a fee; it is there to cover losses. If losses eat into it, the broker closes your position.

### Long and short

Being long means you profit when the price rises (you bought). Being short means you profit when it falls (you sold something you borrowed, or sold a future). System C is long one index and short another at the same time, so it only cares about the difference between them.

### Leverage

Controlling more money in the market than you have in the account. One 2YY contract moves like about $50,000 of bonds but needs only a few hundred euros of margin. Leverage multiplies gains and losses.

### Basis point

One hundredth of a percent (0.01%). A move of 43 basis points is a move of 0.43%. On €10,000, one basis point is €1.

### Round trip

Buying and later selling (or the reverse). Trading costs on this site are counted per round trip: commissions plus the difference between the buying and selling price.

### Volatility

How much a price usually moves. A volatile market swings a lot from day to day.

### ATR

Average true range: how far a price usually moves in a day, averaged over recent days. System B places its stop a fixed fraction of the ATR below the entry.

### Stop

An order that closes a trade automatically if the price moves against you by a set amount, to cap the loss.

### VWAP

Volume-weighted average price: the average price of the day so far, where busy moments count more. Many intraday traders treat it as the day's "fair" price.

### Penny stock

A cheap share, here one priced between $1 and $5. Often small, young companies.

### Delisted

A share that stops trading on its exchange, usually because the company went bankrupt, was taken over, or fell below the exchange's rules.

## Testing words

### Backtest

Running a trading rule on past prices to see what it would have done. A backtest can only say what would have happened, never what will happen, and it's easy to fool yourself with one. Most of this site is about how.

### Paper trading

Following a system in real time and writing down every trade, without real money. It tests the rules on data that didn't exist when they were written.

### t-statistic

A number that says how unlikely a result is to be luck. Around 2 means "probably not luck" in most studies. I required 2.8, because when you test many ideas, some will look good by accident.

### Placebo

The same trade on fake dates. If moving the dates doesn't hurt the result, the dates weren't the reason, and the idea fails.

### Benchmark

What the idea has to beat. Not "doing nothing", but the obvious alternative, such as holding the same bonds on ordinary days.

### Walk-forward

A way to tune settings honestly: choose them on past years, test on the next year, and repeat. The test years never influence the choice.

### Overfitting

Tuning a rule so closely to past data that it describes the noise, not a real pattern. Overfit rules look great in a backtest and fail afterwards.

### Look-ahead bug

A backtest that accidentally uses information that wasn't available yet at the time of the trade. It makes fake profits. The ICT "edge" on this site was one.

### Survivorship bias

Testing only on companies that still exist today. It hides every company that went bust, so results look better than they were.

### R

The amount risked on one trade (the distance to the stop). "+0.1 R" means an average profit of 10% of what was risked, or €10 per €100 risked.

### Drawdown

A fall from a previous high. "Deepest fall from a peak: 12.7%" means that at its worst, the account was 12.7% below its best point so far.

### Median and "1 in 10"

The median is the middle result: half were better, half worse. A "1 in 10" bad case means only one result in ten was worse.

### Compounding

Leaving profits in so they earn profits too. In the System A projection, profits buy more contracts as the account grows.
