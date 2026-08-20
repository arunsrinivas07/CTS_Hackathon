"""
Medical Claims Normalization Pipeline
======================================
Reads the seven raw claim CSVs (read-only), combines them into one normalized
table, and saves to data/processed/medical/claims_normalized.csv.

Normalized columns produced
----------------------------
SOURCE_FILE          - original filename (no extension)
CLAIM_TYPE           - human-readable label (inpatient / outpatient / carrier /
                       dme / hha / hospice / snf)
CLAIM_ID             - unified claim identifier
BENE_ID              - beneficiary identifier
PROVIDER_ID          - best-available rendering / organisation NPI or PRVDR_NUM
CLAIM_START_DATE     - parsed service-from date  (CLM_FROM_DT)
CLAIM_END_DATE       - parsed service-through date (CLM_THRU_DT)
YEAR                 - calendar year derived from CLAIM_START_DATE
CLAIM_DURATION_DAYS  - CLAIM_END_DATE minus CLAIM_START_DATE (integer, ≥0)
CLM_PMT_AMT          - claim payment amount (direct passthrough)
CLM_TOT_CHRG_AMT     - total charge amount  (direct passthrough; NaN if absent)
DIAG_COUNT           - count of non-null ICD_DGNS_CDn columns (excl. E-codes)
PROC_COUNT           - count of non-null ICD_PRCDR_CDn or HCPCS_CD columns
LINE_COUNT           - max LINE_NUM / CLM_LINE_NUM per claim row
UNIT_COUNT           - REV_CNTR_UNIT_CNT / LINE_SRVC_CNT where available
PRNCPAL_DGNS_CD      - principal diagnosis (passthrough)
AT_PHYSN_NPI         - attending physician NPI (passthrough; NaN if absent)
ORG_NPI_NUM          - organisation NPI (passthrough; NaN if absent)

All original source columns are PRESERVED in the output after the normalized
columns (prefixed with SRC__).  No values are invented; missing = NaN.

Run from the project root:
    python scripts/normalize_medical_claims.py
"""

import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── paths ─────────────────────────────────────────────────────────────────────
ROOT     = Path(__file__).resolve().parent.parent
CLAIMS   = ROOT / "data" / "raw" / "claims"
OUT_DIR  = ROOT / "data" / "processed" / "medical"
REF_DIR  = ROOT / "data" / "processed" / "reference"
OUT_DIR.mkdir(parents=True, exist_ok=True)
REF_DIR.mkdir(parents=True, exist_ok=True)

OUT_CSV     = OUT_DIR  / "claims_normalized.csv"
SCHEMA_PATH = REF_DIR  / "claims_schema_mapping.md"


# ── per-file column mapping config ────────────────────────────────────────────
# Keys are normalised column names; values are ordered candidate source columns.
# The first non-null match per row wins.  If none exist in a file the column is
# left as NaN.

FIELD_MAP: dict[str, list[str]] = {
    "CLAIM_ID":         ["CLM_ID"],
    "BENE_ID":          ["BENE_ID"],
    # Provider: prefer NPI, fall back to legacy PRVDR_NUM / TAX_NUM
    "PROVIDER_ID":      ["ORG_NPI_NUM", "AT_PHYSN_NPI", "PRF_PHYSN_NPI",
                         "RNDRNG_PHYSN_NPI", "PRVDR_NUM", "PRVDR_NPI",
                         "RFR_PHYSN_NPI"],
    "CLM_PMT_AMT":      ["CLM_PMT_AMT"],
    "CLM_TOT_CHRG_AMT": ["CLM_TOT_CHRG_AMT", "NCH_CARR_CLM_SBMTD_CHRG_AMT"],
    # Dates
    "CLAIM_START_DATE": ["CLM_FROM_DT"],
    "CLAIM_END_DATE":   ["CLM_THRU_DT"],
    # Line / unit counts (header-level; line files have one row per line)
    "LINE_COUNT":       ["CLM_LINE_NUM", "LINE_NUM"],
    "UNIT_COUNT":       ["REV_CNTR_UNIT_CNT", "LINE_SRVC_CNT",
                         "CARR_LINE_MTUS_CNT", "DMERC_LINE_MTUS_CNT"],
    # Pass-through informational columns
    "PRNCPAL_DGNS_CD":  ["PRNCPAL_DGNS_CD"],
    "AT_PHYSN_NPI":     ["AT_PHYSN_NPI"],
    "ORG_NPI_NUM":      ["ORG_NPI_NUM"],
}

# Regex patterns used to count populated fields
DIAG_RE = re.compile(r"^ICD_DGNS_CD\d+$", re.IGNORECASE)   # excludes E-codes
PROC_RE = re.compile(r"^ICD_PRCDR_CD\d+$", re.IGNORECASE)


# ── date parser ───────────────────────────────────────────────────────────────

def _parse_date_col(series: pd.Series) -> pd.Series:
    for fmt in ("%d-%b-%Y", "%Y%m%d", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            parsed = pd.to_datetime(series, format=fmt, errors="coerce")
            if parsed.notna().sum() > 0:
                return parsed
        except Exception:
            pass
    return pd.to_datetime(series, infer_datetime_format=True, errors="coerce")


# ── per-file normaliser ───────────────────────────────────────────────────────

def _coalesce(df: pd.DataFrame, candidates: list[str]) -> pd.Series:
    """Return first non-null value from candidate columns, in order."""
    result = pd.Series(np.nan, index=df.index, dtype=object)
    for col in candidates:
        if col in df.columns:
            result = result.where(result.notna(), df[col])
    return result


def normalise_file(filepath: Path) -> pd.DataFrame:
    stem = filepath.stem.lower()
    print(f"  reading {filepath.name} …", end="", flush=True)
    df = pd.read_csv(filepath, low_memory=False)
    print(f" {len(df):,} rows")

    # ── resolved normalised columns ──────────────────────────────────────
    out = pd.DataFrame(index=df.index)
    out["SOURCE_FILE"] = filepath.stem          # e.g. "inpatient"
    out["CLAIM_TYPE"]  = stem                   # same, lower-case

    for norm_col, candidates in FIELD_MAP.items():
        out[norm_col] = _coalesce(df, candidates)

    # ── date parsing & derived columns ───────────────────────────────────
    out["CLAIM_START_DATE"] = _parse_date_col(out["CLAIM_START_DATE"])
    out["CLAIM_END_DATE"]   = _parse_date_col(out["CLAIM_END_DATE"])

    out["YEAR"] = out["CLAIM_START_DATE"].dt.year.astype("Int64")

    duration = (out["CLAIM_END_DATE"] - out["CLAIM_START_DATE"]).dt.days
    out["CLAIM_DURATION_DAYS"] = duration.where(duration >= 0).astype("Int64")

    # ── diagnosis count ───────────────────────────────────────────────────
    diag_cols = [c for c in df.columns if DIAG_RE.match(c)]
    if diag_cols:
        out["DIAG_COUNT"] = df[diag_cols].notna().sum(axis=1).astype("Int64")
    else:
        out["DIAG_COUNT"] = pd.NA

    # ── procedure count ───────────────────────────────────────────────────
    proc_cols = [c for c in df.columns if PROC_RE.match(c)]
    hcpcs_present = "HCPCS_CD" in df.columns
    if proc_cols:
        pc = df[proc_cols].notna().sum(axis=1)
        if hcpcs_present:
            pc = pc + df["HCPCS_CD"].notna().astype(int)
        out["PROC_COUNT"] = pc.astype("Int64")
    elif hcpcs_present:
        out["PROC_COUNT"] = df["HCPCS_CD"].notna().astype("Int64")
    else:
        out["PROC_COUNT"] = pd.NA

    # ── numeric casts ─────────────────────────────────────────────────────
    for col in ["CLM_PMT_AMT", "CLM_TOT_CHRG_AMT", "LINE_COUNT", "UNIT_COUNT"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    # ── reorder normalised columns ────────────────────────────────────────
    norm_cols = [
        "SOURCE_FILE", "CLAIM_TYPE",
        "CLAIM_ID", "BENE_ID", "PROVIDER_ID",
        "CLAIM_START_DATE", "CLAIM_END_DATE", "YEAR", "CLAIM_DURATION_DAYS",
        "CLM_PMT_AMT", "CLM_TOT_CHRG_AMT",
        "DIAG_COUNT", "PROC_COUNT", "LINE_COUNT", "UNIT_COUNT",
        "PRNCPAL_DGNS_CD", "AT_PHYSN_NPI", "ORG_NPI_NUM",
    ]
    # Append original source columns with SRC__ prefix to preserve raw data
    src_renamed = df.rename(columns={c: f"SRC__{c}" for c in df.columns})
    result = pd.concat([out[norm_cols], src_renamed], axis=1)
    return result


# ── schema mapping document ───────────────────────────────────────────────────

SCHEMA_MD = """\
# Medical Claims Schema Mapping

Generated by `scripts/normalize_medical_claims.py`.  
Every normalized column and its source mapping per dataset.

---

## Normalized Columns

| Normalized Column | Description | inpatient | outpatient | carrier | dme | hha | hospice | snf |
|---|---|---|---|---|---|---|---|---|
| SOURCE_FILE | Original filename (no extension) | inpatient | outpatient | carrier | dme | hha | hospice | snf |
| CLAIM_TYPE | Human-readable claim category | inpatient | outpatient | carrier | dme | hha | hospice | snf |
| CLAIM_ID | Unique claim identifier | CLM_ID | CLM_ID | CLM_ID | CLM_ID | CLM_ID | CLM_ID | CLM_ID |
| BENE_ID | Beneficiary identifier | BENE_ID | BENE_ID | BENE_ID | BENE_ID | BENE_ID | BENE_ID | BENE_ID |
| PROVIDER_ID | Best-available provider identifier (NPI or legacy) | ORG_NPI_NUM → AT_PHYSN_NPI | ORG_NPI_NUM → AT_PHYSN_NPI | ORG_NPI_NUM → PRF_PHYSN_NPI → RFR_PHYSN_NPI | PRVDR_NUM → PRVDR_NPI | ORG_NPI_NUM → AT_PHYSN_NPI | ORG_NPI_NUM → AT_PHYSN_NPI | ORG_NPI_NUM → AT_PHYSN_NPI |
| CLAIM_START_DATE | Service start date (parsed to date) | CLM_FROM_DT | CLM_FROM_DT | CLM_FROM_DT | CLM_FROM_DT | CLM_FROM_DT | CLM_FROM_DT | CLM_FROM_DT |
| CLAIM_END_DATE | Service end date (parsed to date) | CLM_THRU_DT | CLM_THRU_DT | CLM_THRU_DT | CLM_THRU_DT | CLM_THRU_DT | CLM_THRU_DT | CLM_THRU_DT |
| YEAR | Calendar year derived from CLAIM_START_DATE | derived | derived | derived | derived | derived | derived | derived |
| CLAIM_DURATION_DAYS | CLAIM_END_DATE − CLAIM_START_DATE in days (≥0, else NaN) | derived | derived | derived | derived | derived | derived | derived |
| CLM_PMT_AMT | Medicare claim payment amount | CLM_PMT_AMT | CLM_PMT_AMT | CLM_PMT_AMT | CLM_PMT_AMT | CLM_PMT_AMT | CLM_PMT_AMT | CLM_PMT_AMT |
| CLM_TOT_CHRG_AMT | Total submitted charge amount | CLM_TOT_CHRG_AMT | CLM_TOT_CHRG_AMT | NCH_CARR_CLM_SBMTD_CHRG_AMT | NCH_CARR_CLM_SBMTD_CHRG_AMT | CLM_TOT_CHRG_AMT | CLM_TOT_CHRG_AMT | CLM_TOT_CHRG_AMT |
| DIAG_COUNT | Count of non-null ICD_DGNS_CDn fields (excludes E-codes) | ICD_DGNS_CD1–25 | ICD_DGNS_CD1–25 | ICD_DGNS_CD1–12 | ICD_DGNS_CD1–12 | ICD_DGNS_CD1–25 | ICD_DGNS_CD1–25 | ICD_DGNS_CD1–25 |
| PROC_COUNT | Count of non-null ICD_PRCDR_CDn + HCPCS_CD fields | ICD_PRCDR_CD1–25 + HCPCS_CD | ICD_PRCDR_CD1–25 + HCPCS_CD | HCPCS_CD only | HCPCS_CD only | HCPCS_CD only | HCPCS_CD only | ICD_PRCDR_CD1–25 + HCPCS_CD |
| LINE_COUNT | Line number (header-level; may vary per row in line-level files) | CLM_LINE_NUM | CLM_LINE_NUM | LINE_NUM | LINE_NUM | CLM_LINE_NUM | CLM_LINE_NUM | CLM_LINE_NUM |
| UNIT_COUNT | Service unit count | REV_CNTR_UNIT_CNT | REV_CNTR_UNIT_CNT | LINE_SRVC_CNT → CARR_LINE_MTUS_CNT | LINE_SRVC_CNT → DMERC_LINE_MTUS_CNT | REV_CNTR_UNIT_CNT | REV_CNTR_UNIT_CNT | REV_CNTR_UNIT_CNT |
| PRNCPAL_DGNS_CD | Principal diagnosis code (passthrough) | PRNCPAL_DGNS_CD | PRNCPAL_DGNS_CD | PRNCPAL_DGNS_CD | PRNCPAL_DGNS_CD | PRNCPAL_DGNS_CD | PRNCPAL_DGNS_CD | PRNCPAL_DGNS_CD |
| AT_PHYSN_NPI | Attending physician NPI (passthrough; NaN if absent) | AT_PHYSN_NPI | AT_PHYSN_NPI | NaN | NaN | AT_PHYSN_NPI | AT_PHYSN_NPI | AT_PHYSN_NPI |
| ORG_NPI_NUM | Organisation / facility NPI (passthrough; NaN if absent) | ORG_NPI_NUM | ORG_NPI_NUM | ORG_NPI_NUM | NaN | ORG_NPI_NUM | ORG_NPI_NUM | ORG_NPI_NUM |

---

## Source Preservation

All original source columns are appended to the output with a `SRC__` prefix  
(e.g. `SRC__CLM_FROM_DT`, `SRC__ICD_DGNS_CD1`).  
No raw values are modified or deleted.

---

## Notes

- **PROVIDER_ID** uses coalesce priority: first non-null wins across the  
  candidate list shown per dataset column above.
- **CLM_TOT_CHRG_AMT** for carrier/dme is sourced from  
  `NCH_CARR_CLM_SBMTD_CHRG_AMT` (the closest equivalent submitted-charge field).
- **DIAG_COUNT** counts only `ICD_DGNS_CDn` columns (not E-code columns  
  `ICD_DGNS_E_CDn`) to remain consistent with how principal diagnosis slots  
  are defined across claim types.
- **PROC_COUNT** includes HCPCS_CD where present; for carrier/dme/hha/hospice  
  there are no ICD_PRCDR columns so the count reflects HCPCS_CD only.
- **CLAIM_DURATION_DAYS** is set to NaN when the end date precedes the start  
  date (data quality issue in source).
- Dates are parsed from `dd-Mon-YYYY` format (e.g. `16-Mar-2015`) as used in  
  the source files; fallback formats `YYYYMMDD`, `MM/DD/YYYY`, `YYYY-MM-DD`  
  are also tried.
"""


# ── main ──────────────────────────────────────────────────────────────────────

FILES = ["inpatient", "outpatient", "carrier", "dme", "hha", "hospice", "snf"]

def main():
    frames = []
    for name in FILES:
        fp = CLAIMS / f"{name}.csv"
        frames.append(normalise_file(fp))

    print("\nCombining …")
    combined = pd.concat(frames, ignore_index=True, sort=False)

    # Ensure date columns output as ISO strings, not numpy datetime objects
    for col in ("CLAIM_START_DATE", "CLAIM_END_DATE"):
        combined[col] = combined[col].dt.strftime("%Y-%m-%d")

    print(f"Writing {len(combined):,} rows × {len(combined.columns)} columns …")
    combined.to_csv(OUT_CSV, index=False)
    print(f"✓ Saved → {OUT_CSV.relative_to(ROOT)}")

    # Schema mapping document
    SCHEMA_PATH.write_text(SCHEMA_MD, encoding="utf-8")
    print(f"✓ Schema mapping saved → {SCHEMA_PATH.relative_to(ROOT)}")

    # Quick sanity summary
    print("\n── Summary ──────────────────────────────────────────────────────")
    summary = (
        combined.groupby("CLAIM_TYPE")
        .agg(
            rows=("CLAIM_ID", "count"),
            unique_claims=("CLAIM_ID", "nunique"),
            unique_benes=("BENE_ID",  "nunique"),
            year_min=("YEAR", "min"),
            year_max=("YEAR", "max"),
            avg_payment=("CLM_PMT_AMT", "mean"),
            avg_charge=("CLM_TOT_CHRG_AMT", "mean"),
        )
        .reset_index()
    )
    print(summary.to_string(index=False))
    print("─────────────────────────────────────────────────────────────────")


if __name__ == "__main__":
    main()
