"""
Model B — Medical Claim Anomaly Detection — Training
=====================================================
Pipeline:
    SimpleImputer(strategy="median")
    → StandardScaler()
    → IsolationForest(n_estimators=300, contamination="auto", random_state=42, n_jobs=-1)

All three components are fitted ONLY on the stratified training sample.
The test set is never loaded, never touched.

Outputs
-------
models/model_b_claim/
    isolation_forest.pkl
    imputer.pkl
    scaler.pkl
    feature_columns.pkl
    metadata.json

Run from project root:
    python scripts/train_model_b.py
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
SAMPLE_CSV  = ROOT / "data" / "processed" / "medical" / "model_b_training_sample.csv"
FEAT_JSON   = ROOT / "data" / "processed" / "reference" / "model_b_feature_list.json"
MODEL_DIR   = ROOT / "models" / "model_b_claim"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# ── hyperparameters ───────────────────────────────────────────────────────────
RANDOM_SEED   = 42
N_ESTIMATORS  = 300
CONTAMINATION = "auto"


def _save_pkl(obj, path: Path, label: str) -> None:
    with open(path, "wb") as f:
        pickle.dump(obj, f, protocol=5)
    size_kb = path.stat().st_size / 1024
    print(f"  ✓ {label:<25s} → {path.name}  ({size_kb:,.0f} KB)")


def main():
    t_start = time.perf_counter()

    # ── 1. Load feature column list ───────────────────────────────────────
    print("Loading feature column list …")
    with open(FEAT_JSON, encoding="utf-8") as f:
        feat_meta = json.load(f)
    feature_cols: list[str] = feat_meta["feature_columns"]
    print(f"  {len(feature_cols)} feature columns defined")

    # ── 2. Load training sample ───────────────────────────────────────────
    print("\nLoading training sample …")
    train_raw = pd.read_csv(SAMPLE_CSV, low_memory=False)
    print(f"  {len(train_raw):,} rows × {len(train_raw.columns)} columns")

    # Verify all required feature columns are present
    missing_cols = [c for c in feature_cols if c not in train_raw.columns]
    if missing_cols:
        raise ValueError(f"Missing feature columns in sample: {missing_cols}")
    print(f"  All {len(feature_cols)} feature columns present ✓")

    # Reconstruct claim_type labels for metadata (from OHE cols)
    ohe_cols = [c for c in train_raw.columns if c.startswith("CLMTYPE_")]
    claim_types = sorted(c.replace("CLMTYPE_", "") for c in ohe_cols)
    training_years = sorted(train_raw["YEAR"].dropna().unique().astype(int).tolist())

    # Extract feature matrix — training only
    X_train = train_raw[feature_cols].copy()
    print(f"  Feature matrix shape: {X_train.shape}")

    # Null summary before imputation
    null_pct = X_train.isnull().mean().mul(100)
    cols_with_nulls = null_pct[null_pct > 0]
    print(f"\n  Columns with missing values before imputation: {len(cols_with_nulls)}")
    for col, pct in cols_with_nulls.sort_values(ascending=False).head(5).items():
        print(f"    {col:<40s}: {pct:.1f}%")
    if len(cols_with_nulls) > 5:
        print(f"    … and {len(cols_with_nulls) - 5} more")

    # ── 3. Fit imputer (training data only) ───────────────────────────────
    print("\nFitting SimpleImputer(strategy='median') …")
    t0 = time.perf_counter()
    imputer = SimpleImputer(strategy="median")
    X_imputed = imputer.fit_transform(X_train)
    print(f"  Done in {time.perf_counter() - t0:.2f}s  "
          f"| output shape: {X_imputed.shape}  "
          f"| nulls remaining: {np.isnan(X_imputed).sum()}")

    # ── 4. Fit scaler (training data only) ────────────────────────────────
    print("\nFitting StandardScaler() …")
    t0 = time.perf_counter()
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_imputed)
    print(f"  Done in {time.perf_counter() - t0:.2f}s  "
          f"| mean≈0: {np.abs(X_scaled.mean(axis=0)).max():.4f}  "
          f"| std≈1: {np.abs(X_scaled.std(axis=0) - 1).max():.4f}")

    # ── 5. Fit Isolation Forest (training data only) ──────────────────────
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

    # Quick score summary on training data
    train_scores = iso_forest.score_samples(X_scaled)   # raw anomaly scores
    train_preds  = iso_forest.predict(X_scaled)          # +1 normal, -1 anomaly
    n_anomalies  = int((train_preds == -1).sum())
    n_normal     = int((train_preds ==  1).sum())
    anomaly_rate = n_anomalies / len(train_preds) * 100
    print(f"\n  Training score summary:")
    print(f"    Normal     : {n_normal:>8,}  ({100 - anomaly_rate:.1f}%)")
    print(f"    Anomalous  : {n_anomalies:>8,}  ({anomaly_rate:.1f}%)")
    print(f"    Score range: [{train_scores.min():.4f}, {train_scores.max():.4f}]")
    print(f"    Score mean : {train_scores.mean():.4f}  std: {train_scores.std():.4f}")

    # ── 6. Save artefacts ─────────────────────────────────────────────────
    print("\nSaving model artefacts …")
    _save_pkl(iso_forest, MODEL_DIR / "isolation_forest.pkl", "IsolationForest")
    _save_pkl(imputer,    MODEL_DIR / "imputer.pkl",          "SimpleImputer")
    _save_pkl(scaler,     MODEL_DIR / "scaler.pkl",           "StandardScaler")
    _save_pkl(feature_cols, MODEL_DIR / "feature_columns.pkl", "feature_columns")

    # ── 7. Save metadata.json ─────────────────────────────────────────────
    metadata = {
        "model":                "Model B — Medical Claim Anomaly Detection",
        "algorithm":            "IsolationForest",
        "trained_at":           datetime.now(timezone.utc).isoformat(),
        "training_row_count":   int(len(train_raw)),
        "feature_count":        int(len(feature_cols)),
        "feature_columns":      feature_cols,
        "training_years":       training_years,
        "claim_types":          claim_types,
        "random_seed":          RANDOM_SEED,
        "n_estimators":         N_ESTIMATORS,
        "contamination":        CONTAMINATION,
        "training_anomaly_rate_pct": round(anomaly_rate, 4),
        "training_score_mean":  round(float(train_scores.mean()), 6),
        "training_score_std":   round(float(train_scores.std()),  6),
        "training_score_min":   round(float(train_scores.min()),  6),
        "training_score_max":   round(float(train_scores.max()),  6),
        "preprocessing": {
            "step_1": {
                "name":     "SimpleImputer",
                "strategy": "median",
                "note":     "Fitted on training sample only; medians stored in imputer.pkl",
            },
            "step_2": {
                "name":     "StandardScaler",
                "note":     "Fitted on imputed training data only; mean/std stored in scaler.pkl",
                "with_mean": True,
                "with_std":  True,
            },
            "step_3": {
                "name":          "IsolationForest",
                "n_estimators":  N_ESTIMATORS,
                "contamination": str(CONTAMINATION),
                "random_state":  RANDOM_SEED,
                "n_jobs":        -1,
                "note":          "Fitted on scaled training sample only",
            },
        },
        "artefacts": {
            "isolation_forest": "models/model_b_claim/isolation_forest.pkl",
            "imputer":          "models/model_b_claim/imputer.pkl",
            "scaler":           "models/model_b_claim/scaler.pkl",
            "feature_columns":  "models/model_b_claim/feature_columns.pkl",
        },
        "data_sources": {
            "training_sample":  "data/processed/medical/model_b_training_sample.csv",
            "feature_list":     "data/processed/reference/model_b_feature_list.json",
            "test_set":         "data/processed/medical/test_medical.csv (NOT USED IN TRAINING)",
        },
        "leakage_prevention": {
            "imputer_fitted_on":  "training sample only",
            "scaler_fitted_on":   "training sample only",
            "iforest_fitted_on":  "training sample only",
            "test_data_loaded":   False,
            "peer_stats_period":  "2015-2022 (test year 2023 excluded)",
            "bene_history":       "strictly prior claims only (validated)",
        },
        "total_training_time_sec": round(time.perf_counter() - t_start, 2),
    }

    meta_path = MODEL_DIR / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    size_kb = meta_path.stat().st_size / 1024
    print(f"  ✓ {'metadata.json':<25s} → metadata.json  ({size_kb:.1f} KB)")

    # ── 8. Final summary ──────────────────────────────────────────────────
    total_time = time.perf_counter() - t_start
    print()
    print("=" * 60)
    print("  MODEL B TRAINING COMPLETE")
    print("=" * 60)
    print(f"  Training rows     : {len(train_raw):,}")
    print(f"  Features          : {len(feature_cols)}")
    print(f"  Training years    : {training_years[0]}–{training_years[-1]}")
    print(f"  Claim types       : {', '.join(claim_types)}")
    print(f"  n_estimators      : {N_ESTIMATORS}")
    print(f"  Contamination     : {CONTAMINATION}")
    print(f"  Anomaly rate      : {anomaly_rate:.2f}%")
    print(f"  Total time        : {total_time:.1f}s")
    print(f"  Artefacts saved   : {MODEL_DIR.relative_to(ROOT)}/")
    print("=" * 60)

    # Verify all artefacts exist and are loadable
    print("\nVerifying artefact integrity …")
    for fname in ["isolation_forest.pkl", "imputer.pkl", "scaler.pkl",
                  "feature_columns.pkl", "metadata.json"]:
        p = MODEL_DIR / fname
        assert p.exists(), f"Missing: {fname}"
        if fname.endswith(".pkl"):
            with open(p, "rb") as f:
                obj = pickle.load(f)
            print(f"  {fname:<30s} ✓  ({type(obj).__name__})")
        else:
            with open(p) as f:
                json.load(f)
            print(f"  {fname:<30s} ✓  (valid JSON)")


if __name__ == "__main__":
    main()
