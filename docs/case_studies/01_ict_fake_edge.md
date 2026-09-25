# Case study 1: a t = 5.74 intraday "edge" that was a look-ahead bug

**Summary.** A popular discretionary intraday method ("ICT" / smart-money concepts) was coded exactly as specified and failed. A variant of it then showed +3.38 bps per trade at t = 5.74 over 5,898 trades, positive on 8 of 8 instruments. It was an engine bug: the simulator had looked into the future. Rebuilt correctly, the best walk-forward version had an out-of-sample t of +0.90.

## The test

The rules followed the method's published 2022 model: in a morning "killzone", wait for a liquidity sweep of a prior high or low, a market-structure shift, a displacement bar at least 1.5 × ATR, and a fair-value gap. Enter with a limit order at the gap and put the stop beyond the sweep, with a 2.5 R target. It ran on 5-minute bars of eight markets (EURUSD, GBPUSD, S&P 500, Nasdaq-100, Dow, Russell 2000, DAX, FTSE).

| Version | Trades | bps per trade | t | Instruments positive |
|---|---|---|---|---|
| The method as specified | 866 | −2.71 | −1.51 | 2 of 8 |
| Placebo: a fake killzone (11:00–13:30) | 165 | −2.81 | −0.98 | 1 of 8 |
| **Variant: no displacement filter** | **5,898** | **+3.38** | **+5.74** | **8 of 8** |
| Same variant, fake killzone 11:00–13:30 | 4,441 | +1.96 | +3.91 | 8 of 8 |
| Same variant, fake killzone 13:30–16:00 | 3,242 | +1.22 | +2.45 | 7 of 8 |

## The first warning: the placebos passed too

The variant's "edge" appeared almost as strongly in killzones the method says are meaningless. A real effect tied to the morning session should not survive being moved to the afternoon. A placebo that passes means the result comes from something other than the hypothesis, often from the engine.

## The bug

When a setup's limit order expired unfilled, the engine moved on to the next setup of the day. But to know the order would expire unfilled, it had already looked at prices up to the fill deadline. So the choice of which setup to take depended on prices the trader could not yet have seen, a selection that is impossible in real time. The bug matters when setups overlap within a day, and dropping the displacement filter multiplied them: 866 trades became 5,898.

**Fix (trap #1):** replay each day bar by bar, in time order. At most one working order exists; a newer setup replaces it; every decision uses only bars already closed. Three more fill conventions were tightened at the same time: a fill needs a trade-through of one tick (#4), only the stop can be hit on the fill bar (#3), and a bar that touches the stop "before" the fill is a fill plus a stop-out (#2).

## The second warning: bps positive, R negative

Even the buggy variant earned +3.38 bps but **−0.128 R** per trade. A small positive average in basis points hid a negative expectancy per unit of risk, because the stop distances varied widely. At fixed notional the equity curve grew ×6.9; at a fixed 0.5% risk per trade it fell to ×0.016 (trap #18).

## After the fix

The corrected engine was optimised over 34,560 parameter configurations × 38 filters × 3 sizing rules, **walk-forward** (parameters chosen on past years only, tested on the next year):

- out-of-sample t: **+0.90**;
- probability of backtest overfitting (PBO, CSCV): **51%**, a coin flip;
- the best in-sample configuration, which is what a backtest video would show, is not an estimate of live performance.

## Lessons

1. A t above 5 on intraday data is a reason to audit, not to celebrate.
2. Placebos that also pass point at the engine.
3. Report results in R as well as in bps.
4. Only a time-ordered replay can be trusted with order logic.
