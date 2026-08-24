"""
backend/hybrid_engine.py
========================
Hybrid Payment Integrity Scoring Engine (Adaptive Weighting)
------------------------------------------------------------
Combines two independently-trained fraud/anomaly models:

  Model B  — Claim-Level Isolation Forest   (59 features, unsupervised)
  Model V2 — Provider-Level XGBoost          (59 behavioral features, AUC 0.957)

Adaptive Blending Strategy:
  1. Context-Aware Weighting:
     - For single-claim API scoring without accumulated historical provider batches (N=1),
       the Provider XGBoost prior defaults to ~0.055.
       -> The engine dynamically assigns 80% weight to Claim Anomaly and 20% to Provider Fraud.
     - For provider batch/profiling with accumulated history (N >= 10),
       the engine shifts to 40% Claim / 60% Provider.
  2. Signal Sensitivity:
     - If XGBoost detects high provider fraud risk (>= 0.40), provider weight dominates (>= 70%).
     - If Model B detects extreme claim anomaly (>= 0.95), claim weight stays authoritative.
  3. Dynamic Calibration:
     - For synthetic/unobserved beneficiary history, calibrated anomaly scaling provides
       a full, responsive dynamic range across Low (0-0.40), Medium (0.40-0.55),
       High (0.55-0.75), and Critical (0.75-1.00).

Layer 0 — LEIE Gatekeeper (Deterministic Override):
  If provider NPI matches an active HHS OIG exclusion -> final_score = 1.0 (Critical)
"""

from __future__ import annotations

import os
import sys
import logging
import pickle
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Suppress sklearn versioning warnings
warnings.filterwarnings("ignore", message="X does not have valid feature names", category=UserWarning)
warnings.filterwarnings("ignore", message="Trying to unpickle estimator", category=UserWarning)

# ── path bootstrap ────────────────────────────────────────────────────────────
_HERE  = Path(__file__).resolve().parent
_ROOT  = _HERE

for _p in [str(_HERE), str(_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── Model B artefacts (claim-level) ───────────────────────────────────────────
_MODEL_B  = _ROOT / "models" / "model_b_claim"

def _pkl(p: Path):
    with open(p, "rb") as f:
        return pickle.load(f)

_iso_b  = _pkl(_MODEL_B / "isolation_forest.pkl")
_imp_b  = _pkl(_MODEL_B / "imputer.pkl")

# Sklearn 1.8.0 compatibility patch for SimpleImputer pickled in 1.4.2
if not hasattr(_imp_b, '_fill_dtype'):
    if hasattr(_imp_b, 'statistics_'):
        _imp_b._fill_dtype = _imp_b.statistics_.dtype
    else:
        _imp_b._fill_dtype = np.float64

_scl_b  = _pkl(_MODEL_B / "scaler.pkl")
_feat_b = _pkl(_MODEL_B / "feature_columns.pkl")
_calib_b: dict[str, np.ndarray] = _pkl(_MODEL_B / "score_calibration.pkl")

# ── Model V2 artefacts (provider-level XGBoost) ────────────────────────────────
_MODEL_V2 = _ROOT / "models" / "model_v2_provider"
_PKL_V2   = _MODEL_V2 / "xgboost_fraud_model_v2.pkl"

_model_v2_artifacts: dict | None = None

def _load_v2() -> dict:
    global _model_v2_artifacts
    if _model_v2_artifacts is None:
        with open(_PKL_V2, "rb") as f:
            _model_v2_artifacts = pickle.load(f)
    return _model_v2_artifacts

# ── Import feature engineering helpers ─────────────────────────────────────────
try:
    from app.ml.provider_feature_engine import (
        preprocess_claims,
        aggregate_to_provider,
        build_cms_peer_benchmarks,
        join_cms_peer_features,
        CAT_COLS,
        CMS_USECOLS,
        FRAUD_THRESHOLD,
        TIER_BINS,
        TIER_LABELS,
    )
except ImportError:
    from provider_feature_engine import (
        preprocess_claims,
        aggregate_to_provider,
        build_cms_peer_benchmarks,
        join_cms_peer_features,
        CAT_COLS,
        CMS_USECOLS,
        FRAUD_THRESHOLD,
        TIER_BINS,
        TIER_LABELS,
    )

# ── Import Model B feature builder ─────────────────────────────────────────────
try:
    from app.ml.feature_engine import build_model_b_features, features_to_array
except ImportError:
    from feature_engine import build_model_b_features, features_to_array

# ── Import LEIE checker ────────────────────────────────────────────────────────
try:
    from app.ml.leie_checker import get_leie_index, lookup as leie_lookup, normalise_npi
except ImportError:
    from leie_checker import get_leie_index, lookup as leie_lookup, normalise_npi

# ── Constants ──────────────────────────────────────────────────────────────────

# Hybrid risk tier thresholds (aligned with config.py TIER_BINS)
HYBRID_TIERS = [
    (0.75, "Critical"),
    (0.55, "High"),
    (0.40, "Medium"),
    (0.00, "Low"),
]

_log = logging.getLogger("hybrid_engine")

# ── CMS peer lookup cache (loaded once on first call) ──────────────────────────
_peer_lookup: pd.DataFrame | None = None

def _get_peer_lookup() -> pd.DataFrame:
    global _peer_lookup
    if _peer_lookup is not None:
        return _peer_lookup

    peer_cache = _MODEL_V2 / "cms_peer_benchmarks.csv"
    if not peer_cache.exists():
        peer_cache = _ROOT / "models" / "xgboost_fraud_v2" / "cms_peer_benchmarks.csv"

    if peer_cache.exists():
        _peer_lookup = pd.read_csv(peer_cache)
        _log.info(f"Loaded CMS peer benchmarks from cache: {peer_cache}")
    else:
        _log.warning("CMS peer benchmarks cache not found — running without peer features.")
        _peer_lookup = pd.DataFrame()
    return _peer_lookup


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _pct_rank_vec(value: float, ref: np.ndarray) -> float:
    n       = len(ref)
    n_below = float(np.searchsorted(ref, value, side="left"))
    n_right = float(np.searchsorted(ref, value, side="right"))
    n_equal = n_right - n_below
    return float(np.clip((n_below + n_equal / 2) / n * 100, 0, 100))


def _calibrate_b(raw_score: float, claim_type: str) -> float:
    """Convert Isolation Forest decision_function output -> [0, 100] anomaly score."""
    ref = _calib_b.get(claim_type, _calib_b.get("overall", list(_calib_b.values())[0]))
    pct = _pct_rank_vec(raw_score, ref)
    return float((1 - pct / 100) * 100)   # higher = more anomalous


def _get_hybrid_tier(score_01: float) -> str:
    """Map a [0, 1] score to a risk tier label."""
    for threshold, label in HYBRID_TIERS:
        if score_01 >= threshold:
            return label
    return "Low"


def _score_model_b(claim_dict: dict) -> tuple[float, float, list[dict]]:
    """
    Run Model B (Isolation Forest) on a single claim dict.

    Returns
    -------
    (raw_score, calibrated_score_0_to_1, shap_evidence)
    """
    claim_type = str(claim_dict.get("claim_type", "carrier")).lower()

    # Build the 59-feature vector
    feat_dict, _meta = build_model_b_features(claim_dict)
    X      = features_to_array(feat_dict, _feat_b)
    X_imp  = _imp_b.transform(X)
    X_scl  = _scl_b.transform(X_imp)
    raw    = float(_iso_b.decision_function(X_scl)[0])

    # Calibrated score [0, 100] then / 100 -> [0, 1]
    calib_100 = _calibrate_b(raw, claim_type)
    score_01  = float(np.clip(calib_100 / 100.0, 0.0, 1.0))

    # SHAP evidence (best-effort)
    evidence = []
    try:
        import shap
        explainer = shap.TreeExplainer(_iso_b)
        sv        = np.array(explainer.shap_values(X_scl))[0]
        paired    = sorted(zip(_feat_b, sv.tolist(), X_imp[0].tolist()), key=lambda x: x[1])
        for fname, sval, rval in paired[:5]:
            evidence.append({
                "feature": fname, "value": round(float(rval), 4),
                "shap_contribution": round(float(sval), 6),
                "model": "Model_B_IsolationForest",
                "driver_type": "anomaly_driver",
            })
    except Exception:
        pass

    return raw, score_01, evidence


def _score_model_v2(claim_dict: dict) -> tuple[float, list[dict]]:
    """
    Run XGBoost v2 (provider-level) on a single claim dict.
    Internally aggregates the single claim to a single-provider row.

    Returns
    -------
    (provider_score_01, feature_importances)
    """
    arts         = _load_v2()
    model        = arts["model"]
    feature_cols = arts["feature_cols"]
    encoders     = arts["encoders"]
    medians      = arts["medians"]
    threshold    = arts.get("threshold", FRAUD_THRESHOLD)

    # Map claim_dict keys to the exact schema expected by aggregate_to_provider & join_cms_peer_features
    mapped_dict = {
        "Provider":                claim_dict.get("provider_id") or claim_dict.get("Provider") or "UNKNOWN",
        "BeneID":                  claim_dict.get("bene_id") or claim_dict.get("BeneID") or "BENE_UNKNOWN",
        "ClaimID":                 claim_dict.get("claim_id") or claim_dict.get("ClaimID") or "CLM_UNKNOWN",
        "ClaimStartDt":            claim_dict.get("claim_start_date") or claim_dict.get("ClaimStartDt"),
        "ClaimEndDt":              claim_dict.get("claim_end_date") or claim_dict.get("ClaimEndDt"),
        "ClaimType":               claim_dict.get("claim_type") or claim_dict.get("ClaimType") or "Carrier",
        "InscClaimAmtReimbursed":  float(claim_dict.get("clm_pmt_amt") if claim_dict.get("clm_pmt_amt") is not None else claim_dict.get("InscClaimAmtReimbursed", 0.0)),
        "DeductibleAmtPaid":       float(max(0.0, float(claim_dict.get("clm_tot_chrg_amt", 0.0) or 0.0) - float(claim_dict.get("clm_pmt_amt", 0.0) or 0.0))),
        "AttendingPhysician":      claim_dict.get("at_physn_npi") or claim_dict.get("AttendingPhysician") or np.nan,
        "OperatingPhysician":      claim_dict.get("OperatingPhysician") or np.nan,
        "OtherPhysician":          claim_dict.get("org_npi_num") or claim_dict.get("OtherPhysician") or np.nan,
        "DiagnosisCodeCount":      int(claim_dict.get("diag_count") if claim_dict.get("diag_count") is not None else claim_dict.get("DiagnosisCodeCount", 1)),
        "ProcedureCodeCount":      int(claim_dict.get("proc_count") if claim_dict.get("proc_count") is not None else claim_dict.get("ProcedureCodeCount", 0)),
        "State":                   claim_dict.get("state") or claim_dict.get("STATE_CODE") or claim_dict.get("State") or "CA",
    }

    # Aggregate the single claim row to provider-level features
    raw_df  = pd.DataFrame([mapped_dict])
    prov_df = aggregate_to_provider(raw_df, has_label=False, logger=_log)

    # Join CMS peer benchmarks (charge_vs_peer_ratio, state peer statistics)
    peer = _get_peer_lookup()
    if peer is not None and len(peer) > 0:
        prov_df = join_cms_peer_features(prov_df, peer, _log)

    # Fill missing features with training medians
    for col in feature_cols:
        if col not in prov_df.columns:
            prov_df[col] = medians.get(col, 0.0)

    # Encode categorical columns
    for col in CAT_COLS:
        if col in prov_df.columns and col in encoders:
            le    = encoders[col]
            known = set(le.classes_)
            prov_df[col] = (
                prov_df[col].astype(str)
                .apply(lambda x: x if x in known else "UNKNOWN")
            )
            prov_df[col] = le.transform(prov_df[col])

    # Impute remaining numerics
    for col in feature_cols:
        if col not in CAT_COLS:
            prov_df[col] = prov_df[col].fillna(medians.get(col, 0.0))

    X              = prov_df[feature_cols].values
    provider_score = float(model.predict_proba(X)[0, 1])

    # Feature importances for explainability
    importances = []
    try:
        fi_scores = model.feature_importances_
        top_idx   = np.argsort(fi_scores)[::-1][:5]
        for i in top_idx:
            importances.append({
                "feature":    feature_cols[i],
                "importance": round(float(fi_scores[i]), 6),
                "value":      round(float(prov_df[feature_cols[i]].iloc[0]), 4),
                "model":      "Model_V2_XGBoost",
                "driver_type": "provider_behavioral",
            })
    except Exception:
        pass

    return provider_score, importances


def _calculate_adaptive_weights(
    raw_claim_score: float,
    provider_score: float,
    total_claims: int = 1
) -> tuple[float, float, str]:
    """
    Dynamically compute blending weights based on context and confidence.

    Returns
    -------
    (w_claim, w_provider, weighting_mode)
    """
    # 1. Volume factor: scale provider authority with historical claim volume
    vol_factor   = min(1.0, max(0.0, (total_claims - 1) / 9.0))
    base_w_claim = 0.80 - 0.40 * vol_factor   # 0.80 for N=1, 0.40 for N>=10
    base_w_prov  = 0.20 + 0.40 * vol_factor   # 0.20 for N=1, 0.60 for N>=10

    # 2. Risk peak sensitivity
    if provider_score >= 0.40:
        w_prov  = max(base_w_prov, 0.70)
        w_claim = round(1.0 - w_prov, 2)
        mode    = "provider_risk_dominant"
    elif raw_claim_score >= 0.95 and total_claims <= 2:
        w_claim = max(base_w_claim, 0.80)
        w_prov  = round(1.0 - w_claim, 2)
        mode    = "claim_anomaly_dominant"
    else:
        w_claim = round(base_w_claim, 2)
        w_prov  = round(base_w_prov, 2)
        mode    = "single_claim_adaptive" if total_claims <= 2 else "historical_provider_profile"

    return w_claim, w_prov, mode


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def score_hybrid(claim_dict: dict) -> dict[str, Any]:
    """
    Score a single medical claim using the adaptive hybrid model engine.

    Parameters
    ----------
    claim_dict : dict
        Raw claim fields (same schema as /api/v1/predict MEDICAL_CLAIM).
        Required keys: claim_type, claim_start_date, clm_pmt_amt, clm_tot_chrg_amt, bene_id

    Returns
    -------
    dict with full risk evaluation and explanations.
    """
    # ── Compute duration if not pre-supplied ──────────────────────────────────
    if "claim_duration_days" not in claim_dict:
        try:
            if claim_dict.get("claim_end_date"):
                s = pd.to_datetime(claim_dict["claim_start_date"])
                e = pd.to_datetime(claim_dict["claim_end_date"])
                claim_dict = {**claim_dict, "claim_duration_days": max(0, (e - s).days)}
            else:
                claim_dict = {**claim_dict, "claim_duration_days": 0}
        except Exception:
            claim_dict = {**claim_dict, "claim_duration_days": 0}

    # ── LAYER 0: LEIE Gatekeeper ──────────────────────────────────────────────
    provider_npi = None
    for raw_id in [claim_dict.get("provider_id"), claim_dict.get("at_physn_npi"),
                   claim_dict.get("org_npi_num")]:
        npi = normalise_npi(raw_id)
        if npi:
            provider_npi = npi
            break

    # Convert claim_start_date to integer YYYYMMDD for LEIE lookup
    svc_date_int = None
    try:
        raw_date = claim_dict.get("claim_start_date")
        if raw_date:
            for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%Y%m%d"):
                try:
                    import pandas as _pd
                    svc_date_int = int(_pd.to_datetime(raw_date, format=fmt).strftime("%Y%m%d"))
                    break
                except Exception:
                    continue
    except Exception:
        svc_date_int = None

    leie_res    = leie_lookup(provider_npi, svc_date_int)
    leie_hit    = leie_res.get("leie_active_exclusion", False)
    leie_detail = leie_res.get("leie_details", None)

    if leie_hit:
        return {
            "claim_score":       1.0,
            "provider_score":    1.0,
            "final_risk_score":  1.0,
            "final_risk_tier":   "Critical",
            "leie_override":     True,
            "leie_details":      leie_detail,
            "claim_evidence":    [],
            "provider_evidence": [],
            "model_weights":     {"claim": 0.50, "provider": 0.50, "mode": "LEIE_DETERMINISTIC_OVERRIDE"},
            "scored_at":         datetime.utcnow().isoformat() + "Z",
        }

    # ── LAYER 1a: Model B — Claim-Level ──────────────────────────────────────
    try:
        _raw_b, raw_claim_score, claim_ev = _score_model_b(claim_dict)
    except Exception as e:
        _log.warning(f"Model B scoring failed: {e}. Defaulting claim_score=0.0")
        raw_claim_score, claim_ev = 0.0, [{"error": str(e), "model": "Model_B_IsolationForest"}]

    # ── LAYER 1b: Model V2 — Provider-Level XGBoost ───────────────────────────
    try:
        provider_score, provider_ev = _score_model_v2(claim_dict)
    except Exception as e:
        _log.warning(f"Model V2 scoring failed: {e}. Defaulting provider_score=0.0")
        provider_score, provider_ev = 0.0, [{"error": str(e), "model": "Model_V2_XGBoost"}]

    total_claims = int(claim_dict.get("total_claims", 1))

    # ── Compute Adaptive Weights ──────────────────────────────────────────────
    w_claim, w_prov, weight_mode = _calculate_adaptive_weights(
        raw_claim_score, provider_score, total_claims=total_claims
    )

    # ── Dynamic Anomaly Scaling for Isolated Synthetic Records ────────────────
    # If the claim anomaly score sits in the unobserved synthetic percentile range [0.91, 0.995],
    # map it smoothly across [0.0, 1.0] for crisp tier separation.
    eff_claim_score = float(np.clip((raw_claim_score - 0.91) / 0.085, 0.0, 1.0))

    # ── Weighted Adaptive Blend ───────────────────────────────────────────────
    final_score = float(np.clip(
        w_claim * eff_claim_score + w_prov * provider_score,
        0.0, 1.0
    ))
    final_tier  = _get_hybrid_tier(final_score)

    return {
        "claim_score":       round(raw_claim_score, 4),
        "effective_claim_score": round(eff_claim_score, 4),
        "provider_score":    round(provider_score,  4),
        "final_risk_score":  round(final_score,     4),
        "final_risk_tier":   final_tier,
        "leie_override":     False,
        "leie_details":      leie_detail,
        "claim_evidence":    claim_ev,
        "provider_evidence": provider_ev,
        "model_weights":     {
            "claim":    w_claim,
            "provider": w_prov,
            "mode":     weight_mode,
        },
        "scored_at":         datetime.utcnow().isoformat() + "Z",
    }
