"""
Model B — Temporal Test Set Validation
=======================================
Loads the frozen artefacts from models/model_b_claim/ and scores the
untouched 2023 test set.  No artefact is modified; all transforms use
the training-fitted imputer and scaler.

Checks performed
----------------
  V1  No NaN scores after preprocessing
  V2  Decision function values are finite
  V3  Risk scores are in [0, 100]
  V4  All seven claim types present in test predictions
  V5  Zero CLAIM_ID overlap between training and test populations
  V6  Test set contains only future year (2023) — no training years
  V7  Peer stats were built from training period only (metadata check)
  V8  Score coverage — no rows skipped
  V9  Anomaly rate is non-trivial (> 0% and < 100%)

Outputs
-------
data/outputs/model_b_validation_report.txt   (full text report)
data/outputs/model_b_test_scores.csv         (scored test rows)

Run from project root:
    python scripts/validate_model_b.py
"""

import json
import pickle
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── paths ─────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).resolve().parent.parent
MODEL_DIR  = ROOT / "models" / "model_b_claim"
TEST_CSV   = ROOT / "data" / "processed" / "medical" / "test_medical.csv"
TRAIN_SAMP = ROOT / "data" / "processed" / "medical" / "model_b_training_sample.csv"
HIST_CSV   = ROOT / "data" / "processed" / "medical" / "claims_with_beneficiary_history.csv"
OUT_DIR    = ROOT / "data" / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

REPORT_TXT  = OUT_DIR / "model_b_validation_report.txt"
SCORES_CSV  = OUT_DIR / "model_b_test_scores.csv"

# Risk level thresholds (percentile of anomaly score, higher = more anomalous)
RISK_THRESHOLDS = {
    "CRITICAL": 95,
    "HIGH":     85,
    "MEDIUM":   70,
    "LOW":       0,
}


# ── load artefacts ────────────────────────────────────────────────────────────

def _load_pkl(path: Path):
    with open(path, "rb") as f:
        return pickle.load(f)


# ── score normalisation ───────────────────────────────────────────────────────

def _normalise_to_risk_score(raw_scores: np.ndarray) -> np.ndarray:
    """
    Convert IsolationForest decision_function scores to a 0–100 risk score.

    IsolationForest.decision_function returns:
        negative  → anomalous  (more negative = more anomalous)
        positive  → normal

    We flip and min-max normalise to [0, 100] so that:
        100 = most anomalous
        0   = most normal
    """
    flipped = -raw_scores                    # higher = more anomalous
    lo, hi  = flipped.min(), flipped.max()
    if hi == lo:
        return np.full_like(flipped, 50.0)
    return (flipped - lo) / (hi - lo) * 100.0


def _assign_risk_level(scores: pd.Series) -> pd.Series:
    """Assign CRITICAL / HIGH / MEDIUM / LOW based on percentile thresholds."""
    p95 = np.percentile(scores, RISK_THRESHOLDS["CRITICAL"])
    p85 = np.percentile(scores, RISK_THRESHOLDS["HIGH"])
    p70 = np.percentile(scores, RISK_THRESHOLDS["MEDIUM"])

    levels = pd.Series("LOW", index=scores.index, dtype=object)
    levels[scores >= p70] = "MEDIUM"
    levels[scores >= p85] = "HIGH"
    levels[scores >= p95] = "CRITICAL"
    return levels


# ── distribution stats helper ─────────────────────────────────────────────────

def _dist(arr, label="") -> dict:
    a = np.asarray(arr, dtype=float)
    a = a[~np.isnan(a)]
    return {
        "label":  label,
        "n":      int(len(a)),
        "mean":   round(float(a.mean()),              4),
        "std":    round(float(a.std()),               4),
        "min":    round(float(a.min()),               4),
        "p5":     round(float(np.percentile(a,  5)), 4),
        "p25":    round(float(np.percentile(a, 25)), 4),
        "median": round(float(np.median(a)),          4),
        "p75":    round(float(np.percentile(a, 75)), 4),
        "p95":    round(float(np.percentile(a, 95)), 4),
        "max":    round(float(a.max()),               4),
    }


def _fmt_dist(d: dict) -> str:
    return (f"  n={d['n']:,}  mean={d['mean']:.3f}  std={d['std']:.3f}  "
            f"min={d['min']:.3f}  p25={d['p25']:.3f}  median={d['median']:.3f}  "
            f"p75={d['p75']:.3f}  p95={d['p95']:.3f}  max={d['max']:.3f}")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    lines = []
    checks: dict[str, bool] = {}

    def section(title: str):
        lines.append("")
        lines.append("─" * 70)
        lines.append(f"  {title}")
        lines.append("─" * 70)

    lines.append("=" * 70)
    lines.append("  MODEL B — TEMPORAL TEST SET VALIDATION REPORT")
    lines.append("=" * 70)

    # ── 1. Load artefacts ─────────────────────────────────────────────────
    section("1. ARTEFACT LOADING")
    iso_forest   = _load_pkl(MODEL_DIR / "isolation_forest.pkl")
    imputer      = _load_pkl(MODEL_DIR / "imputer.pkl")
    scaler       = _load_pkl(MODEL_DIR / "scaler.pkl")
    feature_cols = _load_pkl(MODEL_DIR / "feature_columns.pkl")
    with open(MODEL_DIR / "metadata.json", encoding="utf-8") as f:
        meta = json.load(f)

    lines.append(f"  IsolationForest    : n_estimators={iso_forest.n_estimators}  "
                 f"contamination={iso_forest.contamination}  "
                 f"random_state={iso_forest.random_state}")
    lines.append(f"  SimpleImputer      : strategy={imputer.strategy}")
    lines.append(f"  StandardScaler     : with_mean={scaler.with_mean}  with_std={scaler.with_std}")
    lines.append(f"  Feature columns    : {len(feature_cols)}")
    lines.append(f"  Model trained at   : {meta.get('trained_at','?')}")
    lines.append(f"  Training rows      : {meta.get('training_row_count',0):,}")

    # ── 2. Load test set ──────────────────────────────────────────────────
    section("2. TEST SET LOADING")
    test = pd.read_csv(TEST_CSV, low_memory=False)
    lines.append(f"  Test rows          : {len(test):,}")
    lines.append(f"  Test columns       : {len(test.columns)}")
    test_years = sorted(test["YEAR"].unique().astype(int).tolist())
    lines.append(f"  Test years         : {test_years}")

    # Reconstruct claim type
    ohe_cols = [c for c in test.columns if c.startswith("CLMTYPE_")]
    test["_CLAIM_TYPE"] = (
        test[ohe_cols].idxmax(axis=1).str.replace("CLMTYPE_", "", regex=False)
    )
    test_claim_types = sorted(test["_CLAIM_TYPE"].unique().tolist())
    lines.append(f"  Claim types found  : {test_claim_types}")

    # ── V6: test contains only future years ───────────────────────────────
    train_years = meta.get("training_years", [])
    year_overlap = set(test_years) & set(train_years)
    checks["V6_no_training_years_in_test"] = len(year_overlap) == 0
    lines.append(f"\n  [V6] Test years {test_years} ∩ training years {train_years} "
                 f"= {sorted(year_overlap)}  "
                 f"{'✓ PASS' if checks['V6_no_training_years_in_test'] else '✗ FAIL'}")

    # ── V7: peer stats period check ───────────────────────────────────────
    peer_period = meta.get("leakage_prevention", {}).get("peer_stats_period", "")
    test_data_loaded = meta.get("leakage_prevention", {}).get("test_data_loaded", True)
    checks["V7_peer_stats_training_only"] = (not test_data_loaded) and ("2023" not in peer_period or "excluded" in peer_period.lower())
    lines.append(f"  [V7] test_data_loaded in training: {test_data_loaded}  "
                 f"peer_stats_period='{peer_period}'  "
                 f"{'✓ PASS' if checks['V7_peer_stats_training_only'] else '✗ FAIL'}")

    # ── V5: claim ID overlap check ────────────────────────────────────────
    section("3. TRAINING / TEST POPULATION OVERLAP CHECK")
    hist = pd.read_csv(HIST_CSV, usecols=["CLAIM_ID", "YEAR"], low_memory=False)
    train_ids = set(hist[hist["YEAR"] <= 2022]["CLAIM_ID"].unique())
    test_ids  = set(hist[hist["YEAR"] == 2023]["CLAIM_ID"].unique())
    id_overlap = train_ids & test_ids
    checks["V5_no_id_overlap"] = len(id_overlap) == 0
    lines.append(f"  Training CLAIM_IDs (YEAR<=2022) : {len(train_ids):,}")
    lines.append(f"  Test CLAIM_IDs     (YEAR==2023)  : {len(test_ids):,}")
    lines.append(f"  Overlapping IDs                  : {len(id_overlap)}")
    lines.append(f"  [V5] No ID overlap  "
                 f"{'✓ PASS' if checks['V5_no_id_overlap'] else '✗ FAIL'}")

    # ── 3. Score the test set ─────────────────────────────────────────────
    section("4. SCORING")
    missing_feat = [c for c in feature_cols if c not in test.columns]
    if missing_feat:
        raise ValueError(f"Test set missing feature columns: {missing_feat}")
    lines.append(f"  All {len(feature_cols)} feature columns present ✓")

    X_test = test[feature_cols].copy()
    null_before = int(X_test.isnull().sum().sum())
    lines.append(f"  Nulls before imputation  : {null_before:,}")

    # Apply training-fitted transforms (no refitting)
    X_imputed = imputer.transform(X_test.values)
    null_after = int(np.isnan(X_imputed).sum())
    lines.append(f"  Nulls after imputation   : {null_after}")

    X_scaled = scaler.transform(X_imputed)
    lines.append(f"  Scaling applied          : ✓")

    # Decision function (raw anomaly scores)
    raw_scores = iso_forest.decision_function(X_scaled)
    predictions = iso_forest.predict(X_scaled)          # +1 normal / -1 anomaly
    risk_scores = _normalise_to_risk_score(raw_scores)

    # ── V1: no NaN scores ─────────────────────────────────────────────────
    checks["V1_no_nan_scores"] = int(np.isnan(risk_scores).sum()) == 0
    lines.append(f"\n  [V1] NaN risk scores     : {np.isnan(risk_scores).sum()}  "
                 f"{'✓ PASS' if checks['V1_no_nan_scores'] else '✗ FAIL'}")

    # ── V2: finite decision function ──────────────────────────────────────
    checks["V2_finite_decision_fn"] = bool(np.all(np.isfinite(raw_scores)))
    lines.append(f"  [V2] Infinite raw scores : {int(~np.isfinite(raw_scores)).sum() if not checks['V2_finite_decision_fn'] else 0}  "
                 f"{'✓ PASS' if checks['V2_finite_decision_fn'] else '✗ FAIL'}")

    # ── V3: scores in [0, 100] ────────────────────────────────────────────
    checks["V3_scores_in_range"] = bool(
        np.all(risk_scores >= 0) and np.all(risk_scores <= 100)
    )
    lines.append(f"  [V3] Scores in [0,100]   : min={risk_scores.min():.4f}  max={risk_scores.max():.4f}  "
                 f"{'✓ PASS' if checks['V3_scores_in_range'] else '✗ FAIL'}")

    # ── V8: coverage ──────────────────────────────────────────────────────
    checks["V8_full_coverage"] = len(risk_scores) == len(test)
    lines.append(f"  [V8] Score coverage      : {len(risk_scores):,} / {len(test):,}  "
                 f"{'✓ PASS' if checks['V8_full_coverage'] else '✗ FAIL'}")

    # ── Attach scores to test frame ───────────────────────────────────────
    test["RAW_DECISION_SCORE"] = raw_scores
    test["ANOMALY_PREDICTION"]  = predictions        # +1 / -1
    test["RISK_SCORE"]          = risk_scores
    test["RISK_LEVEL"]          = _assign_risk_level(pd.Series(risk_scores))

    n_anomalies = int((predictions == -1).sum())
    n_normal    = int((predictions ==  1).sum())
    anomaly_rate = n_anomalies / len(test) * 100

    # ── V9: non-trivial anomaly rate ──────────────────────────────────────
    checks["V9_nontrivial_anomaly_rate"] = 0 < anomaly_rate < 100
    lines.append(f"  [V9] Anomaly rate        : {anomaly_rate:.2f}%  "
                 f"({'✓ PASS' if checks['V9_nontrivial_anomaly_rate'] else '✗ FAIL'})")

    # ── 5. Distribution summaries ─────────────────────────────────────────
    section("5. SCORE DISTRIBUTIONS")
    lines.append("  Raw decision function scores:")
    lines.append(_fmt_dist(_dist(raw_scores, "raw")))
    lines.append("")
    lines.append("  Risk scores (0–100, higher = more anomalous):")
    lines.append(_fmt_dist(_dist(risk_scores, "risk")))
    lines.append("")
    lines.append("  Anomaly prediction counts:")
    lines.append(f"    Normal    (+1) : {n_normal:>8,}  ({100 - anomaly_rate:.2f}%)")
    lines.append(f"    Anomalous (-1) : {n_anomalies:>8,}  ({anomaly_rate:.2f}%)")
    lines.append("")
    lines.append("  Risk level distribution:")
    for lvl in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        cnt = int((test["RISK_LEVEL"] == lvl).sum())
        pct = cnt / len(test) * 100
        lines.append(f"    {lvl:<10}: {cnt:>8,}  ({pct:.2f}%)")

    # ── 6. Score distribution by CLAIM_TYPE ───────────────────────────────
    section("6. SCORE DISTRIBUTION BY CLAIM_TYPE")
    expected_types = set(meta.get("claim_types", []))
    found_types    = set(test_claim_types)
    checks["V4_all_claim_types"] = expected_types == found_types
    lines.append(f"  Expected types : {sorted(expected_types)}")
    lines.append(f"  Found types    : {sorted(found_types)}")
    lines.append(f"  [V4] All 7 claim types present  "
                 f"{'✓ PASS' if checks['V4_all_claim_types'] else '✗ FAIL'}")
    lines.append("")
    lines.append(f"  {'CLAIM_TYPE':<13} {'n':>7}  {'anomaly%':>9}  "
                 f"{'mean_risk':>10}  {'med_risk':>9}  {'p95_risk':>9}")
    lines.append("  " + "-" * 62)

    ct_stability: dict[str, float] = {}
    for ct in sorted(test_claim_types):
        mask  = test["_CLAIM_TYPE"] == ct
        ct_df = test[mask]
        ct_an = int((ct_df["ANOMALY_PREDICTION"] == -1).sum())
        ct_ar = ct_an / len(ct_df) * 100
        rs    = ct_df["RISK_SCORE"].values
        ct_stability[ct] = float(rs.std())
        lines.append(
            f"  {ct:<13} {len(ct_df):>7,}  {ct_ar:>8.2f}%  "
            f"{rs.mean():>10.3f}  {np.median(rs):>9.3f}  "
            f"{np.percentile(rs, 95):>9.3f}"
        )

    # ── 7. Score distribution by YEAR ─────────────────────────────────────
    section("7. SCORE DISTRIBUTION BY YEAR")
    lines.append(f"  {'YEAR':>6}  {'n':>7}  {'anomaly%':>9}  "
                 f"{'mean_risk':>10}  {'med_risk':>9}  {'p95_risk':>9}")
    lines.append("  " + "-" * 52)
    for yr in sorted(test["YEAR"].unique()):
        mask = test["YEAR"] == yr
        yr_df = test[mask]
        yr_an = int((yr_df["ANOMALY_PREDICTION"] == -1).sum())
        yr_ar = yr_an / len(yr_df) * 100
        rs    = yr_df["RISK_SCORE"].values
        lines.append(
            f"  {int(yr):>6}  {len(yr_df):>7,}  {yr_ar:>8.2f}%  "
            f"{rs.mean():>10.3f}  {np.median(rs):>9.3f}  "
            f"{np.percentile(rs, 95):>9.3f}"
        )

    # ── 8. Stability across claim types ───────────────────────────────────
    section("8. STABILITY ACROSS CLAIM TYPES")
    lines.append(f"  (Score standard deviation per claim type — lower = more stable)")
    lines.append(f"  {'CLAIM_TYPE':<13}  {'score_std':>10}")
    lines.append("  " + "-" * 28)
    max_std = max(ct_stability.values()) if ct_stability else 0
    for ct, std in sorted(ct_stability.items(), key=lambda x: -x[1]):
        bar = "█" * int(std / max_std * 20) if max_std > 0 else ""
        lines.append(f"  {ct:<13}  {std:>10.4f}  {bar}")

    # ── 9. Top anomalous claims ───────────────────────────────────────────
    section("9. TOP 20 ANOMALOUS CLAIMS")
    top20 = (
        test.nlargest(20, "RISK_SCORE")[
            ["_CLAIM_TYPE", "YEAR", "CLM_PMT_AMT", "CLM_TOT_CHRG_AMT",
             "DIAG_COUNT", "PROC_COUNT", "RISK_SCORE", "RISK_LEVEL",
             "RAW_DECISION_SCORE"]
        ]
    )
    lines.append(
        f"  {'CLAIM_TYPE':<13} {'YEAR':>5} {'PAYMENT':>10} {'CHARGE':>10} "
        f"{'DIAG':>5} {'PROC':>5} {'RISK_SCORE':>11} {'LEVEL':>9}"
    )
    lines.append("  " + "-" * 75)
    for _, row in top20.iterrows():
        lines.append(
            f"  {row['_CLAIM_TYPE']:<13} {int(row['YEAR']):>5} "
            f"{row['CLM_PMT_AMT']:>10.2f} {row['CLM_TOT_CHRG_AMT']:>10.2f} "
            f"{int(row['DIAG_COUNT']) if pd.notna(row['DIAG_COUNT']) else '?':>5} "
            f"{int(row['PROC_COUNT']) if pd.notna(row['PROC_COUNT']) else '?':>5} "
            f"{row['RISK_SCORE']:>11.3f} {row['RISK_LEVEL']:>9}"
        )

    # ── 10. Validation summary ────────────────────────────────────────────
    section("10. VALIDATION SUMMARY")
    all_pass = all(checks.values())
    for check_id, passed in sorted(checks.items()):
        lines.append(f"  [{check_id}]  {'✓ PASS' if passed else '✗ FAIL'}")
    lines.append("")
    lines.append("=" * 70)
    verdict = "ALL CHECKS PASSED ✓" if all_pass else "SOME CHECKS FAILED — REVIEW REQUIRED ✗"
    lines.append(f"  VERDICT: {verdict}")
    lines.append("=" * 70)

    # ── 11. Save outputs ──────────────────────────────────────────────────
    report_text = "\n".join(lines)
    REPORT_TXT.write_text(report_text, encoding="utf-8")
    print(f"✓ Report saved  → {REPORT_TXT.relative_to(ROOT)}")

    # Save scored test rows (drop internal helper col)
    test_out = test.drop(columns=["_CLAIM_TYPE"])
    test_out.to_csv(SCORES_CSV, index=False)
    print(f"✓ Scores saved  → {SCORES_CSV.relative_to(ROOT)}")
    print(f"  {len(test_out):,} rows  |  columns: {list(test_out.columns[-4:])}")

    # Print report to console
    print()
    print(report_text)


if __name__ == "__main__":
    main()
