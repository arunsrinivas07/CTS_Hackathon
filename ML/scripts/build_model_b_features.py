"""
Model B — Medical Anomaly Feature Dataset Builder
===================================================
Combines:
  1. claims_with_beneficiary_history.csv   (normalized claims + bene history)
  2. medical_claim_type_stats.json         (training-period peer statistics)

Produces a machine-learning-ready feature table with:
  - No raw identifiers (CLAIM_ID, BENE_ID, PROVIDER_ID excluded)
  - No future information
  - All peer-comparison features derived from training-period stats only
  - One-hot encoded CLAIM_TYPE

Outputs
-------
data/processed/medical/model_b_features.csv
data/processed/reference/model_b_feature_list.json

Run from project root:
    python scripts/build_model_b_features.py
"""

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── paths ─────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).resolve().parent.parent
HISTORY_CSV = ROOT / "data" / "processed" / "medical" / "claims_with_beneficiary_history.csv"
STATS_JSON  = ROOT / "data" / "processed" / "reference" / "medical_claim_type_stats.json"
OUT_DIR     = ROOT / "data" / "processed" / "medical"
REF_DIR     = ROOT / "data" / "processed" / "reference"
OUT_DIR.mkdir(parents=True, exist_ok=True)
REF_DIR.mkdir(parents=True, exist_ok=True)

OUT_CSV         = OUT_DIR / "model_b_features.csv"
FEATURE_LIST    = REF_DIR / "model_b_feature_list.json"

# Columns to NEVER include in the feature table
EXCLUDE_COLS = {
    "CLAIM_ID", "BENE_ID", "PROVIDER_ID",
    "AT_PHYSN_NPI", "ORG_NPI_NUM",           # raw provider IDs
    "PRNCPAL_DGNS_CD",                         # raw code, not a feature
    "CLAIM_START_DATE", "CLAIM_END_DATE",      # raw dates
    "SOURCE_FILE",                             # same as CLAIM_TYPE
    "BENE_BIRTH_DT", "BENE_DEATH_DT",         # raw dates / identifiers
}

# ── stats lookup helpers ──────────────────────────────────────────────────────

class PeerStats:
    """Lightweight wrapper around the JSON stats for fast lookups."""

    # Map normalized col names → stats JSON metric keys
    METRIC_MAP = {
        "CLM_PMT_AMT":          "clm_pmt_amt",
        "CLM_TOT_CHRG_AMT":     "clm_tot_chrg_amt",
        "CLAIM_DURATION_DAYS":  "claim_duration_days",
        "LINE_COUNT":           "line_count",
        "UNIT_COUNT":           "unit_count",
        "DIAG_COUNT":           "diag_count",
        "PROC_COUNT":           "proc_count",
    }

    def __init__(self, path: Path):
        with open(path, encoding="utf-8") as f:
            self._d = json.load(f)

    def median(self, claim_type: str, metric: str) -> float | None:
        return self._d.get(claim_type, {}).get(metric, {}).get("median")

    def mad_scaled(self, claim_type: str, metric: str) -> float | None:
        return self._d.get(claim_type, {}).get(metric, {}).get("mad_scaled")

    def percentile_rank(self, claim_type: str, metric: str, value: float) -> float | None:
        """
        Returns the interpolated percentile rank (0–100) of `value` within
        the pre-computed percentile distribution for this claim_type/metric.
        Uses linear interpolation between the nine reference percentile points.
        """
        pcts = self._d.get(claim_type, {}).get(metric, {}).get("percentiles")
        if pcts is None or value is None or np.isnan(value):
            return None
        points = sorted((int(k[1:]), v) for k, v in pcts.items())   # [(1,v),(5,v),...]
        ranks  = [p[0] for p in points]
        values = [p[1] for p in points]

        if value <= values[0]:
            return float(ranks[0])
        if value >= values[-1]:
            return float(ranks[-1])
        # Linear interpolation
        for i in range(len(values) - 1):
            lo_v, hi_v = values[i], values[i + 1]
            lo_r, hi_r = ranks[i],  ranks[i + 1]
            if lo_v <= value <= hi_v:
                if hi_v == lo_v:
                    return float(lo_r)
                frac = (value - lo_v) / (hi_v - lo_v)
                return float(lo_r + frac * (hi_r - lo_r))
        return None


def _robust_z(value: float, median: float | None, mad_scaled: float | None) -> float | None:
    """Compute robust Z-score; returns None when denominator is zero/None."""
    if median is None or mad_scaled is None:
        return None
    if np.isnan(value):
        return None
    if mad_scaled == 0.0:
        # Zero MAD means all training values equal the median; return sign-based score
        return 0.0 if value == median else np.sign(value - median) * np.inf
    return (value - median) / mad_scaled


# ── vectorised peer-comparison builders ──────────────────────────────────────

def _add_peer_features(df: pd.DataFrame, stats: PeerStats) -> pd.DataFrame:
    """
    For each claim type, compute vectorised peer comparison features.
    Works group-by-group to apply type-specific constants.
    """
    # Metric config: (source_col, short_name, stats_key)
    METRICS = [
        ("CLM_PMT_AMT",         "CLAIM_PAYMENT",        "clm_pmt_amt"),
        ("CLM_TOT_CHRG_AMT",    "CLAIM_CHARGE",         "clm_tot_chrg_amt"),
        ("CLAIM_DURATION_DAYS", "CLAIM_DURATION_DAYS",  "claim_duration_days"),
        ("LINE_COUNT",          "NUM_LINES",             "line_count"),
        ("DIAG_COUNT",          "NUM_DIAGNOSES",         "diag_count"),
        ("PROC_COUNT",          "NUM_PROCEDURES",        "proc_count"),
    ]

    # Pre-allocate output columns
    for _, name, _ in METRICS:
        df[f"{name}_VS_TYPE_MEDIAN"]   = np.nan
        df[f"{name}_TYPE_ROBUST_Z"]    = np.nan
        df[f"{name}_TYPE_PERCENTILE"]  = np.nan

    for ct, grp_idx in df.groupby("CLAIM_TYPE").groups.items():
        for src_col, name, stats_key in METRICS:
            med = stats.median(ct, stats_key)
            mad = stats.mad_scaled(ct, stats_key)

            if med is None:
                continue

            vals = pd.to_numeric(df.loc[grp_idx, src_col], errors="coerce")

            # vs_median: ratio (value / median), NaN where median=0
            if med != 0:
                df.loc[grp_idx, f"{name}_VS_TYPE_MEDIAN"] = (vals / med).values
            else:
                df.loc[grp_idx, f"{name}_VS_TYPE_MEDIAN"] = np.where(
                    vals == 0, 1.0, np.nan
                )

            # robust Z
            if mad is not None and mad != 0.0:
                df.loc[grp_idx, f"{name}_TYPE_ROBUST_Z"] = ((vals - med) / mad).values
            else:
                df.loc[grp_idx, f"{name}_TYPE_ROBUST_Z"] = np.where(
                    vals == med, 0.0, np.sign(vals - med) * np.inf
                )

            # percentile rank (vectorised via apply on the group)
            pcts = (
                df._d_stats.get(ct, {})
                   .get(stats_key, {})
                   .get("percentiles")
            ) if hasattr(df, "_d_stats") else None

            # Use the stats object properly
            pct_series = vals.apply(
                lambda v, ct=ct, sk=stats_key: stats.percentile_rank(ct, sk, v)
            )
            df.loc[grp_idx, f"{name}_TYPE_PERCENTILE"] = pct_series.values

    return df


# ── beneficiary age at claim ──────────────────────────────────────────────────

def _bene_age(df: pd.DataFrame) -> pd.Series:
    """Compute beneficiary age at claim start. Returns NaN if DOB missing."""
    try:
        dob = pd.to_datetime(df["BENE_BIRTH_DT"], format="%d-%b-%Y", errors="coerce")
        clm = pd.to_datetime(df["CLAIM_START_DATE"], errors="coerce")
        age = (clm - dob).dt.days / 365.25
        return age.where(age >= 0)
    except Exception:
        return pd.Series(np.nan, index=df.index)


def _is_deceased(df: pd.DataFrame) -> pd.Series:
    """1 if the beneficiary has a recorded death date, else 0."""
    return df["BENE_DEATH_DT"].notna().astype(int)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    # ── 1. Load data ──────────────────────────────────────────────────────
    print("Loading claims history …")
    df = pd.read_csv(HISTORY_CSV, low_memory=False)
    print(f"  {len(df):,} rows × {len(df.columns)} columns")

    print("Loading peer statistics …")
    stats = PeerStats(STATS_JSON)

    # ── 2. Derived base features ──────────────────────────────────────────
    print("Computing derived features …")

    # Safe divide helper
    def safe_div(a: pd.Series, b: pd.Series) -> pd.Series:
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(b > 0, a / b, np.nan)

    pmt  = pd.to_numeric(df["CLM_PMT_AMT"],      errors="coerce")
    chrg = pd.to_numeric(df["CLM_TOT_CHRG_AMT"], errors="coerce")
    lns  = pd.to_numeric(df["LINE_COUNT"],        errors="coerce")
    uts  = pd.to_numeric(df["UNIT_COUNT"],        errors="coerce")

    df["PAYMENT_PER_LINE"]   = safe_div(pmt,  lns)
    df["CHARGE_PER_LINE"]    = safe_div(chrg, lns)
    df["PAYMENT_PER_UNIT"]   = safe_div(pmt,  uts)
    df["CHARGE_PER_UNIT"]    = safe_div(chrg, uts)
    df["UNPAID_CHARGE"]      = (chrg - pmt).clip(lower=0)

    # Beneficiary-relative payment features
    hist_avg = pd.to_numeric(df["HIST_PREV_AVG_PAY"], errors="coerce")
    hist_max = pd.to_numeric(df["HIST_PREV_MAX_PAY"], errors="coerce")
    df["PAYMENT_VS_BENE_PREV_AVG"] = safe_div(pmt, hist_avg)
    df["PAYMENT_VS_BENE_PREV_MAX"] = safe_div(pmt, hist_max)

    # Beneficiary demographics
    df["BENE_AGE_AT_CLAIM"]    = _bene_age(df)
    df["BENE_IS_DECEASED"]     = _is_deceased(df)

    # ── 3. Peer comparison features ───────────────────────────────────────
    print("Computing peer-comparison features …")
    df = _add_peer_features(df, stats)

    # ── 4. One-hot encode CLAIM_TYPE ──────────────────────────────────────
    print("One-hot encoding CLAIM_TYPE …")
    dummies = pd.get_dummies(df["CLAIM_TYPE"], prefix="CLMTYPE").astype(int)
    df = pd.concat([df, dummies], axis=1)

    # ── 4b. Cap inf robust-Z values ──────────────────────────────────────
    # Where MAD=0 and value != median, robust Z is ±inf (mathematically correct
    # but not usable by most ML frameworks). Cap at ±10 (well outside normal range).
    robust_z_cols = [c for c in df.columns if c.endswith("_TYPE_ROBUST_Z")]
    for col in robust_z_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        df[col] = df[col].clip(lower=-10.0, upper=10.0)

    # ── 5. Drop excluded / identifier columns ─────────────────────────────
    print("Dropping identifier and raw columns …")
    drop_cols = [c for c in EXCLUDE_COLS if c in df.columns]
    # Also drop raw string columns not useful as features
    drop_cols += [c for c in ["CLAIM_TYPE", "SOURCE_FILE"] if c in df.columns]
    df = df.drop(columns=drop_cols)

    # ── 6. Define final feature columns (ordered) ─────────────────────────
    # Categories:
    #   A. Temporal
    #   B. Claim amounts
    #   C. Claim structure
    #   D. Per-unit / per-line
    #   E. Peer comparison (vs type median / robust Z / percentile)
    #   F. Beneficiary demographics
    #   G. Beneficiary history (all-time)
    #   H. Beneficiary utilisation windows
    #   I. CLAIM_TYPE one-hot

    FEATURE_GROUPS = {
        "temporal": [
            "YEAR",
        ],
        "claim_amounts": [
            "CLM_PMT_AMT",
            "CLM_TOT_CHRG_AMT",
            "UNPAID_CHARGE",
        ],
        "claim_structure": [
            "CLAIM_DURATION_DAYS",
            "LINE_COUNT",
            "UNIT_COUNT",
            "DIAG_COUNT",
            "PROC_COUNT",
        ],
        "per_unit_line": [
            "PAYMENT_PER_LINE",
            "CHARGE_PER_LINE",
            "PAYMENT_PER_UNIT",
            "CHARGE_PER_UNIT",
        ],
        "peer_payment": [
            "CLAIM_PAYMENT_VS_TYPE_MEDIAN",
            "CLAIM_PAYMENT_TYPE_ROBUST_Z",
            "CLAIM_PAYMENT_TYPE_PERCENTILE",
        ],
        "peer_charge": [
            "CLAIM_CHARGE_VS_TYPE_MEDIAN",
            "CLAIM_CHARGE_TYPE_ROBUST_Z",
            "CLAIM_CHARGE_TYPE_PERCENTILE",
        ],
        "peer_duration": [
            "CLAIM_DURATION_DAYS_VS_TYPE_MEDIAN",
            "CLAIM_DURATION_DAYS_TYPE_ROBUST_Z",
            "CLAIM_DURATION_DAYS_TYPE_PERCENTILE",
        ],
        "peer_lines": [
            "NUM_LINES_VS_TYPE_MEDIAN",
            "NUM_LINES_TYPE_ROBUST_Z",
            "NUM_LINES_TYPE_PERCENTILE",
        ],
        "peer_diagnoses": [
            "NUM_DIAGNOSES_VS_TYPE_MEDIAN",
            "NUM_DIAGNOSES_TYPE_ROBUST_Z",
            "NUM_DIAGNOSES_TYPE_PERCENTILE",
        ],
        "peer_procedures": [
            "NUM_PROCEDURES_VS_TYPE_MEDIAN",
            "NUM_PROCEDURES_TYPE_ROBUST_Z",
            "NUM_PROCEDURES_TYPE_PERCENTILE",
        ],
        "bene_relative_payment": [
            "PAYMENT_VS_BENE_PREV_AVG",
            "PAYMENT_VS_BENE_PREV_MAX",
        ],
        "bene_demographics": [
            "BENE_AGE_AT_CLAIM",
            "BENE_IS_DECEASED",
            "SEX_IDENT_CD",
            "BENE_RACE_CD",
            "STATE_CODE",
        ],
        "bene_history": [
            "HIST_PREV_CLAIM_CNT",
            "HIST_PREV_TOTAL_PAY",
            "HIST_PREV_AVG_PAY",
            "HIST_PREV_MAX_PAY",
            "HIST_PREV_PROVIDER_CNT",
            "HIST_PREV_TYPE_CNT",
            "HIST_DAYS_SINCE_PREV",
            "HIST_DAYS_SINCE_SAME_TYPE",
        ],
        "bene_utilisation_30d": [
            "HIST_W30_CLAIM_CNT",
            "HIST_W30_TOTAL_PAY",
            "HIST_W30_PROVIDER_CNT",
        ],
        "bene_utilisation_90d": [
            "HIST_W90_CLAIM_CNT",
            "HIST_W90_TOTAL_PAY",
            "HIST_W90_PROVIDER_CNT",
        ],
        "claim_type_ohe": sorted([c for c in df.columns if c.startswith("CLMTYPE_")]),
    }

    # Build flat ordered feature list, keep only those present in df
    feature_cols = []
    for group, cols in FEATURE_GROUPS.items():
        for c in cols:
            if c in df.columns and c not in feature_cols:
                feature_cols.append(c)

    # Select only feature columns (discard anything not in the list)
    df_out = df[feature_cols].copy()

    # ── 7. Save ───────────────────────────────────────────────────────────
    print(f"\nWriting {len(df_out):,} rows × {len(df_out.columns)} feature columns …")
    df_out.to_csv(OUT_CSV, index=False)
    print(f"✓ Saved → {OUT_CSV.relative_to(ROOT)}")

    # Feature list JSON
    feature_meta = {
        "total_features":  len(feature_cols),
        "total_rows":      len(df_out),
        "groups":          {grp: [c for c in cols if c in df.columns]
                            for grp, cols in FEATURE_GROUPS.items()},
        "feature_columns": feature_cols,
        "excluded_identifiers": sorted(EXCLUDE_COLS),
        "notes": [
            "CLAIM_TYPE is one-hot encoded as CLMTYPE_<type>",
            "Peer stats derived from training period 2015-2022 only",
            "Robust Z = (value - type_median) / (MAD * 1.4826); capped at [-10, +10]",
            "When MAD=0, robust Z is 0.0 if value==median, else ±10 (cap applied)",
            "Percentile rank interpolated from 9-point reference distribution",
            "HIST_ features are computed as strictly-prior information (no leakage)",
            "VS_TYPE_MEDIAN = value / type_median (ratio; 1.0 = exactly median)",
            "UNPAID_CHARGE = max(0, CLM_TOT_CHRG_AMT - CLM_PMT_AMT)",
            "PAYMENT_VS_BENE_PREV_AVG/MAX = payment / bene historical avg/max",
        ],
    }
    with open(FEATURE_LIST, "w", encoding="utf-8") as f:
        json.dump(feature_meta, f, indent=2)
    print(f"✓ Feature list saved → {FEATURE_LIST.relative_to(ROOT)}")

    # ── 8. Summary ────────────────────────────────────────────────────────
    print("\n── Feature null rates ────────────────────────────────────────────")
    null_pct = df_out.isnull().mean().mul(100).round(1)
    non_zero = (null_pct > 0)
    if non_zero.any():
        print(null_pct[non_zero].to_string())
    else:
        print("  All features 100% populated (no nulls)")

    print("\n── Feature value ranges (sample) ────────────────────────────────")
    sample_cols = [
        "CLM_PMT_AMT", "CLAIM_PAYMENT_TYPE_ROBUST_Z",
        "CLAIM_PAYMENT_TYPE_PERCENTILE", "BENE_AGE_AT_CLAIM",
        "HIST_PREV_CLAIM_CNT", "HIST_W30_CLAIM_CNT",
    ]
    for c in sample_cols:
        if c in df_out.columns:
            s = df_out[c].dropna()
            print(f"  {c:<40s}: min={s.min():.2f}  mean={s.mean():.2f}  max={s.max():.2f}")

    print("\n── CLAIM_TYPE one-hot distribution ──────────────────────────────")
    for c in sorted([c for c in df_out.columns if c.startswith("CLMTYPE_")]):
        cnt = df_out[c].sum()
        pct = cnt / len(df_out) * 100
        print(f"  {c:<25s}: {cnt:>9,}  ({pct:.1f}%)")

    print(f"\nTotal features: {len(feature_cols)}")


if __name__ == "__main__":
    main()
