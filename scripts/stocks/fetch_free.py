"""Download the free data for Phase S (docs/stocks/STOCK_PLAN.md s2.1).

    python scripts/stocks/fetch_free.py french fred
    python scripts/stocks/fetch_free.py sec --user-agent "Name email@domain"
    python scripts/stocks/fetch_free.py sec-index --user-agent "..."   (optional, large)

Sources (each is logged in data/SOURCES.md with the retrieval date):
  french     Ken French Data Library: FF5 and momentum factors (monthly, daily),
             NYSE ME breakpoints, size deciles, momentum deciles.
  fred       FRED: AAA (Moody's Aaa yield), CPIAUCSL, DTB3, DEXUSEU (USD per EUR).
  sec        SEC Financial Statement Data Sets (2009q1+), Insider Transactions
             Data Sets (2006q1+), the bulk submissions.zip (per-company filing
             history with acceptance times and 8-K items), company_tickers_exchange.json,
             companyfacts.zip (all XBRL facts per company, for cover-page shares).
  sec-index  EDGAR quarterly form indexes (all filings by form type), 2006+.

Already-downloaded files are skipped, so the script can be rerun safely.
SEC requests are throttled to <= 5 a second and carry the User-Agent.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tradelab.stocks import paths  # noqa: E402
from tradelab.stocks.http import check_user_agent, download  # noqa: E402

FRENCH_BASE = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
FRENCH_FILES = [
    "F-F_Research_Data_Factors_CSV.zip",
    "F-F_Research_Data_Factors_daily_CSV.zip",
    "F-F_Research_Data_5_Factors_2x3_CSV.zip",
    "F-F_Research_Data_5_Factors_2x3_daily_CSV.zip",
    "F-F_Momentum_Factor_CSV.zip",
    "F-F_Momentum_Factor_daily_CSV.zip",
    "ME_Breakpoints_CSV.zip",
    "Portfolios_Formed_on_ME_CSV.zip",
    "Portfolios_Formed_on_ME_Daily_CSV.zip",
    "10_Portfolios_Prior_12_2_CSV.zip",
]
FRED_SERIES = ["AAA", "CPIAUCSL", "DTB3", "DEXUSEU"]

SEC_FSDS = "https://www.sec.gov/files/dera/data/financial-statement-data-sets/{y}q{q}.zip"
SEC_INSIDER = ("https://www.sec.gov/files/structureddata/data/"
               "insider-transactions-data-sets/{y}q{q}_form345.zip")
# from 2026q2 the SEC posts new insider files under a different folder
SEC_INSIDER_NEW = ("https://www.sec.gov/files/datastandardsinnovation/data/"
                   "insider-transactions-data-sets/{y}q{q}_form345.zip")
SEC_SINGLE = {
    "submissions.zip": "https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip",
    "company_tickers_exchange.json": "https://www.sec.gov/files/company_tickers_exchange.json",
    # every XBRL fact per company with its filing date and accession: the source of
    # dei:EntityCommonStockSharesOutstanding (cover-page shares), which the
    # Financial Statement Data Sets mostly omit
    "companyfacts.zip": "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip",
}
SEC_FORM_IDX = "https://www.sec.gov/Archives/edgar/full-index/{y}/QTR{q}/form.gz"


def quarters(first_year: int, today: date | None = None):
    today = today or date.today()
    for y in range(first_year, today.year + 1):
        for q in range(1, 5):
            if (y, q) < (today.year, (today.month - 1) // 3 + 1):
                yield y, q


def report(name: str, status: str) -> None:
    print(f"  {status:<22} {name}", flush=True)


REFRESH = False    # --refresh: re-download files that change over time (not quarterly zips)


def _fresh(path: Path) -> Path:
    if REFRESH and path.exists():
        path.unlink()
    return path


def fetch_french() -> None:
    print("Ken French library ->", paths.FRENCH)
    for f in FRENCH_FILES:
        report(f, download(FRENCH_BASE + f, _fresh(paths.FRENCH / f)))


def fetch_fred() -> None:
    print("FRED ->", paths.FRED)
    for s in FRED_SERIES:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={s}"
        report(s, download(url, _fresh(paths.FRED / f"{s}.csv")))


def fetch_sec(ua: str) -> None:
    print("SEC bulk files ->", paths.SEC)
    for name, url in SEC_SINGLE.items():
        report(name, download(url, _fresh(paths.SEC / name), ua))
    for y, q in quarters(2009):
        report(f"fsds {y}q{q}", download(SEC_FSDS.format(y=y, q=q),
                                         paths.SEC / "fsds" / f"{y}q{q}.zip", ua))
    for y, q in quarters(2006):
        dest = paths.SEC / "insider" / f"{y}q{q}_form345.zip"
        status = download(SEC_INSIDER.format(y=y, q=q), dest, ua)
        if status.startswith("missing"):
            status = download(SEC_INSIDER_NEW.format(y=y, q=q), dest, ua)
        report(f"insider {y}q{q}", status)


def fetch_sec_index(ua: str) -> None:
    print("EDGAR form indexes ->", paths.SEC / "form_idx")
    for y, q in quarters(2006):
        report(f"form.idx {y}Q{q}", download(SEC_FORM_IDX.format(y=y, q=q),
                                             paths.SEC / "form_idx" / f"{y}Q{q}.gz", ua))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", nargs="+", choices=["french", "fred", "sec", "sec-index"])
    ap.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT"))
    ap.add_argument("--refresh", action="store_true",
                    help="re-download files that change (French, FRED, SEC tickers, submissions, "
                         "companyfacts); quarterly zips are never re-downloaded")
    a = ap.parse_args()
    global REFRESH
    REFRESH = a.refresh
    if any(w.startswith("sec") for w in a.what):
        check_user_agent(a.user_agent)
    for w in a.what:
        {"french": fetch_french, "fred": fetch_fred,
         "sec": lambda: fetch_sec(a.user_agent),
         "sec-index": lambda: fetch_sec_index(a.user_agent)}[w]()


if __name__ == "__main__":
    main()
