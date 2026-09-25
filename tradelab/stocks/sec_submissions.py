"""SEC bulk submissions.zip -> company metadata and a filing index with acceptance times.

Source: https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip
(one JSON per CIK, plus CIK##########-submissions-NNN.json overflow files for
companies with long histories).

acceptanceDateTime carries a 'Z' and IS UTC: Hooker Furniture's 10-K
0001185185-11-000487 shows 2011-04-13T20:47:01Z here and 16:47 (ET) in the
Financial Statement Data Sets. We convert once to America/New_York wall time
(DST-aware) and store it tz-naive (backtest trap #13).

    build()            -> built/companies.parquet, built/filings.parquet
    load_companies(), load_filings(forms=None)

Filings kept (FORMS): 8-K (with items, e.g. '2.02' = results of operations),
10-K/10-Q, merger proxies and tender offers (delisting classification),
Form 25 (exchange delisting), Form 15 (deregistration), 20-F/40-F (foreign filers).
"""
from __future__ import annotations

import json
import zipfile

import pandas as pd

from . import paths

FORMS = {
    "8-K", "8-K/A", "10-K", "10-K/A", "10-Q", "10-Q/A", "10-KT", "10-QT", "10-K405",
    "DEFM14A", "DEFM14C", "PREM14A", "SC TO-T", "SC TO-T/A", "SC 14D9", "SC 14D9/A",
    "SC 13E3", "SC 13E3/A", "25", "25-NSE", "15-12B", "15-12G", "15-15D",
    "20-F", "40-F", "S-1", "424B4",
}
_FIELDS = ["accessionNumber", "filingDate", "reportDate", "acceptanceDateTime", "form", "items"]


def _rows(block: dict, cik: int):
    n = len(block.get("accessionNumber", []))
    cols = {f: block.get(f, [""] * n) for f in _FIELDS}
    for i in range(n):
        if cols["form"][i] in FORMS:
            yield (cik, cols["accessionNumber"][i], cols["form"][i], cols["filingDate"][i],
                   cols["reportDate"][i], cols["acceptanceDateTime"][i], cols["items"][i])


def build(verbose: bool = True) -> None:
    z = zipfile.ZipFile(paths.SEC / "submissions.zip")
    names = z.namelist()
    overflow: dict[str, list[str]] = {}
    for n in names:
        if "-submissions-" in n:
            overflow.setdefault(n[:13], []).append(n)
    companies, filings, bad = [], [], []
    main = [n for n in names if "-submissions-" not in n]
    for k, n in enumerate(main):
        try:
            d = json.loads(z.read(n))
        except json.JSONDecodeError:
            bad.append(n)            # a few files in the SEC bulk zip are empty
            continue
        # companies file forms 10-K/10-Q/8-K; individuals (insiders) are 'other' with no SIC
        if not d.get("sic") and d.get("entityType") != "operating":
            continue
        cik = int(d["cik"])
        b = (d.get("addresses") or {}).get("business") or {}
        companies.append({
            "cik": cik, "name": d.get("name"), "entity_type": d.get("entityType"),
            "sic": d.get("sic"), "category": d.get("category"),
            "tickers": "|".join(t for t in d.get("tickers", []) if t),
            "exchanges": "|".join(e for e in d.get("exchanges", []) if e),
            "state_business": b.get("stateOrCountry"), "foreign_business": b.get("isForeignLocation"),
            "state_inc": d.get("stateOfIncorporation"),
            "former_names": json.dumps(d.get("formerNames", [])),
        })
        filings.extend(_rows(d["filings"]["recent"], cik))
        for extra in overflow.get(n[:13], []):
            try:
                filings.extend(_rows(json.loads(z.read(extra)), cik))
            except json.JSONDecodeError:
                bad.append(extra)
        if verbose and k % 100_000 == 0:
            print(f"  {k:>7}/{len(main)} files, {len(companies)} companies, {len(filings)} filings",
                  flush=True)
    comp = pd.DataFrame(companies)
    comp["sic"] = pd.to_numeric(comp["sic"], errors="coerce").astype("Int64")
    f = pd.DataFrame(filings, columns=["cik", "accession", "form", "filing_date", "report_date",
                                       "acceptance_utc", "items"])
    acc = pd.to_datetime(f.pop("acceptance_utc"), utc=True, errors="coerce")
    f["accepted"] = acc.dt.tz_convert("America/New_York").dt.tz_localize(None)
    f["filing_date"] = pd.to_datetime(f["filing_date"], errors="coerce")
    f["report_date"] = pd.to_datetime(f["report_date"], errors="coerce")
    f = f.drop_duplicates(["cik", "accession"])
    comp.to_parquet(paths.BUILT / "companies.parquet", index=False)
    f.to_parquet(paths.BUILT / "filings.parquet", index=False)
    if verbose:
        print(f"done: {len(comp)} companies, {len(f)} filings; "
              f"{len(bad)} unreadable files skipped: {bad[:5]}")


def load_companies() -> pd.DataFrame:
    return pd.read_parquet(paths.BUILT / "companies.parquet")


def load_filings(forms=None) -> pd.DataFrame:
    filt = [("form", "in", list(forms))] if forms else None
    return pd.read_parquet(paths.BUILT / "filings.parquet", filters=filt)
