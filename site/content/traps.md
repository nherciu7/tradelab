---
title: "53 ways I fooled myself"
summary: "Every mistake that produced a wrong result in this project at least once, in plain English."
description: "53 backtest traps from a trading research project: look-ahead bugs, cost errors, survivorship bias, vendor data problems, placebos that peeked, and how each was fixed."
---

Each of these produced a wrong number at least once: a fake edge, a hidden loss, or a test that couldn't fail. Once a trap was found, it went on this list, and every new result was checked against the whole list before I believed it. The numbering is stable because the code refers to it.

The technical version, with the fix for each, is in [BACKTEST_TRAPS.md](https://github.com/nherciu7/tradelab/blob/main/docs/BACKTEST_TRAPS.md).

[[traps-list]]
