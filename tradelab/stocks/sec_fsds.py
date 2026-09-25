"""SEC Financial Statement Data Sets -> first-reported fundamentals, dated by acceptance.

Source: https://www.sec.gov/dera/data/financial-statement-data-sets (quarterly zips,
downloaded by scripts/stocks/fetch_free.py). Each zip has
    sub.txt  one row per filing (adsh): cik, name, sic, business address, form,
             period, fy, fp, filed, accepted (EDGAR acceptance timestamp, ET)
    num.txt  one row per reported number: adsh, tag, version, ddate (period end
             the number refers to), qtrs (0 = point in time, 1 = quarter, 4 = year),
             uom, segments, coreg, value
The data sets begin in 2009q2 (2009q1 is empty). Smaller companies start in
mid-2011 (XBRL phase-in).

Rules (docs/BACKTEST_TRAPS.md):
  #30  a value is known from its filing's `accepted` time, never its period end;
       it is first tradable at the close of the next trading day.
  #31  only the FIRST filing that reported (cik, tag, ddate, qtrs, uom) counts.
       Later comparatives and amendments (restatements) are ignored.
Only face-statement numbers are kept: empty `segments` and empty `coreg`
(no business-segment or subsidiary breakdowns).

    build(first=None, last=None)  parse all zips -> built/fsds_sub.parquet, fsds_num.parquet
    load_sub(), load_num()        the built tables
    first_reported(num)           one row per (cik, tag, ddate, qtrs, uom), earliest acceptance
"""
from __future__ import annotations

import csv
import zipfile
from pathlib import Path

import pandas as pd

from . import paths

FORMS = {"10-K", "10-Q", "10-KT", "10-QT", "10-K/A", "10-Q/A", "10-KT/A", "10-QT/A"}

# The tags the Phase S tests need. Several concepts have alternative tags;
# fundamentals.py picks among them in a fixed, documented order.
TAGS = {
    # balance sheet (qtrs = 0)
    "AssetsCurrent", "Assets", "LiabilitiesCurrent", "Liabilities",
    "LiabilitiesAndStockholdersEquity", "StockholdersEquity",
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    "PreferredStockValue", "PreferredStockValueOutstanding", "PreferredStockSharesOutstanding",
    "TemporaryEquityCarryingAmountAttributableToParent",
    "LongTermDebtNoncurrent", "LongTermDebt", "LongTermDebtAndCapitalLeaseObligations",
    "DebtCurrent", "LongTermDebtCurrent", "ShortTermBorrowings",
    "CashAndCashEquivalentsAtCarryingValue", "Goodwill", "IntangibleAssetsNetExcludingGoodwill",
    "CommonStockSharesOutstanding", "CommonStockSharesIssued", "TreasuryStockShares",
    "MinorityInterest",
    # income statement (qtrs = 1 or 4; 2/3 are year-to-date in 10-Qs)
    "Revenues", "SalesRevenueNet", "RevenueFromContractWithCustomerExcludingAssessedTax",
    "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueGoodsNet",
    "CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold", "GrossProfit",
    "OperatingIncomeLoss", "NetIncomeLoss", "ProfitLoss",
    "NetIncomeLossAvailableToCommonStockholdersBasic",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
    "EarningsPerShareBasic", "EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted",
    "WeightedAverageNumberOfSharesOutstandingBasic",
    "WeightedAverageNumberOfDilutedSharesOutstanding",
    "CommonStockDividendsPerShareDeclared", "CommonStockDividendsPerShareCashPaid",
    # cash flow
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    "PaymentsOfDividends", "PaymentsOfDividendsCommonStock",
    "ProceedsFromIssuanceOfCommonStock",
    # cover page (rarely present in these data sets; see sec_companyfacts)
    "EntityCommonStockSharesOutstanding",
}

SUB_COLS = ["adsh", "cik", "name", "sic", "countryba", "stprba", "cityba", "countryinc",
            "afs", "fye", "form", "period", "fy", "fp", "filed", "accepted", "prevrpt"]
NUM_COLS = ["adsh", "tag", "ddate", "qtrs", "uom", "segments", "coreg", "value"]


def _read(z: zipfile.ZipFile, name: str, usecols, chunksize=None):
    return pd.read_csv(z.open(name), sep="\t", usecols=usecols, dtype=str,
                       quoting=csv.QUOTE_NONE, encoding="utf-8", encoding_errors="replace",
                       on_bad_lines="warn", chunksize=chunksize, keep_default_na=False)


def parse_quarter(zip_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(sub, num) for one quarterly zip, filtered to 10-K/10-Q filings and TAGS."""
    with zipfile.ZipFile(zip_path) as z:
        sub = _read(z, "sub.txt", lambda c: c in SUB_COLS)
        sub = sub[sub["form"].isin(FORMS)]
        keep = set(sub["adsh"])
        parts = []
        for ch in _read(z, "num.txt", lambda c: c in NUM_COLS, chunksize=1_000_000):
            if "segments" not in ch:
                ch["segments"] = ""
            ch = ch[ch["tag"].isin(TAGS) & ch["adsh"].isin(keep)
                    & (ch["segments"] == "") & (ch["coreg"] == "")]
            parts.append(ch.drop(columns=["segments", "coreg"]))
    num = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=NUM_COLS)
    sub = sub.assign(
        cik=sub["cik"].astype(int),
        sic=pd.to_numeric(sub["sic"], errors="coerce").astype("Int64"),
        period=pd.to_datetime(sub["period"], format="%Y%m%d", errors="coerce"),
        filed=pd.to_datetime(sub["filed"], format="%Y%m%d", errors="coerce"),
        accepted=pd.to_datetime(sub["accepted"].str[:19], errors="coerce"),
        fy=pd.to_numeric(sub["fy"], errors="coerce").astype("Int64"),
        source=zip_path.stem)
    num = num.assign(
        ddate=pd.to_datetime(num["ddate"], format="%Y%m%d", errors="coerce"),
        qtrs=pd.to_numeric(num["qtrs"], errors="coerce").astype("Int16"),
        value=pd.to_numeric(num["value"], errors="coerce"))
    return sub, num.dropna(subset=["value", "ddate"])


def build(verbose: bool = True) -> None:
    """Parse every downloaded quarter into two parquet tables."""
    subs, nums = [], []
    for zp in sorted((paths.SEC / "fsds").glob("*.zip")):
        s, n = parse_quarter(zp)
        subs.append(s)
        nums.append(n)
        if verbose:
            print(f"  {zp.stem}: {len(s):>6} filings, {len(n):>8} values", flush=True)
    sub = pd.concat(subs, ignore_index=True).drop_duplicates("adsh", keep="first")
    num = pd.concat(nums, ignore_index=True).drop_duplicates()
    sub.to_parquet(paths.BUILT / "fsds_sub.parquet", index=False)
    num.to_parquet(paths.BUILT / "fsds_num.parquet", index=False)


def load_sub() -> pd.DataFrame:
    return pd.read_parquet(paths.BUILT / "fsds_sub.parquet")


def load_num(tags=None) -> pd.DataFrame:
    filt = [("tag", "in", list(tags))] if tags else None
    return pd.read_parquet(paths.BUILT / "fsds_num.parquet", filters=filt)


def first_reported(num: pd.DataFrame, sub: pd.DataFrame) -> pd.DataFrame:
    """One row per (cik, tag, ddate, qtrs, uom): the value from the earliest-accepted
    filing that reported it (mistake #31), with that filing's metadata."""
    meta = sub[["adsh", "cik", "form", "fp", "fy", "period", "accepted", "sic", "countryba"]]
    df = num.merge(meta, on="adsh", how="inner")
    df = df.sort_values(["accepted", "adsh"])
    return df.drop_duplicates(["cik", "tag", "ddate", "qtrs", "uom"], keep="first")
