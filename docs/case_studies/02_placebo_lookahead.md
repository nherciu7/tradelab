# Case study 2: a placebo that manufactured a fake lead (trap #53)

**Summary.** A placebo meant to *kill* a result instead created a new "lead" at t = 6.0. It came from how the placebo chose its dates. Once audited and turned into a tradable rule, the lead lost money in-sample (2012–2026) and out-of-sample (2000–2011).

## The original test (S3)

Post-earnings drift in microcaps. The top decile of 3-day earnings-announcement returns, bought two days later and held 60 trading days, earned +0.64% a month over size-matched microcaps (t 3.27, academic, before costs; 6,110 events, 2012–2026).

The pre-registered placebo asked: do big 3-day moves **without** earnings news drift just as much? If so, the effect is generic continuation, not an earnings effect. For each real event, the placebo took the same stock on the **nearest** date within ±250 trading days that was at least 20 days from any announcement and had a 3-day move at least as big.

Result: the non-news moves drifted *more*, +1.72% a month (t 6.0). S3 failed on that basis, and "microcap continuation after big non-news moves" was recorded as a lead.

## The audit

A t above 5 triggers an audit (the project rule). The tradable version of the lead only uses information known at the time: big moves in eligible microcaps, no earnings filing in the prior 20 days, no merger filing, volume on the signal and entry days. It showed the opposite:

| Event type (SEC filings within 3 days) | Events | Excess / month | t |
|---|---|---|---|
| Merger-related filing | 1,770 | −1.11% | −2.34 |
| Other 8-K | 3,782 | −0.39% | −1.57 |
| No filing | 11,190 | −0.50% | −2.11 |
| Frozen rule (mergers out, volume required) | 15,865 | −0.51% | −2.24 |

So where did +1.72% come from? The placebo's date search looked **both ways** from each real earnings event, and picked many dates weeks *before* it. A placebo date up to about 60 trading days before a big earnings reaction has a holding window that **contains that future reaction**. Splitting the placebo events:

| S3 placebo events | Events | Excess / month | t |
|---|---|---|---|
| Hold contains the (future) earnings reaction | 1,674 | **+6.59%** | +10.24 |
| Placebo after the event | 2,167 | −0.85% | −2.72 |
| Placebo before the event, no overlap | 792 | −2.45% | −5.85 |

The whole "lead" came from the placebo being conditioned on a future jump. The hypothesis was written into the script's docstring before this split was computed (`scripts/stocks/l1_audit_placebo_origin.py`).

## The out-of-sample test anyway

The rule had been pre-registered for one run on 2000–2011, an independent period with its own validation checks and a dollar-volume proxy for microcaps (89% agreement with the market-cap definition on 2012–2026). It was run once: academic −0.45% a month (t −1.41); a 10-stock portfolio after costs −1.73% a month (t −2.65).

## Lessons

1. A placebo is code too, and it can have look-ahead. A placebo date may use only information known at that date.
2. The audit rule exists for exactly this: a lead at t = 6 was treated as a hypothesis to break, not a discovery.
3. The correction propagates. S3 still fails (its 10-stock portfolio lost after costs), but its stated reason ("non-news jumps drift more") was withdrawn.
