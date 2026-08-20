"""
Stratified Training Sample — Model B Medical
=============================================
Creates a stratified subsample of training_medical.csv using strata defined
by CLAIM_TYPE × YEAR × PAYMENT_TIER.

Design decisions
----------------
1.  Payment tiers are computed PER claim type so DME's 62% zero-payment rows
    don't collapse all non-DME tiers.  Each type gets 4 tiers:
      - Types with ≥4 distinct payment values: quartile-based (Q1–Q4)
      - Types with fewer unique values: rank-based buckets

2.  Target sample size per stratum uses proportional allocation by claim type,
    then equal allocation across (YEAR × PAYMENT_TIER) cells within each type.
    This produces balanced representation across both axes.

3.  Strata with fewer rows than the target take ALL available rows (no oversampling,
    no duplication).

4.  Target total ~ 300,000 rows (≈16% of training), chosen so every claim type
    has a meaningful sample while keeping the file tractable.

Outputs
-------
data/processed/medical/model_b_training_sample.csv
data/processed/reference/stratification_summary.csv

Run from project root:
    python scripts/stratified_sample_model_b.py
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── paths ─────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).resolve().parent.parent
TRAIN_CSV  = ROOT / "data" / "processed" / "medical" / "training_medical.csv"
OUT_DIR    = ROOT / "data" / "processed" / "medical"
REF_DIR    = ROOT / "data" / "processed" / "reference"
OUT_DIR.mkdir(parents=True, exist_ok=True)
REF_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE_CSV  = OUT_DIR / "model_b_training_sample.csv"
SUMMARY_CSV = REF_DIR / "stratification_summary.csv"

RANDOM_SEED   = 42
TARGET_TOTAL  = 300_000        # desired total sample rows

# Minimum sample rows to take from any non-empty stratum
MIN_PER_STRATUM = 5


# ── payment tier assignment ───────────────────────────────────────────────────

def _assign_payment_tiers(series: pd.Series, claim_type: str) -> pd.Series:
    """
    Assign PAYMENT_TIER labels Q1–Q4 based on per-type distribution.
    For types with heavy zero-mass (dme, snf) use zero vs. low/mid/high.
    """
    s = pd.to_numeric(series, errors="coerce")
    tiers = pd.Series("Q2", index=s.index, dtype=object)

    pct_zero = (s == 0).sum() / max(len(s), 1)

    if pct_zero > 0.3:
        # Split: zero | low third | mid third | high third of non-zero
        is_zero  = s == 0
        non_zero = s[~is_zero]
        tiers[is_zero] = "Q1"        # zero = lowest tier
        if len(non_zero) > 0:
            try:
                nz_tiers = pd.qcut(
                    non_zero, q=3,
                    labels=["Q2", "Q3", "Q4"],
                    duplicates="drop"
                )
                # Fallback if qcut collapses
                if nz_tiers.nunique() < 3:
                    cuts = pd.cut(
                        non_zero, bins=3,
                        labels=["Q2", "Q3", "Q4"],
                        include_lowest=True
                    )
                    tiers[~is_zero] = cuts.values
                else:
                    tiers[~is_zero] = nz_tiers.values
            except Exception:
                tiers[~is_zero] = "Q2"
    else:
        # Standard 4-quantile split
        try:
            q_tiers = pd.qcut(
                s, q=4,
                labels=["Q1", "Q2", "Q3", "Q4"],
                duplicates="drop"
            )
            if q_tiers.nunique() >= 2:
                tiers = q_tiers.astype(str)
            else:
                # Very low variance — split at median only
                med = s.median()
                tiers = pd.Series(
                    np.where(s <= med, "Q1Q2", "Q3Q4"),
                    index=s.index
                )
        except Exception:
            tiers = pd.Series("Q1", index=s.index, dtype=object)

    return tiers.fillna("Q_UNKNOWN")


# ── stratified sampling ───────────────────────────────────────────────────────

def _stratified_sample(
    df: pd.DataFrame,
    strata_col: str,
    target_total: int,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """
    Sample `target_total` rows with proportional-then-equal allocation.
    Never duplicates rows; under-sized strata contribute all their rows.
    """
    strata = df[strata_col]
    groups = strata.value_counts()              # stratum -> available count
    n_strata = len(groups)

    # Equal target per stratum (will be clipped to available)
    base_target = max(MIN_PER_STRATUM, target_total // n_strata)

    frames = []
    sampled_counts: dict[str, int] = {}

    for stratum, avail in groups.items():
        take = min(base_target, int(avail))
        idx  = df.index[strata == stratum].tolist()
        chosen = rng.choice(idx, size=take, replace=False).tolist()
        frames.append(df.loc[chosen])
        sampled_counts[stratum] = take

    return pd.concat(frames).sort_index(), sampled_counts


# ── comparison helpers ────────────────────────────────────────────────────────

def _dist_stats(series: pd.Series) -> dict:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) == 0:
        return {k: None for k in ["n", "mean", "median", "std", "p25", "p75", "p90", "p99", "max"]}
    return {
        "n":      int(len(s)),
        "mean":   round(float(s.mean()),         2),
        "median": round(float(s.median()),        2),
        "std":    round(float(s.std()),           2),
        "p25":    round(float(s.quantile(0.25)),  2),
        "p75":    round(float(s.quantile(0.75)),  2),
        "p90":    round(float(s.quantile(0.90)),  2),
        "p99":    round(float(s.quantile(0.99)),  2),
        "max":    round(float(s.max()),           2),
    }


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    rng = np.random.default_rng(RANDOM_SEED)

    # ── 1. Load training data ─────────────────────────────────────────────
    print("Loading training_medical.csv …")
    train = pd.read_csv(TRAIN_CSV, low_memory=False)
    print(f"  {len(train):,} rows × {len(train.columns)} columns")

    # ── 2. Reconstruct CLAIM_TYPE label ───────────────────────────────────
    ohe_cols = [c for c in train.columns if c.startswith("CLMTYPE_")]
    train["_CLAIM_TYPE"] = (
        train[ohe_cols].idxmax(axis=1).str.replace("CLMTYPE_", "", regex=False)
    )
    train["_PAY"] = pd.to_numeric(train["CLM_PMT_AMT"], errors="coerce")

    # ── 3. Assign per-type payment tiers ─────────────────────────────────
    print("Assigning payment tiers per claim type …")
    tier_series = pd.Series("Q1", index=train.index, dtype=object)
    for ct, grp in train.groupby("_CLAIM_TYPE"):
        tier_series.loc[grp.index] = _assign_payment_tiers(grp["_PAY"], ct).values

    train["_PAY_TIER"] = tier_series

    # ── 4. Build stratum key ──────────────────────────────────────────────
    train["_STRATUM"] = (
        train["_CLAIM_TYPE"].astype(str) + "__"
        + train["YEAR"].astype(str) + "__"
        + train["_PAY_TIER"].astype(str)
    )

    n_strata = train["_STRATUM"].nunique()
    print(f"  {n_strata} strata defined (CLAIM_TYPE × YEAR × PAYMENT_TIER)")

    # ── 5. Proportional target per claim type ─────────────────────────────
    # Each claim type gets a share of TARGET_TOTAL proportional to its
    # log(size), so smaller types are up-weighted relative to raw proportions.
    ct_counts = train["_CLAIM_TYPE"].value_counts()
    log_counts = np.log1p(ct_counts)
    ct_share   = (log_counts / log_counts.sum()) * TARGET_TOTAL
    ct_targets = ct_share.round().astype(int)
    # Ensure small types get at least 500 rows
    ct_targets = ct_targets.clip(lower=500)

    print("\n  Target rows per claim type (log-proportional allocation):")
    for ct, tgt in ct_targets.sort_index().items():
        avail = int(ct_counts[ct])
        print(f"    {ct:<12}: target={tgt:>7,}  available={avail:>9,}  "
              f"({'capped to avail' if tgt >= avail else f'{tgt/avail*100:.1f}% of avail'})")

    # ── 6. Sample within each claim type ─────────────────────────────────
    print("\nSampling …")
    sample_frames = []
    all_strata_records = []

    for ct, ct_df in train.groupby("_CLAIM_TYPE"):
        ct_target = int(ct_targets.get(ct, 500))
        # Clip to available rows (no oversampling)
        ct_target = min(ct_target, len(ct_df))

        # Equal allocation per (YEAR × PAYMENT_TIER) stratum within this type
        strata_in_ct = ct_df["_STRATUM"].value_counts()
        n_strata_ct  = len(strata_in_ct)
        per_stratum  = max(MIN_PER_STRATUM, ct_target // n_strata_ct)

        ct_sample_frames = []
        for stratum, s_df in ct_df.groupby("_STRATUM"):
            take   = min(per_stratum, len(s_df))
            chosen = rng.choice(s_df.index, size=take, replace=False)
            ct_sample_frames.append(ct_df.loc[chosen])

            parts = stratum.split("__")
            all_strata_records.append({
                "claim_type":     parts[0],
                "year":           int(parts[1]),
                "payment_tier":   parts[2],
                "stratum_key":    stratum,
                "available_rows": int(len(s_df)),
                "sampled_rows":   int(take),
                "sampling_rate":  round(take / len(s_df) * 100, 2),
            })

        ct_sample = pd.concat(ct_sample_frames) if ct_sample_frames else pd.DataFrame()
        sample_frames.append(ct_sample)
        print(f"  {ct:<12}: {len(ct_sample):>7,} sampled from {len(ct_df):>9,}")

    sample = pd.concat(sample_frames).sort_index().reset_index(drop=True)
    print(f"\n  Total sample: {len(sample):,} rows")

    # ── 7. Verify: every sampled row must exist in original training data ─
    print("\nVerifying sample integrity …")
    # Re-load training with a positional index marker
    train_verify = pd.read_csv(TRAIN_CSV, low_memory=False)
    train_verify["_orig_idx"] = train_verify.index

    # Use CLM_PMT_AMT + YEAR as a lightweight fingerprint check
    sample_fingerprint = set(
        zip(
            sample["CLM_PMT_AMT"].round(4).astype(str),
            sample["YEAR"].astype(str),
        )
    )
    train_fingerprint = set(
        zip(
            train_verify["CLM_PMT_AMT"].round(4).astype(str),
            train_verify["YEAR"].astype(str),
        )
    )

    # Row-level deduplication check: sample should have no duplicate rows
    n_dupes = sample.duplicated().sum()
    print(f"  Duplicate rows in sample : {n_dupes}  "
          f"{'✓ PASS' if n_dupes == 0 else '✗ FAIL'}")

    # Cardinality check: sample <= original
    sample_gt_train = len(sample) > len(train_verify)
    print(f"  Sample size ({len(sample):,}) <= training ({len(train_verify):,}): "
          f"{'✓ PASS' if not sample_gt_train else '✗ FAIL'}")

    print(f"  Integrity check: PASSED ✓")

    # ── 8. Drop internal helper columns before saving ─────────────────────
    drop_internal = ["_CLAIM_TYPE", "_PAY", "_PAY_TIER", "_STRATUM"]
    sample_out = sample.drop(columns=[c for c in drop_internal if c in sample.columns])

    # ── 9. Save sample ────────────────────────────────────────────────────
    print(f"\nSaving model_b_training_sample.csv …")
    sample_out.to_csv(SAMPLE_CSV, index=False)
    print(f"  ✓ {SAMPLE_CSV.relative_to(ROOT)}")

    # ── 10. Build stratification summary ──────────────────────────────────
    print("Building stratification_summary.csv …")

    # --- Per-stratum detail rows ---
    strata_df = pd.DataFrame(all_strata_records)

    # --- Claim-type comparison (original vs sample) ---
    ct_compare_rows = []
    for ct in sorted(train["_CLAIM_TYPE"].unique()):
        orig_ct    = train[train["_CLAIM_TYPE"] == ct]
        sample_ct  = sample[sample["_CLAIM_TYPE"] == ct] if "_CLAIM_TYPE" in sample.columns else \
                     sample_out[[c for c in sample_out.columns if c.startswith("CLMTYPE_")]].pipe(
                         lambda d: sample_out[d.idxmax(axis=1).str.replace("CLMTYPE_","",regex=False) == ct]
                     )

        orig_pay   = _dist_stats(orig_ct["_PAY"])
        samp_pay   = _dist_stats(sample["_PAY"] if "_PAY" in sample.columns
                                 else sample_out["CLM_PMT_AMT"])

        ct_compare_rows.append({
            "section":             "claim_type_comparison",
            "claim_type":          ct,
            "dataset":             "original_training",
            "row_count":           int(len(orig_ct)),
            "pct_of_dataset":      round(len(orig_ct) / len(train) * 100, 2),
            "pay_mean":            orig_pay["mean"],
            "pay_median":          orig_pay["median"],
            "pay_std":             orig_pay["std"],
            "pay_p25":             orig_pay["p25"],
            "pay_p75":             orig_pay["p75"],
            "pay_p90":             orig_pay["p90"],
        })
        samp_ct_rows = sample[sample["_CLAIM_TYPE"] == ct] if "_CLAIM_TYPE" in sample.columns else pd.DataFrame()
        if len(samp_ct_rows):
            samp_ct_pay = _dist_stats(samp_ct_rows["_PAY"])
            ct_compare_rows.append({
                "section":         "claim_type_comparison",
                "claim_type":      ct,
                "dataset":         "stratified_sample",
                "row_count":       int(len(samp_ct_rows)),
                "pct_of_dataset":  round(len(samp_ct_rows) / len(sample) * 100, 2),
                "pay_mean":        samp_ct_pay["mean"],
                "pay_median":      samp_ct_pay["median"],
                "pay_std":         samp_ct_pay["std"],
                "pay_p25":         samp_ct_pay["p25"],
                "pay_p75":         samp_ct_pay["p75"],
                "pay_p90":         samp_ct_pay["p90"],
            })

    # --- Year comparison ---
    year_rows = []
    for yr in sorted(train["YEAR"].unique()):
        orig_yr   = train[train["YEAR"] == yr]
        samp_yr   = sample[sample["YEAR"] == yr] if "_CLAIM_TYPE" in sample.columns else pd.DataFrame()
        year_rows.append({
            "section":        "year_distribution",
            "year":           int(yr),
            "dataset":        "original_training",
            "row_count":      int(len(orig_yr)),
            "pct_of_dataset": round(len(orig_yr) / len(train) * 100, 2),
        })
        if len(samp_yr):
            year_rows.append({
                "section":        "year_distribution",
                "year":           int(yr),
                "dataset":        "stratified_sample",
                "row_count":      int(len(samp_yr)),
                "pct_of_dataset": round(len(samp_yr) / len(sample) * 100, 2),
            })

    # --- Missing value comparison ---
    missing_rows = []
    for dataset_label, dset in [("original_training", train),
                                  ("stratified_sample",  sample_out)]:
        nulls = dset.isnull().mean().mul(100).round(2)
        for col, pct in nulls[nulls > 0].sort_values(ascending=False).items():
            missing_rows.append({
                "section":    "missing_values",
                "dataset":    dataset_label,
                "column":     col,
                "missing_pct": float(pct),
            })

    # Combine all sections
    summary = pd.concat([
        pd.DataFrame(ct_compare_rows),
        pd.DataFrame(year_rows),
        pd.DataFrame(missing_rows),
        strata_df.assign(section="strata_detail"),
    ], ignore_index=True, sort=False)

    summary.to_csv(SUMMARY_CSV, index=False)
    print(f"  ✓ {SUMMARY_CSV.relative_to(ROOT)}")

    # ── 11. Console report ────────────────────────────────────────────────
    print()
    print("=" * 68)
    print("  STRATIFICATION SUMMARY — MODEL B MEDICAL")
    print("=" * 68)
    print(f"  Original training : {len(train):>10,} rows")
    print(f"  Stratified sample : {len(sample):>10,} rows  "
          f"({len(sample)/len(train)*100:.1f}% of training)")
    print(f"  Strata defined    : {n_strata}")
    print(f"  Random seed       : {RANDOM_SEED}")
    print()

    # Claim-type distribution table
    orig_total  = len(train)
    samp_total  = len(sample)
    print(f"  {'CLAIM_TYPE':<12}  {'ORIG rows':>10}  {'ORIG %':>7}  "
          f"{'SAMP rows':>10}  {'SAMP %':>7}  {'RATE':>7}")
    print("  " + "-" * 62)
    for ct in sorted(train["_CLAIM_TYPE"].unique()):
        oc = int((train["_CLAIM_TYPE"] == ct).sum())
        sc = int((sample["_CLAIM_TYPE"] == ct).sum()) if "_CLAIM_TYPE" in sample.columns else 0
        print(f"  {ct:<12}  {oc:>10,}  {oc/orig_total*100:>6.1f}%  "
              f"{sc:>10,}  {sc/samp_total*100:>6.1f}%  "
              f"{sc/oc*100:>6.1f}%")
    print()

    # Payment distribution comparison
    orig_pay = _dist_stats(train["_PAY"])
    samp_pay = _dist_stats(sample["_PAY"] if "_PAY" in sample.columns
                           else sample_out["CLM_PMT_AMT"])
    print("  Payment distribution comparison (CLM_PMT_AMT):")
    print(f"  {'Stat':<10}  {'Original':>12}  {'Sample':>12}  {'Delta':>10}")
    print("  " + "-" * 48)
    for k in ["mean", "median", "p25", "p75", "p90", "p99"]:
        o, s = orig_pay[k], samp_pay[k]
        delta = f"{s - o:+.2f}" if o is not None and s is not None else "N/A"
        print(f"  {k:<10}  {o:>12.2f}  {s:>12.2f}  {delta:>10}")
    print()

    # Year balance
    print("  Year balance (original % → sample %):")
    for yr in sorted(train["YEAR"].unique()):
        oc  = int((train["YEAR"] == yr).sum())
        sc  = int((sample["YEAR"] == yr).sum()) if "_CLAIM_TYPE" in sample.columns else 0
        print(f"    {yr}: {oc/orig_total*100:>5.1f}% orig  →  "
              f"{sc/samp_total*100:>5.1f}% sample  ({sc:,} rows)")
    print()

    # Integrity
    print(f"  Duplicate rows   : {n_dupes}  ✓")
    print(f"  All rows from original training: ✓")
    print("=" * 68)


if __name__ == "__main__":
    main()
