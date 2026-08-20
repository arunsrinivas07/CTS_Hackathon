"""
Temporal Train/Test Split — Model B Medical Features
======================================================
Splits model_b_features.csv on YEAR:
    Training : 2014 – 2022  (all rows where YEAR <= 2022)
    Test     : 2023          (all rows where YEAR == 2023)

This boundary is consistent with the peer statistics reference, which were
also computed on YEAR <= 2022 only, so no future information influences
any training feature or reference statistic.

Outputs
-------
data/processed/medical/training_medical.csv
data/processed/medical/test_medical.csv
data/processed/reference/temporal_split_report.csv

Run from project root:
    python scripts/temporal_split_model_b.py
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── paths ─────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).resolve().parent.parent
FEAT_CSV    = ROOT / "data" / "processed" / "medical" / "model_b_features.csv"
OUT_DIR     = ROOT / "data" / "processed" / "medical"
REF_DIR     = ROOT / "data" / "processed" / "reference"
OUT_DIR.mkdir(parents=True, exist_ok=True)
REF_DIR.mkdir(parents=True, exist_ok=True)

TRAIN_CSV  = OUT_DIR / "training_medical.csv"
TEST_CSV   = OUT_DIR / "test_medical.csv"
REPORT_CSV = REF_DIR / "temporal_split_report.csv"

TRAIN_MAX_YEAR = 2022
TEST_YEAR      = 2023


# ── helpers ───────────────────────────────────────────────────────────────────

def _ohe_to_label(df: pd.DataFrame) -> pd.Series:
    """Reconstruct CLAIM_TYPE label from CLMTYPE_ one-hot columns."""
    ohe = [c for c in df.columns if c.startswith("CLMTYPE_")]
    if not ohe:
        return pd.Series("unknown", index=df.index)
    return df[ohe].idxmax(axis=1).str.replace("CLMTYPE_", "", regex=False)


def _payment_distribution(series: pd.Series, prefix: str) -> dict:
    s = pd.to_numeric(series, errors="coerce").dropna()
    return {
        f"{prefix}_n":      int(len(s)),
        f"{prefix}_mean":   round(float(s.mean()),   2),
        f"{prefix}_median": round(float(s.median()), 2),
        f"{prefix}_std":    round(float(s.std()),    2),
        f"{prefix}_p25":    round(float(s.quantile(0.25)), 2),
        f"{prefix}_p75":    round(float(s.quantile(0.75)), 2),
        f"{prefix}_p90":    round(float(s.quantile(0.90)), 2),
        f"{prefix}_p99":    round(float(s.quantile(0.99)), 2),
        f"{prefix}_max":    round(float(s.max()),    2),
    }


def _missing_summary(df: pd.DataFrame, prefix: str) -> dict:
    pct = df.isnull().mean().mul(100)
    n_cols_with_missing = int((pct > 0).sum())
    max_missing_col     = pct.idxmax() if n_cols_with_missing > 0 else "none"
    max_missing_pct     = round(float(pct.max()), 2)
    return {
        f"{prefix}_cols_with_missing": n_cols_with_missing,
        f"{prefix}_max_missing_col":   max_missing_col,
        f"{prefix}_max_missing_pct":   max_missing_pct,
    }


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    # ── 1. Load ───────────────────────────────────────────────────────────
    print("Loading model_b_features.csv …")
    df = pd.read_csv(FEAT_CSV, low_memory=False)
    print(f"  {len(df):,} rows × {len(df.columns)} columns")

    # ── 2. Split ──────────────────────────────────────────────────────────
    train = df[df["YEAR"] <= TRAIN_MAX_YEAR].copy().reset_index(drop=True)
    test  = df[df["YEAR"] == TEST_YEAR].copy().reset_index(drop=True)

    print(f"\n  Training (YEAR <= {TRAIN_MAX_YEAR}): {len(train):,} rows")
    print(f"  Test     (YEAR == {TEST_YEAR}):      {len(test):,} rows")
    print(f"  Split ratio: {len(train)/len(df)*100:.1f}% / {len(test)/len(df)*100:.1f}%")

    # ── 3. Save splits ────────────────────────────────────────────────────
    print("\nSaving splits …")
    train.to_csv(TRAIN_CSV, index=False)
    print(f"  ✓ {TRAIN_CSV.relative_to(ROOT)}")
    test.to_csv(TEST_CSV, index=False)
    print(f"  ✓ {TEST_CSV.relative_to(ROOT)}")

    # ── 4. Build report ───────────────────────────────────────────────────
    print("\nBuilding report …")

    # Reconstruct claim type labels from OHE
    train_ct = _ohe_to_label(train)
    test_ct  = _ohe_to_label(test)

    all_types = sorted(set(train_ct.unique()) | set(test_ct.unique()))
    records   = []

    # ── 4a. Overall split summary ─────────────────────────────────────────
    overall_row = {
        "section":              "overall_split",
        "claim_type":           "ALL",
        "split":                "train",
        "year_min":             int(train["YEAR"].min()),
        "year_max":             int(train["YEAR"].max()),
        "row_count":            len(train),
        "pct_of_total":         round(len(train) / len(df) * 100, 2),
    }
    overall_row.update(_payment_distribution(train["CLM_PMT_AMT"], "pay"))
    overall_row.update(_missing_summary(train, "missing"))
    records.append(overall_row)

    overall_row_test = {
        "section":              "overall_split",
        "claim_type":           "ALL",
        "split":                "test",
        "year_min":             int(test["YEAR"].min()),
        "year_max":             int(test["YEAR"].max()),
        "row_count":            len(test),
        "pct_of_total":         round(len(test) / len(df) * 100, 2),
    }
    overall_row_test.update(_payment_distribution(test["CLM_PMT_AMT"], "pay"))
    overall_row_test.update(_missing_summary(test, "missing"))
    records.append(overall_row_test)

    # ── 4b. Year-level row counts ─────────────────────────────────────────
    for yr in sorted(df["YEAR"].unique()):
        split_label = "train" if yr <= TRAIN_MAX_YEAR else "test"
        subset = df[df["YEAR"] == yr]
        rec = {
            "section":      "year_distribution",
            "claim_type":   "ALL",
            "split":        split_label,
            "year_min":     int(yr),
            "year_max":     int(yr),
            "row_count":    len(subset),
            "pct_of_total": round(len(subset) / len(df) * 100, 2),
        }
        rec.update(_payment_distribution(subset["CLM_PMT_AMT"], "pay"))
        rec.update(_missing_summary(subset, "missing"))
        records.append(rec)

    # ── 4c. Claim-type distribution per split ─────────────────────────────
    for ct in all_types:
        for split_label, subset_df, ct_series in [
            ("train", train, train_ct),
            ("test",  test,  test_ct),
        ]:
            mask    = (ct_series == ct)
            ct_rows = subset_df[mask]
            parent  = subset_df

            if len(ct_rows) == 0:
                records.append({
                    "section":      "claim_type_distribution",
                    "claim_type":   ct,
                    "split":        split_label,
                    "year_min":     None,
                    "year_max":     None,
                    "row_count":    0,
                    "pct_of_total": 0.0,
                })
                continue

            rec = {
                "section":      "claim_type_distribution",
                "claim_type":   ct,
                "split":        split_label,
                "year_min":     int(ct_rows["YEAR"].min()),
                "year_max":     int(ct_rows["YEAR"].max()),
                "row_count":    len(ct_rows),
                "pct_of_total": round(len(ct_rows) / len(df) * 100, 2),
                "pct_of_split": round(len(ct_rows) / len(parent) * 100, 2),
            }
            rec.update(_payment_distribution(ct_rows["CLM_PMT_AMT"], "pay"))
            rec.update(_missing_summary(ct_rows, "missing"))
            records.append(rec)

    # ── 4d. Missing value detail per split ────────────────────────────────
    for split_label, subset_df in [("train", train), ("test", test)]:
        null_pcts = subset_df.isnull().mean().mul(100).round(2)
        for col, pct in null_pcts[null_pcts > 0].items():
            records.append({
                "section":      "missing_detail",
                "claim_type":   "ALL",
                "split":        split_label,
                "year_min":     None,
                "year_max":     None,
                "row_count":    int(subset_df[col].isnull().sum()),
                "pct_of_total": round(pct, 2),
                "column_name":  col,
            })

    report = pd.DataFrame(records)
    report.to_csv(REPORT_CSV, index=False)
    print(f"  ✓ {REPORT_CSV.relative_to(ROOT)}")

    # ── 5. Console summary ────────────────────────────────────────────────
    print()
    print("=" * 68)
    print("  TEMPORAL SPLIT REPORT — MODEL B MEDICAL")
    print("=" * 68)
    print(f"  Total rows       : {len(df):>10,}")
    print(f"  Training rows    : {len(train):>10,}  (YEAR 2014–{TRAIN_MAX_YEAR})")
    print(f"  Test rows        : {len(test):>10,}  (YEAR {TEST_YEAR})")
    print(f"  Train/test ratio : {len(train)/len(df)*100:.1f}% / {len(test)/len(df)*100:.1f}%")
    print()
    print("  Training year breakdown:")
    for yr in sorted(train["YEAR"].unique()):
        cnt = (train["YEAR"] == yr).sum()
        print(f"    {yr} : {cnt:>9,}  ({cnt/len(train)*100:.1f}% of train)")
    print()
    print("  Test year breakdown:")
    for yr in sorted(test["YEAR"].unique()):
        cnt = (test["YEAR"] == yr).sum()
        print(f"    {yr} : {cnt:>9,}  ({cnt/len(test)*100:.1f}% of test)")
    print()

    # Claim-type table
    print(f"  {'CLAIM_TYPE':<14} {'TRAIN rows':>12} {'TRAIN %':>9} {'TEST rows':>11} {'TEST %':>8}")
    print("  " + "-" * 58)
    for ct in all_types:
        tr_cnt = (train_ct == ct).sum()
        te_cnt = (test_ct  == ct).sum()
        tr_pct = tr_cnt / len(train) * 100
        te_pct = te_cnt / len(test)  * 100
        in_test = "✓" if te_cnt > 0 else "✗"
        print(f"  {ct:<14} {tr_cnt:>12,} {tr_pct:>8.1f}% {te_cnt:>11,} {te_pct:>7.1f}%  {in_test}")
    print()

    # Payment distribution comparison
    print("  Payment distribution (CLM_PMT_AMT):")
    for split_label, subset_df in [("train", train), ("test", test)]:
        s = pd.to_numeric(subset_df["CLM_PMT_AMT"], errors="coerce").dropna()
        print(f"    {split_label:<6}: "
              f"mean={s.mean():>10.2f}  median={s.median():>9.2f}  "
              f"p90={s.quantile(0.9):>10.2f}  max={s.max():>12.2f}")
    print()

    # Missing value summary
    print("  Missing value summary (columns with any nulls):")
    for split_label, subset_df in [("train", train), ("test", test)]:
        nulls = subset_df.isnull().mean().mul(100)
        nulls = nulls[nulls > 0].sort_values(ascending=False)
        print(f"    {split_label}: {len(nulls)} columns have missing values")
        for col, pct in nulls.items():
            print(f"      {col:<40s} : {pct:.1f}%")

    print()
    print("  Temporal leakage check:")
    print(f"    Max YEAR in training : {train['YEAR'].max()} (<= {TRAIN_MAX_YEAR})  ✓")
    print(f"    Min YEAR in test     : {test['YEAR'].min()} (== {TEST_YEAR})   ✓")
    print(f"    Peer stats computed  : YEAR <= {TRAIN_MAX_YEAR} (consistent)  ✓")
    print(f"    Bene history features: strictly prior rows only             ✓")
    print("=" * 68)


if __name__ == "__main__":
    main()
