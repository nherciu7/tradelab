"""SEC Insider Transactions Data Sets (Forms 3/4/5) -> transactions and a ticker map.

Source: https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets
(quarterly zips from 2006q1; tab-separated SUBMISSION, REPORTINGOWNER, NONDERIV_TRANS, ...).

Outputs (built/):
  insider_trans.parquet   open-market purchases (P) and sales (S) of non-derivative
                          securities from ORIGINAL Forms 4 (amendments 4/A dropped:
                          first reported only, mistake #31). One row per transaction,
                          with the filing date (the signal date, mistake #32), issuer
                          CIK and ticker as filed, and the filing's reporting owners.
  issuer_symbols.parquet  (issuer_cik, symbol, filing_date) from every Form 3/4/5:
                          the raw material for the point-in-time ticker->CIK map
                          (mistake #34).

A filing can list several reporting owners (e.g. a director and his trust, or a
fund and its general partner). They are kept together on one row per transaction
(`owner_ciks`, '|'-joined) so a single joint filing can never be counted as two
insiders. Relationship flags are OR-ed across the filing's owners.
"""
from __future__ import annotations

import csv
import zipfile

import pandas as pd

from . import paths

CODES = {"P", "S"}


def _read(z: zipfile.ZipFile, name: str, cols: list[str]) -> pd.DataFrame:
    return pd.read_csv(z.open(name), sep="\t", dtype=str, quoting=csv.QUOTE_NONE,
                       usecols=lambda c: c in cols, keep_default_na=False,
                       encoding="utf-8", encoding_errors="replace", on_bad_lines="warn")


def _date(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, format="%d-%b-%Y", errors="coerce")


def parse_quarter(zip_path) -> tuple[pd.DataFrame, pd.DataFrame]:
    with zipfile.ZipFile(zip_path) as z:
        sub = _read(z, "SUBMISSION.tsv", ["ACCESSION_NUMBER", "FILING_DATE", "PERIOD_OF_REPORT",
                                          "DOCUMENT_TYPE", "ISSUERCIK", "ISSUERNAME",
                                          "ISSUERTRADINGSYMBOL", "AFF10B5ONE"])
        own = _read(z, "REPORTINGOWNER.tsv", ["ACCESSION_NUMBER", "RPTOWNERCIK",
                                              "RPTOWNER_RELATIONSHIP", "RPTOWNER_TITLE"])
        tr = _read(z, "NONDERIV_TRANS.tsv", ["ACCESSION_NUMBER", "SECURITY_TITLE", "TRANS_DATE",
                                             "TRANS_CODE", "TRANS_SHARES", "TRANS_PRICEPERSHARE",
                                             "TRANS_ACQUIRED_DISP_CD", "SHRS_OWND_FOLWNG_TRANS",
                                             "DIRECT_INDIRECT_OWNERSHIP"])
    sub.columns = [c.lower() for c in sub.columns]
    own.columns = [c.lower() for c in own.columns]
    tr.columns = [c.lower() for c in tr.columns]
    sub["filing_date"] = _date(sub["filing_date"])
    sub["issuercik"] = pd.to_numeric(sub["issuercik"], errors="coerce").astype("Int64")

    symbols = (sub[["issuercik", "issuertradingsymbol", "filing_date", "document_type"]]
               .rename(columns={"issuercik": "issuer_cik", "issuertradingsymbol": "symbol"}))
    symbols["symbol"] = symbols["symbol"].str.strip().str.upper()

    rel = own["rptowner_relationship"].fillna("")
    own = own.assign(is_director=rel.str.contains("Director"),
                     is_officer=rel.str.contains("Officer"),
                     is_ten_pct=rel.str.contains("TenPercent"),
                     is_other=rel.str.contains("Other"))
    owners = own.groupby("accession_number").agg(
        owner_ciks=("rptownercik", lambda x: "|".join(sorted(set(x)))),
        n_owners=("rptownercik", "nunique"),
        is_director=("is_director", "any"), is_officer=("is_officer", "any"),
        is_ten_pct=("is_ten_pct", "any"), is_other=("is_other", "any"),
        officer_title=("rptowner_title", lambda x: "|".join(t for t in x if t)))

    tr = tr[tr["trans_code"].isin(CODES)]
    tr = tr.merge(sub[sub["document_type"] == "4"], on="accession_number", how="inner")
    tr = tr.merge(owners, left_on="accession_number", right_index=True, how="left")
    out = pd.DataFrame({
        "accession": tr["accession_number"],
        "filing_date": tr["filing_date"],
        "trans_date": _date(tr["trans_date"]),
        "issuer_cik": tr["issuercik"],
        "symbol": tr["issuertradingsymbol"].str.strip().str.upper(),
        "issuer_name": tr["issuername"],
        "security_title": tr["security_title"],
        "code": tr["trans_code"],
        "acq_disp": tr["trans_acquired_disp_cd"],
        "shares": pd.to_numeric(tr["trans_shares"], errors="coerce"),
        "price": pd.to_numeric(tr["trans_pricepershare"], errors="coerce"),
        "shares_after": pd.to_numeric(tr["shrs_ownd_folwng_trans"], errors="coerce"),
        "direct": tr["direct_indirect_ownership"],
        "aff10b5one": tr["aff10b5one"] if "aff10b5one" in tr else "",
        "owner_ciks": tr["owner_ciks"], "n_owners": tr["n_owners"],
        "is_director": tr["is_director"], "is_officer": tr["is_officer"],
        "is_ten_pct": tr["is_ten_pct"], "is_other": tr["is_other"],
        "officer_title": tr["officer_title"],
    })
    out["value"] = out["shares"] * out["price"]
    return out, symbols


def build(verbose: bool = True) -> None:
    trans, syms = [], []
    for zp in sorted((paths.SEC / "insider").glob("*_form345.zip")):
        t, s = parse_quarter(zp)
        trans.append(t)
        syms.append(s)
        if verbose:
            print(f"  {zp.stem}: {len(t):>7} P/S transactions, {len(s):>7} filings", flush=True)
    t = pd.concat(trans, ignore_index=True)
    s = pd.concat(syms, ignore_index=True).dropna(subset=["issuer_cik", "filing_date"])
    t.to_parquet(paths.BUILT / "insider_trans.parquet", index=False)
    s.to_parquet(paths.BUILT / "issuer_symbols.parquet", index=False)


def load_trans() -> pd.DataFrame:
    return pd.read_parquet(paths.BUILT / "insider_trans.parquet")


def load_symbols() -> pd.DataFrame:
    return pd.read_parquet(paths.BUILT / "issuer_symbols.parquet")
