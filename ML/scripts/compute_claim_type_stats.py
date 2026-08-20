"""
Claim-Type Peer Statistics
===========================
Computes robust reference statistics for each CLAIM_TYPE using the
TRAINING period only (years 2015–2022).  2023 is held out as the test
period and is never touched here.

For every CLAIM_TYPE × metric combination the output contains:
  - n               : count of non-null observations
  - median          : 50th percentile (robust central tendency)
  - mad             : median absolute deviation (robust spread)
  - robust_z_ref    : {"median": m, "mad": s} for computing
                      robust Z = (x - median) / (1.4826 * MAD)
  - percentiles     : p1 / p5 / p10 / p25 / p50 / p75 / p90 / p95 / p99
  - iqr             : p75 - p25

Metrics computed per claim type:
  - clm_pmt_amt         : claim payment amount
  - clm_tot_chrg_amt    : total charge amount
  - claim_duration_days : service duration
  - line_count          : revenue / line count
  - unit_count          : service units
  - diag_count          : number of diagnoses
  - proc_count          : number of procedures
  - hcpcs_unique_cnt    : unique HCPCS codes per claim (where available)

HCPCS unique count is derived from the raw normalized claims file
(SRC__HCPCS_CD column) grouped per CLAIM_ID, then merged into the
training set.  inpatient and outpatient have one HCPCS per line so the
unique count per claim is computed from the line-level rows.

Training cutoff: YEAR <= 2022
Test / holdout : YEAR == 2023  (never used here)

Outputs
-------
data/processed/reference/medical_claim_type_stats.json

Run from the project root:
    python scripts/compute_claim_type_stats.py
"""

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── configuration ─────────────────────────────────────────────────────────────
ROOT         = Path(__file__).resolve().parent.parent
HISTORY_CSV  = ROOT / "data" / "processed" / "medical" / "claims_with_beneficiary_history.csv"
NORM_CSV     = ROOT / "data" / "processed" / "medical" / "claims_normalized.csv"
OUT_DIR      = ROOT / "data" / "processed" / "reference"
OUT_JSON     = OUT_DIR / "medical_claim_type_stats.json"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TRAIN_MAX_YEAR = 2022   # inclusive — 2023 is the test holdout

METRIC_COLS = {
    "clm_pmt_amt":          "CLM_PMT_AMT",
    "clm_tot_chrg_amt":     "CLM_TOT_CHRG_AMT",
    "claim_duration_days":  "CLAIM_DURATION_DAYS",
    "line_count":           "LINE_COUNT",
    "unit_count":           "UNIT_COUNT",
    "diag_count":           "DIAG_COUNT",
    "proc_count":           "PROC_COUNT",
}

PERCENTILE_POINTS = [1, 5, 10, 25, 50, 75, 90, 95, 99]

# Normalisation constant for MAD → consistent std estimator under normality
_C = 1.4826


# ── helpers ───────────────────────────────────────────────────────────────────

def _robust_stats(series: pd.Series, label: str) -> dict:
    """Return median, MAD, percentiles, IQR, and robust-Z reference for a series."""
    s = pd.to_numeric(series, errors="coerce").dropna()
    n = len(s)

    if n == 0:
        return {
            "metric":    label,
            "n":         0,
            "median":    None,
            "mad":       None,
            "mad_scaled": None,
            "robust_z_ref": {"median": None, "mad_scaled": None,
                              "note": "robust Z = (x - median) / mad_scaled"},
            "percentiles": {f"p{p}": None for p in PERCENTILE_POINTS},
            "iqr":       None,
            "mean":      None,
            "std":       None,
        }

    med  = float(np.median(s))
    mad  = float(np.median(np.abs(s - med)))
    mad_scaled = float(mad * _C)   # consistent estimator of std

    pcts = {
        f"p{p}": float(np.percentile(s, p))
        for p in PERCENTILE_POINTS
    }
    iqr  = pcts["p75"] - pcts["p25"]

    return {
        "metric":       label,
        "n":            int(n),
        "median":       round(med, 4),
        "mad":          round(mad, 4),
        "mad_scaled":   round(mad_scaled, 4),
        "robust_z_ref": {
            "median":     round(med, 4),
            "mad_scaled": round(mad_scaled, 4),
            "note": "robust Z-score = (x - median) / mad_scaled",
        },
        "percentiles":  {k: round(v, 4) for k, v in pcts.items()},
        "iqr":          round(iqr, 4),
        "mean":         round(float(s.mean()), 4),
        "std":          round(float(s.std(ddof=1)), 4),
    }


def _hcpcs_unique_per_claim(norm_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute the number of unique HCPCS codes per CLAIM_ID from the
    normalized (line-level) claims table.
    Returns a DataFrame with columns [CLAIM_ID, CLAIM_TYPE, YEAR, hcpcs_unique_cnt].
    """
    tmp = norm_df[["CLAIM_ID", "CLAIM_TYPE", "YEAR", "SRC__HCPCS_CD"]].copy()
    tmp = tmp[tmp["SRC__HCPCS_CD"].notna()]
    hcpcs_cnt = (
        tmp.groupby(["CLAIM_ID", "CLAIM_TYPE", "YEAR"])["SRC__HCPCS_CD"]
        .nunique()
        .reset_index()
        .rename(columns={"SRC__HCPCS_CD": "hcpcs_unique_cnt"})
    )
    return hcpcs_cnt


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    # ── 1. Load training data (history file, exclude test year) ──────────
    print("Loading training claims (YEAR <= 2022) …")
    train = pd.read_csv(
        HISTORY_CSV,
        usecols=["CLAIM_ID", "CLAIM_TYPE", "YEAR",
                 "CLM_PMT_AMT", "CLM_TOT_CHRG_AMT", "CLAIM_DURATION_DAYS",
                 "LINE_COUNT", "UNIT_COUNT", "DIAG_COUNT", "PROC_COUNT"],
        low_memory=False,
    )
    before = len(train)
    train  = train[train["YEAR"] <= TRAIN_MAX_YEAR].reset_index(drop=True)
    print(f"  {before:,} total rows → {len(train):,} training rows "
          f"(dropped {before - len(train):,} test rows, YEAR > {TRAIN_MAX_YEAR})")

    # ── 2. Build HCPCS unique count from normalized file (training only) ─
    print("Loading HCPCS data from normalized claims …")
    norm = pd.read_csv(
        NORM_CSV,
        usecols=["CLAIM_ID", "CLAIM_TYPE", "YEAR", "SRC__HCPCS_CD"],
        low_memory=False,
    )
    norm_train = norm[norm["YEAR"] <= TRAIN_MAX_YEAR].copy()
    hcpcs_df   = _hcpcs_unique_per_claim(norm_train)
    print(f"  HCPCS unique counts computed for {len(hcpcs_df):,} claims")

    # Merge into training set
    train = train.merge(hcpcs_df[["CLAIM_ID", "hcpcs_unique_cnt"]],
                        on="CLAIM_ID", how="left")
    print(f"  HCPCS null after merge: "
          f"{train['hcpcs_unique_cnt'].isna().mean()*100:.1f}% of rows "
          f"(expected for claim types without HCPCS)")

    # ── 3. Compute stats per CLAIM_TYPE ──────────────────────────────────
    print("\nComputing robust statistics …")

    output: dict = {
        "_metadata": {
            "description":       "Claim-type peer statistics computed from training data only",
            "training_period":   f"2015 – {TRAIN_MAX_YEAR}",
            "test_holdout":      "2023 (excluded from all statistics)",
            "train_rows":        int(len(train)),
            "mad_scale_constant": _C,
            "robust_z_formula":  "robust_z = (x - median) / (MAD * 1.4826)",
            "percentile_points": PERCENTILE_POINTS,
            "source_files": {
                "claims_history": str(HISTORY_CSV.relative_to(ROOT)),
                "claims_normalized": str(NORM_CSV.relative_to(ROOT)),
            },
        }
    }

    all_metrics = list(METRIC_COLS.items()) + [("hcpcs_unique_cnt", "hcpcs_unique_cnt")]

    claim_types = sorted(train["CLAIM_TYPE"].unique())
    for ct in claim_types:
        ct_df = train[train["CLAIM_TYPE"] == ct]
        n_claims = int(ct_df["CLAIM_ID"].nunique())
        n_rows   = int(len(ct_df))
        print(f"  {ct:<12s} : {n_rows:>8,} rows | {n_claims:>7,} unique claims")

        ct_stats: dict = {
            "_claim_type_summary": {
                "claim_type":   ct,
                "train_rows":   n_rows,
                "unique_claims": n_claims,
                "year_range":   [int(ct_df["YEAR"].min()), int(ct_df["YEAR"].max())],
            }
        }

        for metric_key, col_name in all_metrics:
            if col_name in ct_df.columns:
                ct_stats[metric_key] = _robust_stats(ct_df[col_name], metric_key)
            else:
                ct_stats[metric_key] = {
                    "metric": metric_key, "n": 0,
                    "note": f"Column {col_name} not available for {ct}",
                }

        output[ct] = ct_stats

    # ── 4. Save JSON ──────────────────────────────────────────────────────
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\n✓ Saved → {OUT_JSON.relative_to(ROOT)}")

    # ── 5. Print summary table ────────────────────────────────────────────
    print("\n── Peer Stats Summary (median | MAD) ────────────────────────────")
    header = f"{'claim_type':<12}  {'payment':>12}  {'charge':>12}  "
    header += f"{'duration':>10}  {'lines':>8}  {'diags':>8}  {'procs':>8}  {'hcpcs_uniq':>11}"
    print(header)
    print("-" * len(header))
    for ct in claim_types:
        def _fmt(key):
            s = output[ct].get(key, {})
            m = s.get("median")
            d = s.get("mad")
            if m is None:
                return f"{'N/A':>12}"
            return f"{m:>8.1f}|{d:<5.1f}" if d is not None else f"{m:>12.1f}"

        row = (
            f"{ct:<12}  "
            f"{_fmt('clm_pmt_amt'):>12}  "
            f"{_fmt('clm_tot_chrg_amt'):>12}  "
            f"{_fmt('claim_duration_days'):>10}  "
            f"{_fmt('line_count'):>8}  "
            f"{_fmt('diag_count'):>8}  "
            f"{_fmt('proc_count'):>8}  "
            f"{_fmt('hcpcs_unique_cnt'):>11}"
        )
        print(row)
    print("─────────────────────────────────────────────────────────────────")
    print("Format: median | MAD")


if __name__ == "__main__":
    main()
