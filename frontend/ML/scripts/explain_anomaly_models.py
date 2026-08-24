"""
Anomaly Model Explainability — Model B (Medical) & Model C (PDE)
=================================================================
Uses SHAP TreeExplainer to compute feature contributions for both
Isolation Forest models.

IMPORTANT LABELLING NOTE
-------------------------
SHAP values here represent statistical anomaly evidence — how much each
feature pushes a transaction toward or away from the typical population
distribution seen in training.

They do NOT constitute proof of fraud, abuse, or policy violation.
Anomaly = statistical departure from training patterns.

SHAP sign convention for IsolationForest (TreeExplainer):
    Negative SHAP → pushes anomaly score lower → anomaly driver
                    (feature value is unusually extreme for this population)
    Positive SHAP → pushes anomaly score higher → normalizing factor
                    (feature value is typical, reducing anomaly signal)

Outputs
-------
data/outputs/model_b_explanations.csv   — per-row SHAP values, top drivers (test set)
data/outputs/model_c_explanations.csv   — per-row SHAP values, top drivers (test set)
data/processed/reference/model_b_global_feature_importance.csv
data/processed/reference/model_c_global_feature_importance.csv

Run from project root:
    python scripts/explain_anomaly_models.py
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import shap
import pickle

warnings.filterwarnings("ignore")

# ── paths ─────────────────────────────────────────────────────────────────────
ROOT    = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "outputs"
REF_DIR = ROOT / "data" / "processed" / "reference"
OUT_DIR.mkdir(parents=True, exist_ok=True)
REF_DIR.mkdir(parents=True, exist_ok=True)

# Model B
MB_MODEL   = ROOT / "models" / "model_b_claim"
MB_TEST    = ROOT / "data" / "outputs" / "model_b_test_scores.csv"
MB_OUT     = OUT_DIR / "model_b_explanations.csv"
MB_GLOBAL  = REF_DIR / "model_b_global_feature_importance.csv"

# Model C
MC_MODEL   = ROOT / "models" / "model_c_pde"
MC_TEST    = ROOT / "data" / "outputs" / "model_c_pde_test_scores.csv"
MC_OUT     = OUT_DIR / "model_c_explanations.csv"
MC_GLOBAL  = REF_DIR / "model_c_global_feature_importance.csv"

# Number of top drivers to record per row
TOP_N_ANOMALY  = 5    # top anomaly-driving features (most negative SHAP)
TOP_N_NORMAL   = 3    # top normalizing features (most positive SHAP)

# Max rows to run full per-row SHAP on (TreeExplainer is fast but test set is large)
MAX_ROWS_SHAP_B = 50_000   # Model B test: 50,579 rows — do all
MAX_ROWS_SHAP_C = 14_330   # Model C test: 14,330 rows — do all


# ── helpers ───────────────────────────────────────────────────────────────────

def _load_artefacts(model_dir: Path):
    def _pkl(name):
        with open(model_dir / name, "rb") as f:
            return pickle.load(f)
    return (_pkl("isolation_forest.pkl"), _pkl("imputer.pkl"),
            _pkl("scaler.pkl"),          _pkl("feature_columns.pkl"))


def _preprocess(df: pd.DataFrame, feat_cols: list, imp, scl) -> np.ndarray:
    """Impute → scale feature matrix."""
    X     = df[feat_cols].values.astype(float)
    X_imp = imp.transform(X)
    return scl.transform(X_imp)


def _compute_shap(iso, X_scaled: np.ndarray, max_rows: int) -> np.ndarray:
    """Compute SHAP values (TreeExplainer). Returns array (n, n_features)."""
    n = min(max_rows, X_scaled.shape[0])
    explainer = shap.TreeExplainer(iso)
    print(f"    Computing SHAP for {n:,} rows …")
    sv = explainer.shap_values(X_scaled[:n])
    return np.array(sv), explainer.expected_value


def _top_drivers(sv_row: np.ndarray, feat_cols: list,
                 X_raw_row: np.ndarray,     # original (pre-scaled) feature values
                 n_anomaly: int = 5,
                 n_normal:  int = 3) -> dict:
    """
    For one row, return top anomaly and normal drivers with values
    and SHAP contributions.
    """
    paired = list(zip(feat_cols, sv_row.tolist(), X_raw_row.tolist()))

    # Anomaly drivers: most negative SHAP (feature makes claim more anomalous)
    anomaly_drivers = sorted(paired, key=lambda x: x[1])[:n_anomaly]
    # Normal drivers: most positive SHAP (feature makes claim look more normal)
    normal_drivers  = sorted(paired, key=lambda x: -x[1])[:n_normal]

    out = {}
    for rank, (feat, shap_val, raw_val) in enumerate(anomaly_drivers, 1):
        out[f"anomaly_driver_{rank}_feature"]    = feat
        out[f"anomaly_driver_{rank}_value"]      = round(float(raw_val), 4)
        out[f"anomaly_driver_{rank}_shap"]       = round(float(shap_val), 6)
        out[f"anomaly_driver_{rank}_evidence"]   = (
            f"{feat}={raw_val:.3g} deviates from training norm "
            f"(SHAP contribution: {shap_val:+.4f})"
        )

    for rank, (feat, shap_val, raw_val) in enumerate(normal_drivers, 1):
        out[f"normal_driver_{rank}_feature"]     = feat
        out[f"normal_driver_{rank}_value"]       = round(float(raw_val), 4)
        out[f"normal_driver_{rank}_shap"]        = round(float(shap_val), 6)

    return out


def _global_importance(sv: np.ndarray, feat_cols: list,
                        model_name: str) -> pd.DataFrame:
    """
    Compute global feature importance as mean(|SHAP|) across all explained rows.
    Also compute mean SHAP (direction) and anomaly-push ratio.
    """
    mean_abs  = np.abs(sv).mean(axis=0)
    mean_shap = sv.mean(axis=0)
    # Anomaly push ratio: fraction of rows where this feature pushed toward anomaly
    anomaly_push_ratio = (sv < 0).mean(axis=0)

    df = pd.DataFrame({
        "feature":             feat_cols,
        "mean_abs_shap":       mean_abs.round(6),
        "mean_shap":           mean_shap.round(6),
        "anomaly_push_ratio":  anomaly_push_ratio.round(4),
        "direction":           ["anomaly_driver" if m < 0 else "normal_driver"
                                 for m in mean_shap],
        "model":               model_name,
        "interpretation":      [
            (f"Statistically, this feature pushes transactions toward anomaly on average "
             f"({anomaly_push_ratio[i]*100:.0f}% of rows)")
            if mean_shap[i] < 0 else
            (f"Statistically, this feature is typically within training norms "
             f"(normal on {(1-anomaly_push_ratio[i])*100:.0f}% of rows)")
            for i in range(len(feat_cols))
        ],
    }).sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)

    df.insert(0, "rank", range(1, len(df) + 1))
    return df


def _build_output(test_df: pd.DataFrame, sv: np.ndarray,
                  feat_cols: list, X_raw: np.ndarray,
                  risk_col: str = "RISK_SCORE") -> pd.DataFrame:
    """
    Attach per-row top-driver columns and risk metadata to the test frame.
    """
    n = sv.shape[0]

    driver_records = []
    for i in range(n):
        driver_records.append(
            _top_drivers(sv[i], feat_cols, X_raw[i],
                         TOP_N_ANOMALY, TOP_N_NORMAL)
        )

    driver_df  = pd.DataFrame(driver_records)
    meta_cols  = [c for c in test_df.columns
                  if c in (feat_cols + [risk_col, "RISK_LEVEL",
                                        "RAW_DECISION_SCORE", "ANOMALY_PREDICTION",
                                        "YEAR", "BENE_ID", "PDE_ID",
                                        "BRND_GNRC_CD", "PHRMCY_SRVC_TYPE_CD"])]

    result = pd.concat([
        test_df.iloc[:n][meta_cols].reset_index(drop=True),
        driver_df.reset_index(drop=True),
    ], axis=1)

    # Add a human-readable summary per row
    result["statistical_anomaly_summary"] = result.apply(
        lambda r: (
            f"Risk score {r.get(risk_col, '?'):.1f}/100. "
            f"Top anomaly signals: "
            + "; ".join([
                r.get(f"anomaly_driver_{k}_evidence", "")
                for k in range(1, TOP_N_ANOMALY + 1)
                if r.get(f"anomaly_driver_{k}_evidence")
            ])
            + ". NOTE: Statistical anomaly evidence only — not proof of fraud."
        ),
        axis=1,
    )
    return result


# ── model B explainability ────────────────────────────────────────────────────

def explain_model_b():
    print("=" * 62)
    print("  MODEL B — MEDICAL CLAIM EXPLAINABILITY")
    print("=" * 62)

    # Load
    iso, imp, scl, feat_cols = _load_artefacts(MB_MODEL)
    test = pd.read_csv(MB_TEST, low_memory=False)
    print(f"  Test rows: {len(test):,}  Features: {len(feat_cols)}")

    # Reconstruct claim type label for output
    ohe_cols = [c for c in test.columns if c.startswith("CLMTYPE_")]
    test["CLAIM_TYPE_LABEL"] = (
        test[ohe_cols].idxmax(axis=1).str.replace("CLMTYPE_", "", regex=False)
    )

    # Check which feature cols are in test
    missing = [c for c in feat_cols if c not in test.columns]
    if missing:
        raise ValueError(f"Test missing: {missing}")

    # Preprocess
    n = min(MAX_ROWS_SHAP_B, len(test))
    print(f"  Preprocessing {n:,} rows …")
    X_scaled = _preprocess(test.iloc[:n], feat_cols, imp, scl)
    X_raw    = test.iloc[:n][feat_cols].values.astype(float)

    # SHAP
    sv, ev = _compute_shap(iso, X_scaled, n)
    ev_scalar = float(np.ravel(ev)[0])
    print(f"    SHAP matrix shape: {sv.shape}  |  expected_value: {ev_scalar:.4f}")

    # Global importance
    global_imp = _global_importance(sv, feat_cols, "model_b_medical")
    global_imp.to_csv(MB_GLOBAL, index=False)
    print(f"  ✓ Global importance → {MB_GLOBAL.relative_to(ROOT)}")
    print("\n  Top 15 features by mean |SHAP| (Model B):")
    print(f"  {'Rank':<5} {'Feature':<45} {'mean|SHAP|':>11} {'direction':<18}")
    print("  " + "-" * 82)
    for _, row in global_imp.head(15).iterrows():
        print(f"  {int(row['rank']):<5} {row['feature']:<45} "
              f"{row['mean_abs_shap']:>11.5f} {row['direction']:<18}")

    # Per-row output (reset test index to 0-based for iloc[:n])
    test_reset = test.reset_index(drop=True)
    print(f"\n  Building per-row explanation output …")
    out = _build_output(test_reset, sv, feat_cols, X_raw, risk_col="RISK_SCORE")
    out.to_csv(MB_OUT, index=False)
    print(f"  ✓ Per-row explanations → {MB_OUT.relative_to(ROOT)}")
    print(f"    {len(out):,} rows  |  {len(out.columns)} columns")

    # Sample anomalous claim
    print("\n  Sample: Top anomalous claim (highest RISK_SCORE):")
    top_pos = int(test_reset.iloc[:n]["RISK_SCORE"].argmax())
    row     = out.iloc[top_pos]
    print(f"    RISK_SCORE: {row.get('RISK_SCORE', '?')}")
    ct_val = test_reset.iloc[top_pos].get("CLAIM_TYPE_LABEL", "?") if "CLAIM_TYPE_LABEL" in test_reset.columns else "?"
    print(f"    CLAIM_TYPE: {ct_val}")
    for k in range(1, TOP_N_ANOMALY + 1):
        feat_k = row.get(f"anomaly_driver_{k}_feature", "")
        val_k  = row.get(f"anomaly_driver_{k}_value",   "")
        shap_k = row.get(f"anomaly_driver_{k}_shap",    "")
        if feat_k:
            print(f"    Anomaly driver {k}: {feat_k} = {val_k}  (SHAP: {float(shap_k):+.4f})")
    print(f"    Note: {str(row.get('statistical_anomaly_summary',''))[:120]}…")
    print()


# ── model C explainability ────────────────────────────────────────────────────

def explain_model_c():
    print("=" * 62)
    print("  MODEL C — PDE EXPLAINABILITY")
    print("=" * 62)

    # Load
    iso, imp, scl, feat_cols = _load_artefacts(MC_MODEL)
    test = pd.read_csv(MC_TEST, low_memory=False)
    print(f"  Test rows: {len(test):,}  Features: {len(feat_cols)}")

    # Some features may have been added after scoring (risk scores, levels)
    missing = [c for c in feat_cols if c not in test.columns]
    if missing:
        print(f"  WARNING: test missing {len(missing)} cols; loading from pde_features …")
        pde = pd.read_csv(
            ROOT / "data" / "processed" / "pde" / "pde_features.csv",
            usecols=["PDE_ID"] + missing, low_memory=False
        )
        if "PDE_ID" in test.columns:
            test = test.merge(pde, on="PDE_ID", how="left")
        else:
            raise ValueError(f"Cannot join missing cols: {missing}")

    # Preprocess
    n = min(MAX_ROWS_SHAP_C, len(test))
    print(f"  Preprocessing {n:,} rows …")
    X_scaled = _preprocess(test.iloc[:n], feat_cols, imp, scl)
    X_raw    = test.iloc[:n][feat_cols].values.astype(float)

    # SHAP
    sv, ev = _compute_shap(iso, X_scaled, n)
    ev_scalar = float(np.ravel(ev)[0])
    print(f"    SHAP matrix shape: {sv.shape}  |  expected_value: {ev_scalar:.4f}")

    # Global importance
    global_imp = _global_importance(sv, feat_cols, "model_c_pde")
    global_imp.to_csv(MC_GLOBAL, index=False)
    print(f"  ✓ Global importance → {MC_GLOBAL.relative_to(ROOT)}")
    print("\n  Top 15 features by mean |SHAP| (Model C):")
    print(f"  {'Rank':<5} {'Feature':<45} {'mean|SHAP|':>11} {'direction':<18}")
    print("  " + "-" * 82)
    for _, row in global_imp.head(15).iterrows():
        print(f"  {int(row['rank']):<5} {row['feature']:<45} "
              f"{row['mean_abs_shap']:>11.5f} {row['direction']:<18}")

    # Per-row output
    test_reset = test.reset_index(drop=True)
    risk_col_actual = "RISK_SCORE" if "RISK_SCORE" in test_reset.columns else "RISK_SCORE_OVERALL"
    print(f"\n  Building per-row explanation output …")
    out = _build_output(test_reset, sv, feat_cols, X_raw,
                        risk_col=risk_col_actual if risk_col_actual in test_reset.columns else "RISK_SCORE")
    out.to_csv(MC_OUT, index=False)
    print(f"  ✓ Per-row explanations → {MC_OUT.relative_to(ROOT)}")
    print(f"    {len(out):,} rows  |  {len(out.columns)} columns")

    # Sample anomalous PDE transaction
    print("\n  Sample: Top anomalous PDE transaction:")
    top_pos = int(test_reset.iloc[:n][risk_col_actual].argmax()) if risk_col_actual in test_reset.columns else 0
    row     = out.iloc[top_pos]
    rs_val  = row.get("RISK_SCORE", row.get("RISK_SCORE_OVERALL", "?"))
    print(f"    RISK_SCORE    : {rs_val}")
    for k in range(1, TOP_N_ANOMALY + 1):
        feat_k = row.get(f"anomaly_driver_{k}_feature", "")
        val_k  = row.get(f"anomaly_driver_{k}_value",   "")
        shap_k = row.get(f"anomaly_driver_{k}_shap",    "")
        if feat_k:
            print(f"    Anomaly driver {k}: {feat_k} = {val_k}  (SHAP: {float(shap_k):+.4f})")
    print(f"    Note: {str(row.get('statistical_anomaly_summary',''))[:120]}…")
    print()


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    explain_model_b()
    explain_model_c()

    print("=" * 62)
    print("  EXPLAINABILITY COMPLETE")
    print("=" * 62)
    print(f"  Model B explanations  → {MB_OUT.relative_to(ROOT)}")
    print(f"  Model B global imp    → {MB_GLOBAL.relative_to(ROOT)}")
    print(f"  Model C explanations  → {MC_OUT.relative_to(ROOT)}")
    print(f"  Model C global imp    → {MC_GLOBAL.relative_to(ROOT)}")
    print()
    print("  DISCLAIMER: All SHAP values represent statistical anomaly evidence.")
    print("  They indicate how much each feature deviates from training patterns.")
    print("  They do NOT constitute proof of fraud, abuse, or policy violation.")
    print("  Findings require human review before any compliance action.")
    print("=" * 62)


if __name__ == "__main__":
    main()
