"""
Model C — PDE Anomaly Detection — Training
==========================================
Completely separate from Model B (medical claims).
Uses only data/processed/pde/pde_features.csv.

Pipeline:
    SimpleImputer(strategy="median")
    → StandardScaler()
    → IsolationForest(n_estimators=300, contamination="auto",
                      random_state=42, n_jobs=-1)

Temporal split:
    Training : YEAR <= 2022   (501,190 rows)
    Test     : YEAR == 2023   (14,330 rows)   ← never touched during training

All three pipeline steps are fitted on training data ONLY.

Outputs
-------
models/model_c_pde/
    isolation_forest.pkl
    imputer.pkl
    scaler.pkl
    feature_columns.pkl
    metadata.json

Run from project root:
    python scripts/train_model_c_pde.py
"""

import json
import pickle
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

# ── paths ─────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).resolve().parent.parent
PDE_FEAT    = ROOT / "data" / "processed" / "pde" / "pde_features.csv"
MODEL_DIR   = ROOT / "models" / "model_c_pde"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# ── hyperparameters ───────────────────────────────────────────────────────────
RANDOM_SEED       = 42
N_ESTIMATORS      = 300
CONTAMINATION     = "auto"
TRAIN_MAX_YEAR    = 2022
TEST_YEAR         = 2023

# ── feature columns (excludes raw identifiers, strings, dates) ───────────────
# These are the 32 numeric feature columns produced by build_pde_features.py
FEATURE_COLS = [
    # Temporal
    "YEAR",
    # Transaction amounts (pass-through)
    "QTY_DSPNSD_NUM", "DAYS_SUPLY_NUM", "FILL_NUM",
    "TOT_RX_CST_AMT", "PTNT_PAY_AMT",
    "CVRD_D_PLAN_PD_AMT", "NCVRD_PLAN_PD_AMT",
    "GDC_BLW_OOPT_AMT", "GDC_ABV_OOPT_AMT",
    "OTHR_TROOP_AMT", "LICS_AMT", "PLRO_AMT",
    # Derived transaction features
    "COST_PER_UNIT", "COST_PER_DAY",
    "PATIENT_PAYMENT_RATIO", "PLAN_PAYMENT_RATIO",
    "QUANTITY_PER_DAY", "DAYS_SUPPLY", "REFILL_FREQUENCY",
    # Beneficiary history (strictly prior rows only)
    "BENE_PREV_RX_COUNT", "BENE_PREV_RX_COST",
    "BENE_PREV_AVG_RX_COST", "BENE_PREV_MAX_RX_COST",
    "BENE_RX_30D", "BENE_RX_COST_30D",
    "BENE_RX_90D", "BENE_RX_COST_90D",
    # Prescriber history (strictly prior rows only)
    "PRESCRIBER_RX_COUNT", "PRESCRIBER_AVG_RX_COST",
    "PRESCRIBER_MAX_RX_COST", "PRESCRIBER_UNIQUE_BENEFICIARIES",
]


def _save_pkl(obj, path: Path, label: str) -> None:
    with open(path, "wb") as f:
        pickle.dump(obj, f, protocol=5)
    size_kb = path.stat().st_size / 1024
    print(f"  ✓ {label:<30s} → {path.name}  ({size_kb:,.0f} KB)")


def main():
    t_start = time.perf_counter()

    # ── 1. Load features ──────────────────────────────────────────────────
    print("Loading PDE features …")
    df = pd.read_csv(PDE_FEAT, low_memory=False)
    print(f"  {len(df):,} rows × {len(df.columns)} columns")

    # Verify all feature columns exist
    missing = [c for c in FEATURE_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing feature columns: {missing}")
    print(f"  All {len(FEATURE_COLS)} feature columns present ✓")

    # ── 2. Temporal split ─────────────────────────────────────────────────
    train_df = df[df["YEAR"] <= TRAIN_MAX_YEAR].reset_index(drop=True)
    test_df  = df[df["YEAR"] == TEST_YEAR].reset_index(drop=True)

    train_years = sorted(train_df["YEAR"].unique().astype(int).tolist())
    test_years  = sorted(test_df["YEAR"].unique().astype(int).tolist())

    print(f"\n  Training rows (YEAR <= {TRAIN_MAX_YEAR}): {len(train_df):,}")
    print(f"  Test rows     (YEAR == {TEST_YEAR}):      {len(test_df):,}")
    print(f"  Split ratio  : {len(train_df)/len(df)*100:.1f}% / {len(test_df)/len(df)*100:.1f}%")

    # Verify no test-year data in training
    assert train_df["YEAR"].max() <= TRAIN_MAX_YEAR, "Training data contains test-period rows!"
    assert test_df["YEAR"].min()  == TEST_YEAR,      "Test set does not start at expected year!"
    print(f"  Temporal boundary verified ✓")

    # ── 3. Extract feature matrix (training only) ─────────────────────────
    X_train = train_df[FEATURE_COLS].copy()
    print(f"\n  Feature matrix shape: {X_train.shape}")

    null_pct = X_train.isnull().mean().mul(100)
    cols_with_nulls = null_pct[null_pct > 0]
    print(f"  Columns with nulls: {len(cols_with_nulls)}")
    for col, pct in cols_with_nulls.sort_values(ascending=False).items():
        print(f"    {col:<40s}: {pct:.1f}%")

    # ── 4. Fit SimpleImputer on training data ─────────────────────────────
    print(f"\nFitting SimpleImputer(strategy='median') …")
    t0 = time.perf_counter()
    imputer = SimpleImputer(strategy="median")
    X_imputed = imputer.fit_transform(X_train)
    print(f"  Done in {time.perf_counter()-t0:.2f}s  "
          f"| nulls remaining: {np.isnan(X_imputed).sum()}")

    # ── 5. Fit StandardScaler on training data ────────────────────────────
    print(f"\nFitting StandardScaler() …")
    t0 = time.perf_counter()
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_imputed)
    print(f"  Done in {time.perf_counter()-t0:.2f}s  "
          f"| mean≈0: {np.abs(X_scaled.mean(axis=0)).max():.6f}  "
          f"| std≈1: {np.abs(X_scaled.std(axis=0) - 1).max():.6f}")

    # ── 6. Fit IsolationForest on training data ───────────────────────────
    print(f"\nFitting IsolationForest("
          f"n_estimators={N_ESTIMATORS}, "
          f"contamination='{CONTAMINATION}', "
          f"random_state={RANDOM_SEED}, n_jobs=-1) …")
    t0 = time.perf_counter()
    iso_forest = IsolationForest(
        n_estimators=N_ESTIMATORS,
        contamination=CONTAMINATION,
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )
    iso_forest.fit(X_scaled)
    elapsed_if = time.perf_counter() - t0
    print(f"  Done in {elapsed_if:.2f}s")

    # Training score summary
    train_scores = iso_forest.score_samples(X_scaled)
    train_preds  = iso_forest.predict(X_scaled)
    n_anomalies  = int((train_preds == -1).sum())
    n_normal     = int((train_preds ==  1).sum())
    anomaly_rate = n_anomalies / len(train_preds) * 100
    print(f"\n  Training score summary:")
    print(f"    Normal    : {n_normal:>9,}  ({100-anomaly_rate:.2f}%)")
    print(f"    Anomalous : {n_anomalies:>9,}  ({anomaly_rate:.2f}%)")
    print(f"    Score range : [{train_scores.min():.4f}, {train_scores.max():.4f}]")
    print(f"    Score mean  : {train_scores.mean():.4f}  std: {train_scores.std():.4f}")

    # ── 7. Save artefacts ─────────────────────────────────────────────────
    print("\nSaving model artefacts …")
    _save_pkl(iso_forest,    MODEL_DIR / "isolation_forest.pkl", "IsolationForest")
    _save_pkl(imputer,       MODEL_DIR / "imputer.pkl",          "SimpleImputer")
    _save_pkl(scaler,        MODEL_DIR / "scaler.pkl",           "StandardScaler")
    _save_pkl(FEATURE_COLS,  MODEL_DIR / "feature_columns.pkl",  "feature_columns")

    # ── 8. Save metadata.json ─────────────────────────────────────────────
    metadata = {
        "model":                   "Model C — PDE Anomaly Detection",
        "description":             "Separate PDE-only model; not combined with Model B medical claims",
        "algorithm":               "IsolationForest",
        "trained_at":              datetime.now(timezone.utc).isoformat(),
        "training_row_count":      int(len(train_df)),
        "test_row_count":          int(len(test_df)),
        "feature_count":           int(len(FEATURE_COLS)),
        "feature_columns":         FEATURE_COLS,
        "training_period": {
            "years":   train_years,
            "year_min": int(min(train_years)),
            "year_max": int(max(train_years)),
            "description": f"YEAR <= {TRAIN_MAX_YEAR}",
        },
        "test_period": {
            "years":   test_years,
            "year_min": int(min(test_years)),
            "year_max": int(max(test_years)),
            "description": f"YEAR == {TEST_YEAR} (held out, never used in training)",
        },
        "random_seed":             RANDOM_SEED,
        "n_estimators":            N_ESTIMATORS,
        "contamination":           str(CONTAMINATION),
        "training_anomaly_rate_pct": round(anomaly_rate, 4),
        "training_score_mean":     round(float(train_scores.mean()), 6),
        "training_score_std":      round(float(train_scores.std()),  6),
        "training_score_min":      round(float(train_scores.min()),  6),
        "training_score_max":      round(float(train_scores.max()),  6),
        "model_parameters": {
            "n_estimators":  N_ESTIMATORS,
            "contamination": str(CONTAMINATION),
            "random_state":  RANDOM_SEED,
            "n_jobs":        -1,
            "max_samples":   int(iso_forest.max_samples_),
        },
        "preprocessing": {
            "step_1": {
                "name":     "SimpleImputer",
                "strategy": "median",
                "note":     "Fitted on PDE training data only (YEAR <= 2022)",
            },
            "step_2": {
                "name":     "StandardScaler",
                "with_mean": True,
                "with_std":  True,
                "note":     "Fitted on imputed PDE training data only",
            },
            "step_3": {
                "name":          "IsolationForest",
                "n_estimators":  N_ESTIMATORS,
                "contamination": str(CONTAMINATION),
                "random_state":  RANDOM_SEED,
                "n_jobs":        -1,
                "note":          "Fitted on scaled PDE training data only",
            },
        },
        "leakage_prevention": {
            "imputer_fitted_on":          "PDE training data only (YEAR <= 2022)",
            "scaler_fitted_on":           "PDE training data only (YEAR <= 2022)",
            "iforest_fitted_on":          "PDE training data only (YEAR <= 2022)",
            "test_data_loaded_in_train":  False,
            "bene_history_source":        "strictly prior PDE rows only (validated)",
            "prescriber_history_source":  "strictly prior PDE rows only (validated)",
            "no_medical_claims_mixed_in": True,
        },
        "artefacts": {
            "isolation_forest": "models/model_c_pde/isolation_forest.pkl",
            "imputer":          "models/model_c_pde/imputer.pkl",
            "scaler":           "models/model_c_pde/scaler.pkl",
            "feature_columns":  "models/model_c_pde/feature_columns.pkl",
        },
        "data_sources": {
            "pde_features":    "data/processed/pde/pde_features.csv",
            "raw_pde":         "data/raw/pde/pde.csv",
            "test_held_out":   f"YEAR == {TEST_YEAR} rows from pde_features.csv (NOT USED IN TRAINING)",
        },
        "total_training_time_sec": round(time.perf_counter() - t_start, 2),
    }

    meta_path = MODEL_DIR / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    size_kb = meta_path.stat().st_size / 1024
    print(f"  ✓ {'metadata.json':<30s} → metadata.json  ({size_kb:.1f} KB)")

    # ── 9. Verify artefacts are loadable ──────────────────────────────────
    print("\nVerifying artefact integrity …")
    for fname in ["isolation_forest.pkl", "imputer.pkl", "scaler.pkl",
                  "feature_columns.pkl", "metadata.json"]:
        p = MODEL_DIR / fname
        assert p.exists(), f"Missing: {fname}"
        if fname.endswith(".pkl"):
            with open(p, "rb") as f:
                obj = pickle.load(f)
            print(f"  {fname:<35s} ✓  ({type(obj).__name__})")
        else:
            with open(p) as f:
                json.load(f)
            print(f"  {fname:<35s} ✓  (valid JSON)")

    # ── 10. Final summary ─────────────────────────────────────────────────
    total_time = time.perf_counter() - t_start
    print()
    print("=" * 62)
    print("  MODEL C (PDE) TRAINING COMPLETE")
    print("=" * 62)
    print(f"  Training rows     : {len(train_df):,}  (YEAR {min(train_years)}–{max(train_years)})")
    print(f"  Test rows         : {len(test_df):,}   (YEAR {TEST_YEAR}, held out)")
    print(f"  Features          : {len(FEATURE_COLS)}")
    print(f"  n_estimators      : {N_ESTIMATORS}")
    print(f"  contamination     : {CONTAMINATION}")
    print(f"  random_seed       : {RANDOM_SEED}")
    print(f"  Anomaly rate      : {anomaly_rate:.2f}%  ({n_anomalies:,} flagged)")
    print(f"  Score range       : [{train_scores.min():.4f}, {train_scores.max():.4f}]")
    print(f"  Total time        : {total_time:.1f}s")
    print(f"  Artefacts saved   : {MODEL_DIR.relative_to(ROOT)}/")
    print(f"  Medical claims    : NOT mixed in (Model C is PDE-only)")
    print("=" * 62)


if __name__ == "__main__":
    main()
