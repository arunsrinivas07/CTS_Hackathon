"""
Dataset Profiling Script
Reads every CSV under data/raw/ (read-only) and produces a structured profile
saved to data/processed/reference/dataset_profile.csv.

Run from the project root:
    python scripts/profile_datasets.py
"""

import os
import re
import warnings
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")

# ── paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "data" / "processed" / "reference"
OUT_DIR.mkdir(parents=True, exist_ok=True)
PROFILE_PATH = OUT_DIR / "dataset_profile.csv"

# ── domain helpers ───────────────────────────────────────────────────────────

# Patterns that flag a column as a date field
DATE_PATTERNS = re.compile(r"(DT|DATE|_DT$|_DATE$)", re.IGNORECASE)

# Patterns for claim ID / beneficiary / provider
CLM_ID_PATTERNS   = re.compile(r"^CLM_ID$", re.IGNORECASE)
BENE_ID_PATTERNS  = re.compile(r"BENE_ID", re.IGNORECASE)
PRVDR_ID_PATTERNS = re.compile(r"(PRVDR_NUM|ORG_NPI_NUM|AT_PHYSN_NPI|RNDRNG_PHYSN_NPI|PRSCRBR_ID)", re.IGNORECASE)
PAYMENT_PATTERNS  = re.compile(r"(PMT_AMT|PD_AMT|CVRD.*AMT|PTNT_PAY|PLRO_AMT|LICS_AMT)", re.IGNORECASE)
CHARGE_PATTERNS   = re.compile(r"(CHRG_AMT|TOT_RX_CST_AMT)", re.IGNORECASE)
DIAG_PATTERNS     = re.compile(r"(ICD_DGNS|PRNCPAL_DGNS|FST_DGNS)", re.IGNORECASE)
PROC_PATTERNS     = re.compile(r"(ICD_PRCDR|HCPCS_CD)", re.IGNORECASE)

# PDE-specific
PDE_DRUG_PATTERNS = re.compile(r"(PROD_SRVC_ID|BRND_GNRC_CD|CMPND_CD|DAW_PROD_SLCTN_CD|QTY_DSPNSD_NUM|DAYS_SUPLY_NUM)", re.IGNORECASE)
PDE_COST_PATTERNS = re.compile(r"(GDC_BLW|GDC_ABV|PTNT_PAY|OTHR_TROOP|LICS_AMT|PLRO_AMT|CVRD_D_PLAN|NCVRD_PLAN|TOT_RX_CST)", re.IGNORECASE)

CLAIM_FILES = {"carrier", "dme", "hha", "hospice", "inpatient", "outpatient", "snf"}
PDE_FILES   = {"pde"}


# ── utility helpers ──────────────────────────────────────────────────────────

def _col_list(df: pd.DataFrame, pattern: re.Pattern) -> str:
    """Return a comma-separated list of columns matching pattern."""
    return ", ".join(c for c in df.columns if pattern.search(c))


def _parse_dates(series: pd.Series) -> pd.Series:
    """Try to coerce a series to datetime (various formats)."""
    for fmt in ("%d-%b-%Y", "%Y%m%d", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            parsed = pd.to_datetime(series, format=fmt, errors="coerce")
            if parsed.notna().sum() > 0:
                return parsed
        except Exception:
            pass
    return pd.to_datetime(series, infer_datetime_format=True, errors="coerce")


def _numeric_stats(df: pd.DataFrame, col: str) -> dict:
    """Return min/max for numeric-looking columns."""
    try:
        s = pd.to_numeric(df[col], errors="coerce")
        return {"numeric_min": s.min(), "numeric_max": s.max()}
    except Exception:
        return {"numeric_min": None, "numeric_max": None}


def _date_range(df: pd.DataFrame, col: str) -> dict:
    """Return min/max date for date-looking columns."""
    try:
        s = _parse_dates(df[col])
        return {"date_min": s.min(), "date_max": s.max()}
    except Exception:
        return {"date_min": None, "date_max": None}


# ── per-file profiling ────────────────────────────────────────────────────────

def profile_file(filepath: Path) -> list[dict]:
    """
    Read one CSV file and return a list of per-column profile records
    plus one file-level summary record.
    """
    stem = filepath.stem.lower()
    category = filepath.parent.name  # beneficiary | claims | pde | leie
    print(f"  profiling {filepath.relative_to(ROOT)} …")

    df = pd.read_csv(filepath, low_memory=False)

    n_rows = len(df)
    n_cols = len(df.columns)
    n_dupes = int(df.duplicated().sum())

    records: list[dict] = []

    # ── file-level record ─────────────────────────────────────────────────
    file_rec: dict[str, Any] = {
        "file":           filepath.name,
        "category":       category,
        "level":          "file",
        "column":         "__FILE__",
        "row_count":      n_rows,
        "col_count":      n_cols,
        "duplicate_rows": n_dupes,
        "dtype":          None,
        "missing_pct":    None,
        "unique_count":   None,
        "numeric_min":    None,
        "numeric_max":    None,
        "date_min":       None,
        "date_max":       None,
    }

    # ── claim-file extras ──────────────────────────────────────────────────
    if stem in CLAIM_FILES:
        clm_id_cols  = _col_list(df, CLM_ID_PATTERNS)
        bene_cols    = _col_list(df, BENE_ID_PATTERNS)
        prvdr_cols   = _col_list(df, PRVDR_ID_PATTERNS)
        payment_cols = _col_list(df, PAYMENT_PATTERNS)
        charge_cols  = _col_list(df, CHARGE_PATTERNS)
        diag_cols    = _col_list(df, DIAG_PATTERNS)
        proc_cols    = _col_list(df, PROC_PATTERNS)

        # Claim-ID uniqueness
        if clm_id_cols:
            first_id_col = clm_id_cols.split(",")[0].strip()
            clm_unique = int(df[first_id_col].nunique())
            file_rec["claim_id_cols"]    = clm_id_cols
            file_rec["claim_id_unique"]  = clm_unique
            file_rec["claim_id_is_pk"]   = (clm_unique == n_rows)
        else:
            file_rec["claim_id_cols"]   = ""
            file_rec["claim_id_unique"] = None
            file_rec["claim_id_is_pk"]  = None

        file_rec["bene_id_cols"]    = bene_cols
        file_rec["provider_id_cols"] = prvdr_cols
        file_rec["payment_cols"]    = payment_cols
        file_rec["charge_cols"]     = charge_cols
        file_rec["diagnosis_cols"]  = diag_cols
        file_rec["procedure_cols"]  = proc_cols

    # ── PDE extras ────────────────────────────────────────────────────────
    if stem in PDE_FILES:
        file_rec["pde_id_present"]    = "PDE_ID"    in df.columns
        file_rec["bene_id_present"]   = "BENE_ID"   in df.columns
        file_rec["prscrbr_id_present"]= "PRSCRBR_ID" in df.columns
        file_rec["srvc_dt_present"]   = "SRVC_DT"   in df.columns
        file_rec["drug_cols"]         = _col_list(df, PDE_DRUG_PATTERNS)
        file_rec["cost_cols"]         = _col_list(df, PDE_COST_PATTERNS)

    records.append(file_rec)

    # ── per-column records ────────────────────────────────────────────────
    for col in df.columns:
        series = df[col]
        dtype  = str(series.dtype)
        n_missing = int(series.isna().sum())
        missing_pct = round(n_missing / n_rows * 100, 2) if n_rows > 0 else None
        unique_cnt  = int(series.nunique(dropna=True))

        col_rec: dict[str, Any] = {
            "file":           filepath.name,
            "category":       category,
            "level":          "column",
            "column":         col,
            "row_count":      n_rows,
            "col_count":      n_cols,
            "duplicate_rows": None,
            "dtype":          dtype,
            "missing_pct":    missing_pct,
            "unique_count":   unique_cnt,
            "numeric_min":    None,
            "numeric_max":    None,
            "date_min":       None,
            "date_max":       None,
        }

        # Numeric stats
        if dtype in ("int64", "float64", "int32", "float32") or dtype.startswith("int") or dtype.startswith("float"):
            stats = _numeric_stats(df, col)
            col_rec.update(stats)
        elif dtype == "object":
            # Try numeric coercion first, then date
            num = pd.to_numeric(series, errors="coerce")
            if num.notna().sum() / max(n_rows, 1) > 0.5:
                col_rec["numeric_min"] = num.min()
                col_rec["numeric_max"] = num.max()
            elif DATE_PATTERNS.search(col):
                dr = _date_range(df, col)
                col_rec.update(dr)

        records.append(col_rec)

    return records


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    all_records: list[dict] = []

    for subdir in sorted(RAW_DIR.iterdir()):
        if not subdir.is_dir():
            continue
        csv_files = sorted(subdir.glob("*.csv"))
        if not csv_files:
            continue
        print(f"\n[{subdir.name}]")
        for fp in csv_files:
            recs = profile_file(fp)
            all_records.extend(recs)

    profile_df = pd.DataFrame(all_records)

    # Reorder columns: metadata first, stats after, domain extras at end
    lead_cols = [
        "file", "category", "level", "column",
        "row_count", "col_count", "duplicate_rows",
        "dtype", "missing_pct", "unique_count",
        "numeric_min", "numeric_max", "date_min", "date_max",
    ]
    extra_cols = [c for c in profile_df.columns if c not in lead_cols]
    profile_df = profile_df[lead_cols + extra_cols]

    profile_df.to_csv(PROFILE_PATH, index=False)
    print(f"\n✓ Profile saved → {PROFILE_PATH.relative_to(ROOT)}")
    print(f"  {len(profile_df):,} rows  |  {len(profile_df.columns)} columns")


if __name__ == "__main__":
    main()
