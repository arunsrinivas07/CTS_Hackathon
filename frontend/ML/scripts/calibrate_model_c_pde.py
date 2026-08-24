"""
Model C PDE — Risk Score Calibration
======================================
Converts raw IsolationForest decision_function scores into a 0–100
risk score calibrated within meaningful PDE transaction groups.

Calibration formula (consistent with Model B):
    pct_rank   = percentile_of_score(raw_score, reference_array)  # 0–100
    risk_score = (1 - pct_rank / 100) * 100                        # higher = more anomalous

Risk levels:
    CRITICAL : risk_score >= 80
    HIGH     : 60 <= risk_score < 80
    MEDIUM   : 40 <= risk_score < 60
    LOW      : risk_score  < 40

Calibration groups built from TRAINING DATA ONLY (YEAR <= 2022).
Groups evaluated:
    1. Overall PDE population
    2. Year (2015–2022)
    3. Drug category: BRND_GNRC_CD (Brand / Generic)
    4. Pharmacy service type: PHRMCY_SRVC_TYPE_CD (7 types)
    5. Prescriber volume tier: LOW / MID / HIGH (terciles by PRESCRIBER_RX_COUNT)
    6. Beneficiary volume tier: LOW / MID / HIGH (terciles by BENE_PREV_RX_COUNT)

Groups with fewer than MIN_GROUP_SIZE training rows fall back to the
overall reference to prevent unreliable percentile estimates.

The JSON calibration reference is FastAPI-ready: each group stores a
sorted array of raw scores as percentile anchor points (not the raw
array itself, which would be too large) plus the full sorted array is
stored in the companion .pkl file.

Outputs
-------
data/processed/reference/pde_calibration.json     ← percentile anchors, metadata
models/model_c_pde/pde_score_calibration.pkl      ← {group_key: sorted np.ndarray}
data/outputs/model_c_pde_test_scores.csv          ← scored + calibrated test set

Run from project root:
    python scripts/calibrate_model_c_pde.py
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
PDE_FEAT   = ROOT / "data" / "processed" / "pde" / "pde_features.csv"
MODEL_DIR  = ROOT / "models" / "model_c_pde"
REF_DIR    = ROOT / "data" / "processed" / "reference"
OUT_DIR    = ROOT / "data" / "outputs"
REF_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

CALIB_JSON = REF_DIR  / "pde_calibration.json"
CALIB_PKL  = MODEL_DIR / "pde_score_calibration.pkl"
SCORES_CSV = OUT_DIR   / "model_c_pde_test_scores.csv"

# ── constants ─────────────────────────────────────────────────────────────────
TRAIN_MAX_YEAR = 2022
TEST_YEAR      = 2023
MIN_GROUP_SIZE = 1000       # minimum rows to build a group-specific reference
PERCENTILE_ANCHORS = [1, 5, 10, 20, 25, 30, 40, 50, 60, 70, 75, 80, 90, 95, 99]

RISK_LEVELS = [
    (80.0, "CRITICAL"),
    (60.0, "HIGH"),
    (40.0, "MEDIUM"),
    (0.0,  "LOW"),
]

# Prescriber / beneficiary tier boundaries (fitted on training, reused at inference)
# Will be written to JSON so FastAPI can reconstruct group membership
PRESCRIBER_TIER_BOUNDS = (189, 728)    # p33, p66 of PRESCRIBER_RX_COUNT on training
BENE_TIER_BOUNDS       = (38,  136)    # p33, p66 of BENE_PREV_RX_COUNT on training


# ── helpers ───────────────────────────────────────────────────────────────────

def _percentile_rank_vec(values: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """Vectorised percentile rank of each value within reference (sorted)."""
    n = len(reference)
    n_below = np.searchsorted(reference, values, side="left").astype(float)
    n_right = np.searchsorted(reference, values, side="right").astype(float)
    n_equal = n_right - n_below
    pct = (n_below + n_equal / 2.0) / n * 100.0
    return np.clip(pct, 0.0, 100.0)


def _to_risk_score(raw: np.ndarray, reference: np.ndarray) -> np.ndarray:
    pct = _percentile_rank_vec(raw, reference)
    return (1.0 - pct / 100.0) * 100.0


def _assign_risk_level(score: float) -> str:
    for threshold, label in RISK_LEVELS:
        if score >= threshold:
            return label
    return "LOW"


def _assign_risk_vec(scores: np.ndarray) -> np.ndarray:
    levels = np.full(len(scores), "LOW", dtype=object)
    levels[scores >= 40] = "MEDIUM"
    levels[scores >= 60] = "HIGH"
    levels[scores >= 80] = "CRITICAL"
    return levels


def _prescriber_tier(val: float | None,
                     lo: float, hi: float) -> str:
    if val is None or np.isnan(val):
        return "MID"      # fallback for first-prescription rows
    if val <= lo:
        return "LOW"
    if val <= hi:
        return "MID"
    return "HIGH"


def _bene_tier(val: float | None, lo: float, hi: float) -> str:
    if val is None or np.isnan(val):
        return "LOW"      # first fill = new patient = low history
    if val <= lo:
        return "LOW"
    if val <= hi:
        return "MID"
    return "HIGH"


def _percentile_anchors(arr: np.ndarray) -> dict:
    return {
        f"p{p}": round(float(np.percentile(arr, p)), 6)
        for p in PERCENTILE_ANCHORS
    }


def _group_stats(arr: np.ndarray, ref: np.ndarray) -> dict:
    """Summary stats for one group using the appropriate reference."""
    risk = _to_risk_score(arr, ref)
    return {
        "n":                int(len(arr)),
        "raw_min":          round(float(arr.min()), 6),
        "raw_max":          round(float(arr.max()), 6),
        "raw_median":       round(float(np.median(arr)), 6),
        "raw_mean":         round(float(arr.mean()), 6),
        "raw_std":          round(float(arr.std()), 6),
        "raw_percentile_anchors": _percentile_anchors(arr),
        "risk_score_mean":  round(float(risk.mean()), 4),
        "risk_score_median":round(float(np.median(risk)), 4),
        "anomaly_rate_pct": round(float((risk >= 80).mean() * 100), 4),
    }


# ── load model artefacts ──────────────────────────────────────────────────────

def _load_model():
    with open(MODEL_DIR / "isolation_forest.pkl", "rb") as f:
        iso = pickle.load(f)
    with open(MODEL_DIR / "imputer.pkl", "rb") as f:
        imp = pickle.load(f)
    with open(MODEL_DIR / "scaler.pkl", "rb") as f:
        scl = pickle.load(f)
    with open(MODEL_DIR / "feature_columns.pkl", "rb") as f:
        feat = pickle.load(f)
    return iso, imp, scl, feat


def _score_df(df: pd.DataFrame, iso, imp, scl, feat) -> np.ndarray:
    X     = df[feat].values
    X_imp = imp.transform(X)
    X_scl = scl.transform(X_imp)
    return iso.decision_function(X_scl)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    # ── 1. Load model artefacts and PDE features ──────────────────────────
    print("Loading model artefacts …")
    iso, imp, scl, feat = _load_model()

    print("Loading PDE features …")
    df = pd.read_csv(PDE_FEAT, low_memory=False)
    print(f"  {len(df):,} rows")

    train = df[df["YEAR"] <= TRAIN_MAX_YEAR].reset_index(drop=True)
    test  = df[df["YEAR"] == TEST_YEAR].reset_index(drop=True)
    print(f"  Training: {len(train):,}  |  Test: {len(test):,}")

    # ── 2. Score training data (builds calibration reference) ─────────────
    print("\nScoring training data …")
    train["_RAW"] = _score_df(train, iso, imp, scl, feat)
    print(f"  Done. Raw range: [{train['_RAW'].min():.4f}, {train['_RAW'].max():.4f}]")

    # ── 3. Assign group membership columns ────────────────────────────────
    # Prescriber tier
    plo, phi = PRESCRIBER_TIER_BOUNDS
    train["_PRSCR_TIER"] = train["PRESCRIBER_RX_COUNT"].apply(
        lambda v: _prescriber_tier(v, plo, phi)
    )
    # Beneficiary tier
    blo, bhi = BENE_TIER_BOUNDS
    train["_BENE_TIER"] = train["BENE_PREV_RX_COUNT"].apply(
        lambda v: _bene_tier(v, blo, bhi)
    )

    # ── 4. Build calibration reference dict ───────────────────────────────
    print("\nBuilding calibration reference arrays …")
    calibration_ref: dict[str, np.ndarray] = {}
    calib_meta: dict = {}

    # Overall reference (always built — used as fallback)
    overall_raw = np.sort(train["_RAW"].values)
    calibration_ref["overall"] = overall_raw
    calib_meta["overall"] = _group_stats(overall_raw, overall_raw)
    calib_meta["overall"]["description"] = "All PDE training transactions"
    print(f"  overall      : {len(overall_raw):>7,} refs")

    # ── Group 1: Year ─────────────────────────────────────────────────────
    calib_meta["by_year"] = {}
    for yr, grp in train.groupby("YEAR"):
        key = str(int(yr))
        raw_sorted = np.sort(grp["_RAW"].values)
        if len(raw_sorted) >= MIN_GROUP_SIZE:
            calibration_ref[f"year__{key}"] = raw_sorted
            calib_meta["by_year"][key] = _group_stats(raw_sorted, raw_sorted)
            calib_meta["by_year"][key]["description"] = f"Year {yr} PDE transactions"
        else:
            calib_meta["by_year"][key] = {"n": len(raw_sorted), "note": "too small, uses overall fallback"}
        print(f"  year {yr}  : {len(raw_sorted):>7,} refs")

    # ── Group 2: Drug type (Brand vs Generic) ─────────────────────────────
    calib_meta["by_drug_type"] = {}
    for dt, grp in train.groupby("BRND_GNRC_CD"):
        key = str(dt)
        raw_sorted = np.sort(grp["_RAW"].values)
        ref_key = f"drug_type__{key}"
        label = "Brand" if dt == "B" else "Generic"
        if len(raw_sorted) >= MIN_GROUP_SIZE:
            calibration_ref[ref_key] = raw_sorted
            calib_meta["by_drug_type"][key] = _group_stats(raw_sorted, raw_sorted)
            calib_meta["by_drug_type"][key]["description"] = f"{label} drug PDE transactions"
        else:
            calib_meta["by_drug_type"][key] = {"n": len(raw_sorted), "note": "fallback to overall"}
        print(f"  drug_type {key} ({label}): {len(raw_sorted):>7,} refs")

    # ── Group 3: Pharmacy service type ────────────────────────────────────
    PHRMCY_LABELS = {
        1: "Community/Retail", 2: "Compounding", 3: "Home Infusion",
        4: "Institutional", 5: "Long-Term Care", 6: "Mail Order",
        7: "Specialty",
    }
    calib_meta["by_pharmacy_type"] = {}
    for pt, grp in train.groupby("PHRMCY_SRVC_TYPE_CD"):
        key = str(int(pt))
        raw_sorted = np.sort(grp["_RAW"].values)
        ref_key = f"pharmacy_type__{key}"
        label = PHRMCY_LABELS.get(int(pt), f"Type {pt}")
        if len(raw_sorted) >= MIN_GROUP_SIZE:
            calibration_ref[ref_key] = raw_sorted
            calib_meta["by_pharmacy_type"][key] = _group_stats(raw_sorted, raw_sorted)
            calib_meta["by_pharmacy_type"][key]["description"] = f"{label} pharmacy transactions"
        else:
            calib_meta["by_pharmacy_type"][key] = {"n": len(raw_sorted), "note": "fallback to overall"}
        print(f"  pharmacy_type {key} ({label}): {len(raw_sorted):>7,} refs")

    # ── Group 4: Prescriber volume tier ───────────────────────────────────
    calib_meta["by_prescriber_tier"] = {}
    for tier, grp in train.groupby("_PRSCR_TIER"):
        key = str(tier)
        raw_sorted = np.sort(grp["_RAW"].values)
        ref_key = f"prescriber_tier__{key}"
        if len(raw_sorted) >= MIN_GROUP_SIZE:
            calibration_ref[ref_key] = raw_sorted
            calib_meta["by_prescriber_tier"][key] = _group_stats(raw_sorted, raw_sorted)
            calib_meta["by_prescriber_tier"][key]["description"] = (
                f"Prescriber volume tier {key} "
                f"(LOW: ≤{plo} Rx, MID: {plo}–{phi} Rx, HIGH: >{phi} Rx)"
            )
        else:
            calib_meta["by_prescriber_tier"][key] = {"n": len(raw_sorted), "note": "fallback to overall"}
        print(f"  prescriber_tier {key}: {len(raw_sorted):>7,} refs")

    # ── Group 5: Beneficiary volume tier ──────────────────────────────────
    calib_meta["by_beneficiary_tier"] = {}
    for tier, grp in train.groupby("_BENE_TIER"):
        key = str(tier)
        raw_sorted = np.sort(grp["_RAW"].values)
        ref_key = f"bene_tier__{key}"
        if len(raw_sorted) >= MIN_GROUP_SIZE:
            calibration_ref[ref_key] = raw_sorted
            calib_meta["by_beneficiary_tier"][key] = _group_stats(raw_sorted, raw_sorted)
            calib_meta["by_beneficiary_tier"][key]["description"] = (
                f"Beneficiary history tier {key} "
                f"(LOW: ≤{blo} prior Rx, MID: {blo}–{bhi} prior Rx, HIGH: >{bhi} prior Rx)"
            )
        else:
            calib_meta["by_beneficiary_tier"][key] = {"n": len(raw_sorted), "note": "fallback to overall"}
        print(f"  bene_tier {key}: {len(raw_sorted):>7,} refs")

    # ── 5. Save calibration.pkl ───────────────────────────────────────────
    with open(CALIB_PKL, "wb") as f:
        pickle.dump(calibration_ref, f, protocol=5)
    size_kb = CALIB_PKL.stat().st_size / 1024
    print(f"\n  ✓ pde_score_calibration.pkl saved ({size_kb:,.0f} KB)")

    # ── 6. Build and save calibration.json ───────────────────────────────
    calib_json = {
        "_metadata": {
            "description": (
                "PDE-specific risk calibration for Model C. "
                "Built from training data (YEAR <= 2022) only. "
                "Never recompute from live incoming transactions."
            ),
            "calibration_formula": (
                "pct_rank = percentile_of_score(raw_score, reference_array)\n"
                "risk_score = (1 - pct_rank / 100) * 100   # 0–100, higher=more anomalous"
            ),
            "risk_levels": {
                "CRITICAL": "risk_score >= 80",
                "HIGH":     "60 <= risk_score < 80",
                "MEDIUM":   "40 <= risk_score < 60",
                "LOW":      "risk_score < 40",
            },
            "training_period":   "2015–2022",
            "test_period":       "2023 (excluded from calibration)",
            "min_group_size":    MIN_GROUP_SIZE,
            "fallback_group":    "overall",
            "groups_built":      sorted(calibration_ref.keys()),
            "percentile_anchors": PERCENTILE_ANCHORS,
            "group_membership_rules": {
                "prescriber_tier": {
                    "LOW":  f"PRESCRIBER_RX_COUNT <= {plo}",
                    "MID":  f"{plo} < PRESCRIBER_RX_COUNT <= {phi}",
                    "HIGH": f"PRESCRIBER_RX_COUNT > {phi}",
                    "null": "assign MID (first Rx)",
                    "boundaries": list(PRESCRIBER_TIER_BOUNDS),
                },
                "bene_tier": {
                    "LOW":  f"BENE_PREV_RX_COUNT <= {blo} or null (new patient)",
                    "MID":  f"{blo} < BENE_PREV_RX_COUNT <= {bhi}",
                    "HIGH": f"BENE_PREV_RX_COUNT > {bhi}",
                    "null": "assign LOW (first fill)",
                    "boundaries": list(BENE_TIER_BOUNDS),
                },
                "drug_type": {
                    "B": "Brand-name drug",
                    "G": "Generic drug",
                },
                "pharmacy_type": PHRMCY_LABELS,
            },
            "pkl_file": "models/model_c_pde/pde_score_calibration.pkl",
        },
        "groups": calib_meta,
    }

    with open(CALIB_JSON, "w", encoding="utf-8") as f:
        json.dump(calib_json, f, indent=2)
    size_kb = CALIB_JSON.stat().st_size / 1024
    print(f"  ✓ pde_calibration.json saved ({size_kb:.1f} KB)")

    # ── 7. Apply overall calibration to test set and save ─────────────────
    print("\nScoring and calibrating test set (overall reference) …")
    test["_RAW"] = _score_df(test, iso, imp, scl, feat)

    # Overall calibration
    test["RISK_SCORE_OVERALL"] = _to_risk_score(
        test["_RAW"].values, calibration_ref["overall"]
    )

    # Per-year calibration (use year ref if available, else overall)
    test["RISK_SCORE_BY_YEAR"] = test.apply(
        lambda r: float(_to_risk_score(
            np.array([r["_RAW"]]),
            calibration_ref.get(f"year__{int(r['YEAR'])}", calibration_ref["overall"])
        )[0]),
        axis=1,
    )

    # Drug type calibration
    test["RISK_SCORE_BY_DRUG_TYPE"] = test.apply(
        lambda r: float(_to_risk_score(
            np.array([r["_RAW"]]),
            calibration_ref.get(f"drug_type__{r['BRND_GNRC_CD']}", calibration_ref["overall"])
        )[0]),
        axis=1,
    )

    # Prescriber tier
    test["_PRSCR_TIER"] = test["PRESCRIBER_RX_COUNT"].apply(
        lambda v: _prescriber_tier(v, plo, phi)
    )
    test["RISK_SCORE_BY_PRESCRIBER_TIER"] = test.apply(
        lambda r: float(_to_risk_score(
            np.array([r["_RAW"]]),
            calibration_ref.get(f"prescriber_tier__{r['_PRSCR_TIER']}", calibration_ref["overall"])
        )[0]),
        axis=1,
    )

    # Beneficiary tier
    test["_BENE_TIER"] = test["BENE_PREV_RX_COUNT"].apply(
        lambda v: _bene_tier(v, blo, bhi)
    )
    test["RISK_SCORE_BY_BENE_TIER"] = test.apply(
        lambda r: float(_to_risk_score(
            np.array([r["_RAW"]]),
            calibration_ref.get(f"bene_tier__{r['_BENE_TIER']}", calibration_ref["overall"])
        )[0]),
        axis=1,
    )

    # Primary risk score = overall; risk level from that
    test["RISK_SCORE"]   = test["RISK_SCORE_OVERALL"]
    test["RISK_LEVEL"]   = _assign_risk_vec(test["RISK_SCORE"].values)
    test["ANOMALY_PRED"] = iso.predict(
        scl.transform(imp.transform(test[feat].values))
    )

    # Validation
    assert int(test["RISK_SCORE"].isna().sum()) == 0, "NaN risk scores!"
    assert bool((test["RISK_SCORE"] >= 0).all() and (test["RISK_SCORE"] <= 100).all()), "Out-of-range!"
    print(f"  NaN scores: 0  ✓")
    print(f"  Range [0,100]: ✓")

    # Save (drop internal helper cols)
    drop_internal = ["_RAW", "_PRSCR_TIER", "_BENE_TIER"]
    test_out = test.drop(columns=[c for c in drop_internal if c in test.columns])
    test_out.to_csv(SCORES_CSV, index=False)
    print(f"  ✓ Scored test set → {SCORES_CSV.relative_to(ROOT)}")

    # ── 8. Summary report ─────────────────────────────────────────────────
    print()
    print("=" * 68)
    print("  MODEL C PDE CALIBRATION SUMMARY")
    print("=" * 68)
    print(f"  Calibration reference built from: {len(train):,} training rows (YEAR <= {TRAIN_MAX_YEAR})")
    print(f"  Calibration groups built        : {len(calibration_ref)}")
    print(f"  Test rows scored                : {len(test):,}")
    print()
    print(f"  {'Group':<35} {'n_ref':>8}  {'risk_mean':>10}  {'CRIT%':>7}")
    print("  " + "-" * 65)
    for key, ref in sorted(calibration_ref.items()):
        mask = test_out.apply(lambda _: True, axis=1)  # all rows for overall
        if key == "overall":
            rs = test_out["RISK_SCORE_OVERALL"].values
        else:
            continue   # individual group stats shown below
        crit_pct = (rs >= 80).mean() * 100
        print(f"  {'overall (primary)':<35} {len(ref):>8,}  "
              f"{rs.mean():>10.2f}  {crit_pct:>6.1f}%")

    print()
    print("  Risk level distribution on test set (overall calibration):")
    for lvl in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        cnt = int((test_out["RISK_LEVEL"] == lvl).sum())
        pct = cnt / len(test_out) * 100
        print(f"    {lvl:<10}: {cnt:>7,}  ({pct:.2f}%)")

    print()
    print("  Risk score comparison across calibration dimensions:")
    print(f"  {'Dimension':<30} {'mean':>7}  {'median':>8}  {'CRIT%':>7}")
    print("  " + "-" * 58)
    for col, label in [
        ("RISK_SCORE_OVERALL",           "Overall"),
        ("RISK_SCORE_BY_YEAR",           "By year"),
        ("RISK_SCORE_BY_DRUG_TYPE",      "By drug type"),
        ("RISK_SCORE_BY_PRESCRIBER_TIER","By prescriber tier"),
        ("RISK_SCORE_BY_BENE_TIER",      "By beneficiary tier"),
    ]:
        rs = test_out[col].dropna()
        crit_pct = (rs >= 80).mean() * 100
        print(f"  {label:<30} {rs.mean():>7.2f}  {rs.median():>8.2f}  {crit_pct:>6.1f}%")

    print()
    print("  Calibration artefacts:")
    print(f"    {CALIB_JSON.relative_to(ROOT)}")
    print(f"    {CALIB_PKL.relative_to(ROOT)}")
    print("=" * 68)


if __name__ == "__main__":
    main()
