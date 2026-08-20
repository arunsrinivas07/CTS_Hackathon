"""
Model B — Claim-Type-Specific Score Calibration
=================================================
Converts raw IsolationForest decision_function scores into per-claim-type
percentile-based risk scores using ONLY the training sample as the reference
distribution.  The live scoring pipeline never recomputes calibration from
incoming claims — it reads the frozen reference tables produced here.

Calibration formula
-------------------
For a new claim of CLAIM_TYPE t with raw_score r:
    pct_rank  = percentile_rank_within_type_t(r)   # 0–100; higher = more normal
    risk_score = (1 - pct_rank/100) * 100           # higher = more anomalous

Risk levels
-----------
    [80, 100]  → CRITICAL
    [60,  80)  → HIGH
    [40,  60)  → MEDIUM
    [ 0,  40)  → LOW

Calibration artefacts saved
----------------------------
models/model_b_claim/
    score_calibration.pkl    — dict: {claim_type: sorted np.ndarray of raw scores}
    score_calibration.json   — human-readable percentile anchors + metadata

Run from project root:
    python scripts/calibrate_model_b.py
"""

import json
import pickle
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── paths ─────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).resolve().parent.parent
MODEL_DIR   = ROOT / "models" / "model_b_claim"
SAMPLE_CSV  = ROOT / "data" / "processed" / "medical" / "model_b_training_sample.csv"
OUT_DIR     = ROOT / "data" / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CALIB_PKL   = MODEL_DIR / "score_calibration.pkl"
CALIB_JSON  = MODEL_DIR / "score_calibration.json"
SCORED_CSV  = OUT_DIR   / "model_b_test_scores_calibrated.csv"

# Risk level thresholds (calibrated score, higher = more anomalous)
RISK_LEVELS = [
    (80.0,  "CRITICAL"),
    (60.0,  "HIGH"),
    (40.0,  "MEDIUM"),
    (0.0,   "LOW"),
]

PERCENTILE_ANCHORS = [1, 5, 10, 20, 25, 30, 40, 50, 60, 70, 75, 80, 90, 95, 99]


# ── helpers ───────────────────────────────────────────────────────────────────

def _percentile_rank(value: float, reference: np.ndarray) -> float:
    """
    Compute what percentile `value` falls at within `reference` (sorted array).
    Returns 0–100. Uses linear interpolation identical to scipy.stats.percentileofscore
    with kind='mean'.
    """
    n = len(reference)
    if n == 0:
        return 50.0
    # Number of values strictly below and equal to value
    n_below = int(np.searchsorted(reference, value, side="left"))
    n_equal = int(np.searchsorted(reference, value, side="right")) - n_below
    # mean method: (n_below + n_below + n_equal) / 2 / n * 100
    pct = (n_below + (n_equal / 2)) / n * 100.0
    return float(np.clip(pct, 0.0, 100.0))


def _calibrated_risk_score(raw_score: float, reference: np.ndarray) -> float:
    """
    calibrated_risk_score = (1 - percentile_rank/100) * 100
    Range: [0, 100].  100 = most anomalous; 0 = most normal.
    """
    pct = _percentile_rank(raw_score, reference)
    return float((1.0 - pct / 100.0) * 100.0)


def _assign_risk_level(score: float) -> str:
    for threshold, label in RISK_LEVELS:
        if score >= threshold:
            return label
    return "LOW"


def _vectorised_calibrate(
    raw_scores: np.ndarray,
    reference: np.ndarray,
) -> np.ndarray:
    """Vectorised calibration for an array of scores."""
    n_ref = len(reference)
    n_below = np.searchsorted(reference, raw_scores, side="left").astype(float)
    n_right = np.searchsorted(reference, raw_scores, side="right").astype(float)
    n_equal = n_right - n_below
    pct = (n_below + n_equal / 2.0) / n_ref * 100.0
    pct = np.clip(pct, 0.0, 100.0)
    return (1.0 - pct / 100.0) * 100.0


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    # ── 1. Load frozen artefacts ──────────────────────────────────────────
    print("Loading model artefacts …")
    with open(MODEL_DIR / "isolation_forest.pkl", "rb") as f:
        iso = pickle.load(f)
    with open(MODEL_DIR / "imputer.pkl", "rb") as f:
        imp = pickle.load(f)
    with open(MODEL_DIR / "scaler.pkl", "rb") as f:
        scl = pickle.load(f)
    with open(MODEL_DIR / "feature_columns.pkl", "rb") as f:
        feat_cols = pickle.load(f)
    with open(MODEL_DIR / "metadata.json", encoding="utf-8") as f:
        meta = json.load(f)

    claim_types = meta["claim_types"]
    print(f"  Claim types: {claim_types}")

    # ── 2. Score training sample (calibration reference source) ───────────
    print("\nScoring training sample to build calibration references …")
    train = pd.read_csv(SAMPLE_CSV, low_memory=False)
    ohe_cols = [c for c in train.columns if c.startswith("CLMTYPE_")]
    train["_CT"] = (
        train[ohe_cols].idxmax(axis=1).str.replace("CLMTYPE_", "", regex=False)
    )

    X_train = train[feat_cols].values
    X_imp   = imp.transform(X_train)
    X_scl   = scl.transform(X_imp)
    raw_train = iso.decision_function(X_scl)
    train["_RAW"] = raw_train
    print(f"  {len(train):,} training rows scored")

    # ── 3. Build per-type calibration reference (sorted raw score array) ──
    print("\nBuilding per-claim-type calibration reference arrays …")
    calibration_ref: dict[str, np.ndarray] = {}

    for ct in sorted(claim_types):
        ct_scores = train.loc[train["_CT"] == ct, "_RAW"].dropna().values
        ct_scores_sorted = np.sort(ct_scores)
        calibration_ref[ct] = ct_scores_sorted
        print(f"  {ct:<12}: {len(ct_scores_sorted):>7,} reference scores  "
              f"[{ct_scores_sorted.min():.4f}, {ct_scores_sorted.max():.4f}]")

    # ── 4. Save calibration.pkl (for FastAPI) ─────────────────────────────
    with open(CALIB_PKL, "wb") as f:
        pickle.dump(calibration_ref, f, protocol=5)
    size_kb = CALIB_PKL.stat().st_size / 1024
    print(f"\n  ✓ score_calibration.pkl saved  ({size_kb:,.0f} KB)")

    # ── 5. Save calibration.json (human-readable + FastAPI fallback) ──────
    calib_json: dict = {
        "_metadata": {
            "description": (
                "Per-claim-type calibration reference for Model B. "
                "Built from training sample (YEAR 2014–2022) only. "
                "FastAPI must load score_calibration.pkl to apply calibration. "
                "Never recompute calibration from live incoming claims."
            ),
            "calibration_formula": (
                "pct_rank = percentile_of_score(raw_score, reference_array)  # 0-100\n"
                "risk_score = (1 - pct_rank / 100) * 100  # 0-100, higher=more anomalous"
            ),
            "risk_levels": {
                "CRITICAL": "[80, 100]",
                "HIGH":     "[60, 80)",
                "MEDIUM":   "[40, 60)",
                "LOW":      "[0,  40)",
            },
            "training_period":   "2014–2022",
            "source_file":       "data/processed/medical/model_b_training_sample.csv",
            "trained_at":        meta.get("trained_at", ""),
            "claim_types":       sorted(claim_types),
            "percentile_anchors": PERCENTILE_ANCHORS,
        }
    }

    for ct in sorted(claim_types):
        ref = calibration_ref[ct]
        n   = len(ref)
        pct_values = {
            f"p{p}": round(float(np.percentile(ref, p)), 6)
            for p in PERCENTILE_ANCHORS
        }
        calib_json[ct] = {
            "n_reference_scores": int(n),
            "raw_score_min":      round(float(ref.min()),    6),
            "raw_score_max":      round(float(ref.max()),    6),
            "raw_score_median":   round(float(np.median(ref)), 6),
            "raw_score_mean":     round(float(ref.mean()),   6),
            "raw_score_std":      round(float(ref.std()),    6),
            "percentile_anchors": pct_values,
            "note": (
                f"To calibrate a new {ct} claim: look up raw_score in "
                f"score_calibration.pkl['{ct}'] sorted array, compute percentile rank, "
                f"then risk_score = (1 - pct_rank/100)*100"
            ),
        }

    with open(CALIB_JSON, "w", encoding="utf-8") as f:
        json.dump(calib_json, f, indent=2)
    size_kb = CALIB_JSON.stat().st_size / 1024
    print(f"  ✓ score_calibration.json saved ({size_kb:.1f} KB)")

    # ── 6. Apply calibration to test set and save ──────────────────────────
    print("\nApplying calibration to test set …")
    test = pd.read_csv(
        ROOT / "data" / "outputs" / "model_b_test_scores.csv",
        low_memory=False,
    )
    ohe_test = [c for c in test.columns if c.startswith("CLMTYPE_")]
    test["_CT"] = (
        test[ohe_test].idxmax(axis=1).str.replace("CLMTYPE_", "", regex=False)
    )

    test["CALIBRATED_RISK_SCORE"] = np.nan
    test["CALIBRATED_RISK_LEVEL"] = "UNKNOWN"

    for ct in sorted(claim_types):
        mask = test["_CT"] == ct
        if mask.sum() == 0:
            continue
        ref  = calibration_ref[ct]
        raw  = test.loc[mask, "RAW_DECISION_SCORE"].values
        cal  = _vectorised_calibrate(raw, ref)
        test.loc[mask, "CALIBRATED_RISK_SCORE"] = cal
        test.loc[mask, "CALIBRATED_RISK_LEVEL"]  = [_assign_risk_level(s) for s in cal]
        print(f"  {ct:<12}: {mask.sum():>6,} rows calibrated  "
              f"risk_score range [{cal.min():.2f}, {cal.max():.2f}]  "
              f"mean={cal.mean():.2f}")

    # Verify no NaNs in calibrated score
    nan_cal = int(test["CALIBRATED_RISK_SCORE"].isna().sum())
    assert nan_cal == 0, f"NaN calibrated scores: {nan_cal}"
    print(f"\n  NaN calibrated scores: {nan_cal}  ✓")

    # Verify scores in [0, 100]
    oob = int(((test["CALIBRATED_RISK_SCORE"] < 0) |
               (test["CALIBRATED_RISK_SCORE"] > 100)).sum())
    assert oob == 0, f"Out-of-range calibrated scores: {oob}"
    print(f"  Out-of-range [0,100]: {oob}  ✓")

    # Drop internal helper col and save
    test_out = test.drop(columns=["_CT"])
    test_out.to_csv(SCORED_CSV, index=False)
    print(f"\n  ✓ Calibrated scores saved → {SCORED_CSV.relative_to(ROOT)}")

    # ── 7. Summary report ─────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("  MODEL B CALIBRATION SUMMARY")
    print("=" * 70)
    print(f"  Reference built from : training sample (YEAR 2014–2022)")
    print(f"  Reference rows total : {len(train):,}")
    print()

    # Per-claim-type calibrated score distribution on test
    print(f"  {'CLAIM_TYPE':<13} {'n':>6}  {'mean_cal':>9}  {'med_cal':>8}  "
          f"{'CRIT%':>7}  {'HIGH%':>7}  {'MED%':>7}  {'LOW%':>7}")
    print("  " + "-" * 68)
    total = len(test_out)
    for ct in sorted(claim_types):
        mask = test_out[[c for c in test_out.columns if c.startswith("CLMTYPE_")]].idxmax(axis=1).str.replace("CLMTYPE_","",regex=False) == ct
        ct_df = test_out[mask]
        if len(ct_df) == 0:
            continue
        cal = ct_df["CALIBRATED_RISK_SCORE"]
        lvl = ct_df["CALIBRATED_RISK_LEVEL"]
        print(
            f"  {ct:<13} {len(ct_df):>6,}  "
            f"{cal.mean():>9.2f}  {cal.median():>8.2f}  "
            f"{(lvl=='CRITICAL').mean()*100:>6.1f}%  "
            f"{(lvl=='HIGH').mean()*100:>6.1f}%  "
            f"{(lvl=='MEDIUM').mean()*100:>6.1f}%  "
            f"{(lvl=='LOW').mean()*100:>6.1f}%"
        )

    print()
    # Overall distribution
    cal_all = test_out["CALIBRATED_RISK_SCORE"]
    lvl_all = test_out["CALIBRATED_RISK_LEVEL"]
    print("  Overall calibrated risk score:")
    print(f"    mean={cal_all.mean():.2f}  median={cal_all.median():.2f}  "
          f"std={cal_all.std():.2f}  min={cal_all.min():.2f}  max={cal_all.max():.2f}")
    print()
    print("  Risk level distribution (test set, calibrated):")
    for lvl_name in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        cnt = int((lvl_all == lvl_name).sum())
        pct = cnt / total * 100
        print(f"    {lvl_name:<10}: {cnt:>7,}  ({pct:.2f}%)")

    print()
    print("  Calibration artefacts:")
    print(f"    {CALIB_PKL.relative_to(ROOT)}  (FastAPI pickle)")
    print(f"    {CALIB_JSON.relative_to(ROOT)}  (human-readable JSON)")
    print("=" * 70)


if __name__ == "__main__":
    main()
