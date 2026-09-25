---
title: "I tested 139 trading ideas like a QA engineer. Three survived."
summary: "I wanted a trading system for a small account. So I wrote down what each idea should do, ran it on real data with real costs, and tried hard to break it. Most broke."
description: "139 trading ideas, tested the way I test software. 136 broke, 3 held up. The rules, what they made and lost in the backtest, and a public paper-trading scoreboard."
---

[[tiles]]

## The short version

Three rules survived everything I threw at them. In one line each:

- System A: a three-day trade in US government bonds at the end of every month. In the backtest, one contract (about {{a_capital_eur}} of capital) made money in {{a_winning_years}} of {{a_years}} years.
- System B: four trading days a month in the big stock indices. It held up over {{b_months}} months of data, and I still don't know why it works.
- System C: two days every June, when the Russell stock indices rebuild themselves. It made money in {{c_into_wins}} of {{c_events}} years, and from this December it happens twice a year.

The exact rules are further down, with what each one made and lost, and a tool that shows what an amount of your choice could have become. First, what failed, because that's how I know these three are worth a look.

## Why I started

I wanted a trading system that works on a small account.

I started where most people start: YouTube. ICT and "smart money" concepts, chart patterns, breakouts, reversals, VWAP, opening gaps, penny stocks. I wanted them to work. I'd seen enough screenshots of winning trades to half-believe they did.

At work, my job is to find the case where the software breaks. So I did the same here. For each idea I wrote down what should happen before looking at any result, ran it on real data with real costs, and tried hard to break it. {{ideas_rejected}} of {{ideas_tested}} broke. This page is about how they broke, and about the three that didn't.

The whole thing took 2 weeks in September 2026. That was only possible because Claude, Anthropic's AI, wrote and ran most of the code. I explain the split further down.

## How I tested

A [backtest](/glossary/#backtest) (running a rule on past prices to see what it would have done) is easy to fool, including by yourself. So every idea had to pass four gates. I wrote them down before the first test and didn't move them afterwards.

[[diagram:gates]]

1. It works in both halves of the history. Split the years in two. If one half made money and the other lost it, the idea is dead.
2. It's very unlikely to be luck. The measure is the [t-statistic](/glossary/#t-statistic), a number for how unlikely a result is to be luck. Most studies accept 2. I used 2.8, because when you test this many ideas, some will look good by chance.
3. It beats its own [benchmark](/glossary/#benchmark), not cash. A bond trade has to beat simply holding bonds on ordinary days.
4. The [placebo](/glossary/#placebo) fails. A placebo is the same trade on fake dates. If the fake dates make money too, the real dates aren't special.

The placebo killed more ideas than anything else. Take Treasury auctions, the days the US government sells new bonds: prices should rise around them, and they did, with a t of 2.93. Then I shifted every date by two weeks. The fake dates did better, t 6.62, because two weeks later is month end. The auctions had nothing to do with it. That month-end pattern later became System A.

Two more rules sat on top. Any setting I tuned was chosen on past years and tested on the following year, never the other way round ([walk-forward](/glossary/#walk-forward) testing). And anything that looked too good (a t above 5, or more than 30% a year) was checked against a list of known mistakes before I believed it. That list grew to {{traps}}. It's on the [traps page](/traps).

## The graveyard

[[chart:funnel]]

{{ideas_tested}} ideas went in. Most were things people actually trade: chart patterns, calendar effects, index rebalances, trend following, value investing, insider buying. Every idea with its own write-up is in the [graveyard](/graveyard), with the number that killed it.

### The strategies from the videos

I began with the ideas that feel like trading: breakouts, reversals, gaps, [VWAP](/glossary/#vwap), the patterns drawn on charts in every trading video. Here are ten of them, each with a sketch of how it's supposed to work and what happened when I tested it on minute-by-minute prices of four stock indices (DAX, Dow, Nasdaq and FTSE).

The number to watch is the result per €100 risked on a trade. A strategy worth trading has to stay clearly above zero, over thousands of trades, in most markets. None did.

[[gallery]]

Why they fail: over a single day, stock indices tend to snap back rather than keep going, so breakouts mostly fizzle. And every trade pays a small cost, which adds up over thousands of them.

### ICT: the evening I thought it worked

ICT (Inner Circle Trader, a popular "smart money" method on YouTube) got the most attention. Coded exactly as taught, it lost money over 866 trades (t {{ict_spec_t}}), and fake time windows did just as well.

Then I dropped one of its filters, and the backtest said t = {{ict_bug_t}}, positive on all eight markets. That's very hard to get by luck. For one evening I thought I'd found something. Then we found the bug: the engine was peeking at whether an order would fill before deciding to place it. Nobody can do that in real time.

With the bug fixed, I gave ICT every chance. I tried {{ict_configs}} combinations of its settings, times 38 filters and 3 ways of sizing trades, always choosing on past years and testing on the next one. On the years it hadn't seen, the result was t {{ict_oos_t}}, which is what luck looks like. The estimated chance that the tuning was simply [overfit](/glossary/#overfitting): {{ict_pbo}}.

### Penny stocks: 1 in 8 doubled, 1 in 4 halved

Before testing any [penny-stock](/glossary/#penny-stock) strategy, I looked at what simply happens to them. I took every US stock priced between $1 and $5 at any month end from 2000 to 2025, about 1.4 million cases, and checked where it was 12 months later.

[[chart:penny]]

{{penny_doubled}} had doubled. {{penny_halved}} had halved, and {{penny_delisted}} were [delisted](/glossary/#delisted). The typical one (the [median](/glossary/#median-and-1-in-10)) lost {{penny_median}}. Young companies, listed for less than three years, did worse: {{penny_young_halved}} halved and the median lost {{penny_young_median}}.

So the dream trade exists: about 1 in 8 doubled. You just can't tell in advance which one, and the typical penny stock went down.

### Buying the stocks that just exploded

The obvious next idea is to buy the ones that are already moving. I tested it the way a small account would actually trade it: every month, buy the 10 US stocks with the biggest one-day jump in the previous month, with a small monthly savings plan (€400 to start, €35 a month), from 2012 to 2026, with real trading costs and currency fees.

[[chart:s8]]

{{s8_deposited}} went in over 14 years. {{s8_end}} was left. The biggest losses were real collapses, including four bankruptcies and a fraud. The idea is now a list of stocks I avoid, not a strategy.

## Bugs that almost fooled me

Claude wrote most of the code, so Claude wrote most of the bugs. I'd have written plenty myself. What caught them was the process: the four gates, the placebos, and the rule that anything too good gets audited first. Here are six, each with the fake number and the real one.

[[bugs]]

## The three that held up

After {{ideas_rejected}} failures, three rules kept passing: in both halves of the data, against their benchmarks, and against placebos that should have killed them.

Two of them have a clear cause: someone is forced to trade at a known time, whatever the price. An [index fund](/glossary/#index-fund) has to follow its index, and that doesn't depend on anyone's opinion, so it keeps happening. The third works too, but I couldn't find out why.

Everything below is a backtest: what the rules would have done, after trading costs, before taxes. Each system has a small calculator. Type an amount and it shows what that amount did in every real year of the test.

### System A: month-end bonds

The US government borrows by selling [bonds](/glossary/#bond) called [Treasuries](/glossary/#treasury). Big bond indices add the newly issued ones at the end of every month, so every fund that tracks those indices has to buy more bonds in the last days of the month, whatever the price. Insurers and pension funds that follow the same indices do the same.

The rule: hold 2-year Treasuries for the last three trading days of every month, and nothing else. The rest of the month, you're out.

In practice it's one [futures contract](/glossary/#futures-contract) called [2YY](/glossary/#2yy), a small contract on the 2-year Treasury traded in Chicago. You sell it at the close three trading days before the month's last trading day. It's quoted as an interest rate, so selling it is a bet that bond prices rise. It settles by itself on the last day, so there's no exit order. One contract needs about {{a_capital_eur}} in the account: the broker's [margin](/glossary/#margin) (a deposit) plus the worst dip in 24 years.

[[money:a]]

[[chart:system-a]]

The chart shows two separate histories. In colour: 2002 to 2026, the years I found the rule on. In grey: 1976 to 2001, older data I never looked at while choosing the rule, which makes it the fairer test. It's weaker there: {{a_old_losing_years}} of {{a_old_years}} years lost money, and the worst year lost {{a_old_worst_year}} per contract. I'd rather you see that here than find out later.

To check that it's really about month end, I tested the same three-day hold at every other point in the month:

[[chart:windows]]

Month end came first in {{a_rank1_funds}} of {{a_funds}} bond funds I checked. It shows no sign of fading either: split into five-year blocks, the most recent one (2025 to 2026) is the strongest.

What could break it: the index providers could change their month-end rules. The contract settles at 3:00 pm New York time, not at the 4:00 pm close my backtest uses, and the last hour matters. Trading at the close could be thin. And a few month ends fall on days when the bond market closes early.

[Full rules, risks and stop conditions for System A](/systems/a)

### System B: turn of the month in stock indices

The rule: buy the main [stock indices](/glossary/#stock-index) (S&P 500, Nasdaq-100, Russell 2000, Dow, DAX and Euro Stoxx 50) at the close of the last trading day of the month, and sell at the close of the fourth trading day of the next month. Four days in, the rest of the month out. It skips an index when that index is unusually jumpy ([volatility](/glossary/#volatility)), uses a [stop](/glossary/#stop), and puts more money into the calmer indices.

[[money:b]]

[[chart:system-b]]

It made money in only {{b_win}} of months. It works because the good months are bigger than the bad ones. The deepest fall from a peak ([drawdown](/glossary/#drawdown)) was {{b_max_dd}}.

The part that keeps me curious: I don't know why it works. I tested five explanations (pension contributions, funds that target a fixed level of risk, trend-following funds, the pause in company buybacks, a scramble for cash before month end) and all five failed. The full rule still holds in both halves of the data. A trade without a known cause is harder to trust, because you can't see it breaking coming. That's why it's second.

To trade it with futures, one Micro S&P 500 contract ([MES](/glossary/#mes)) needs {{b_mes_margin}} of margin, so realistically €3,000 to €5,000, and one contract means one index instead of six.

[Full rules, risks and stop conditions for System B](/systems/b)

### System C: the Russell rebuild

Every June, FTSE Russell rebuilds its US stock indices: companies move between the Russell 1000 (large companies) and the Russell 2000 (small ones). Funds that track them have to hold the new lists at the closing price on rebuild day, so thousands of trades hit small, thinly traded companies at the same moment.

The rule: two trading days before that close, buy small companies ([IWM](/glossary/#etf), a fund holding the Russell 2000) and [short](/glossary/#long-and-short) large ones (SPY, the S&P 500) with the same amount. Close both at the rebuild. Then do the opposite for five trading days while the move unwinds. It doesn't matter whether the market rises or falls, only whether small companies beat large ones on those days.

[[money:c]]

[[chart:system-c]]

The trade into the close made money in {{c_into_wins}} of {{c_events}} years, {{c_into}} [basis points](/glossary/#basis-point) on average (a basis point is 0.01%). The unwind is less reliable. Without borrowing it's a small trade in money terms, and with one event a year there are only {{c_events}} results in total.

From December 2026, Russell rebuilds twice a year. The first December rebuild takes effect after the close on Friday 11 December. It's the first live test of this system, and I'll post the result.

[Full rules, risks and stop conditions for System C](/systems/c)

## What an amount could have become

The calculators above show one year at a time. This one runs several years in a row, with the profits left in ([compounding](/glossary/#compounding)). It builds 2,000 possible futures, each made of real backtest years picked at random, and shows the spread: the typical outcome, a bad case and a good case.

Two things before you play with it. It's built from the past, and the future can be worse than any past year. And for System A, press the 1977–2001 button: same rule, older data, and the picture changes a lot.

[[projection]]

### All three together

The three systems trade at different times: A in the last days of each month, B across the turn of the month, C in June and December. So the same money can run all three, taking turns, and their results add up. Each simulated year uses the same real year for all three systems, so their good and bad years line up the way they really did. Start with the same amount as above to compare it with System A alone.

[[projection:all]]

## Paper-trading scoreboard

I'm starting to [paper-trade](/glossary/#paper-trading) all three now, in public: every trade logged on the day, without real money. The first System A result is due at the end of September 2026, and the first System C trade in December. The table updates as trades close. If you want the latest results, ask me anytime.

[[scoreboard]]

## How I worked with AI

This was an AI-assisted project: I directed it and made the decisions; Claude (Anthropic's AI) wrote most of the code and ran the tests.

My part: I chose the questions and the ideas, and set the goal (a mechanical system for a small account). The pass bar was mine, and so was pushing for more tests whenever something looked too easy. I approved the one purchase ({{data_spend}} of stock data), decided when to stop hunting, and decided what to publish. This page is my writing and my edit.

Claude's part: Claude Code, inside VS Code, wrote and ran most of the code and the tests. The Claude desktop app handled planning, reviews of research, audits, and the written instructions for the next session. AI research reports were only leads: they mixed real sources with wrong numbers, so every figure was checked at the original source.

An AI session forgets everything when it ends. So the project lives in one file, CLAUDE.md, that every session reads first: the rules, the current state, and the list of mistakes. Every time something fooled us, it went on the list, and every new result was checked against it.

Claude was wrong often, and confidently. It wrote the [look-ahead bug](/glossary/#look-ahead-bug) behind the fake ICT edge, the pass check that let a losing trade through, and the placebo that peeked at future earnings. It also found most of them, once the process pointed it in the right direction. A tool that's fast and sometimes confidently wrong is exactly why the testing mattered.

What I'd do differently: build the paper-trading log first, before the hunt, not at the end. And keep one tally from day one; my own notes disagreed about whether I'd tested 139 ideas or about 150.

## What I learned

- Most trading ideas don't survive a placebo. If moving the dates doesn't hurt the result, the dates weren't the reason.
- Two of the three survivors come from someone forced to trade on a schedule. Chart patterns never survived.
- A number that looks too good is usually a bug. The best results in this whole project were the fake ones.
- Costs decide small edges. Avoiding crypto funding payments was a real effect and still lost money after a 0.1% round trip.
- An AI is a very fast research assistant and a careless one. Give it tests it can't argue with.

## Questions

If you want to go through the rules, the numbers or the risks of any of the three, message me on [LinkedIn](https://www.linkedin.com/in/nichita-herciu/). I'm happy to share the paper-trading log as it fills up.

## Reproduce it

The stock half of the research is in the [GitHub repo](https://github.com/nherciu7/tradelab): the data pipeline, the validation gate, every stock test, the {{traps}} traps, three case studies, and 42 unit tests that run on synthetic data. You'll find the exact rules of A, B and C on their pages. Every chart here reads from `site/data`, which records the source file and the commit for each number. Licensed price data isn't included.
