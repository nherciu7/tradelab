"""Phase S: long-only US stock selection research (see docs/stocks/STOCK_PLAN.md).

Modules
  paths      where the data lives
  http       polite downloads (SEC fair-access rules)
  french     Ken French library parsers (factors, breakpoints, portfolios)
  fred       FRED series

The rules every module follows are docs/BACKTEST_TRAPS.md, traps #28-#53: survivorship-free
prices, first-reported fundamentals dated by SEC acceptance, trade at the next close.
"""
