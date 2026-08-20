"""
CTS Hackathon — Healthcare Anomaly Detection API
==================================================
POST /api/v1/predict         — Claim-level scoring (Model B or C)
POST /api/v1/predict_hybrid  — Hybrid scoring: Model B + XGBoost v2 blended score

Accepts raw medical claim or PDE transaction fields.
Internally builds all required features, scores with the appropriate
anomaly model, checks LEIE, and returns a complete risk assessment.

Models used
-----------
  MEDICAL_CLAIM → Model B (IsolationForest, 59 features)
  PDE           → Model C (IsolationForest, 32 features)
  HYBRID        → Model B + XGBoost v2 CMS Peer-Aware Adaptive Engine

Run:
    uvicorn backend.main:app --reload --port 8000
"""

from __future__ import annotations

import json
import pickle
import warnings
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator

warnings.filterwarnings(
    "ignore",
    message="X does not have valid feature names",
    category=UserWarning,
)

# ── local modules ─────────────────────────────────────────────────────────────
from backend.feature_engine import (
    build_model_b_features,
    build_model_c_features,
    features_to_array,
)
from backend.leie_checker import (
    apply_adjustment,
    get_leie_index,
    lookup as leie_lookup,
    normalise_npi,
)

# ── paths ─────────────────────────────────────────────────────────────────────
_HERE     = Path(__file__).resolve().parent
ROOT      = _HERE.parent
MODEL_B   = ROOT / "models" / "model_b_claim"
MODEL_C   = ROOT / "models" / "model_c_pde"
REF_DIR   = ROOT / "data" / "processed" / "reference"

# ── startup: load all artefacts once ─────────────────────────────────────────

def _pkl(p: Path):
    with open(p, "rb") as f:
        return pickle.load(f)

def _json(p: Path):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# Model B artefacts
_iso_b   = _pkl(MODEL_B / "isolation_forest.pkl")
_imp_b   = _pkl(MODEL_B / "imputer.pkl")
_scl_b   = _pkl(MODEL_B / "scaler.pkl")
_feat_b  = _pkl(MODEL_B / "feature_columns.pkl")
_meta_b  = _json(MODEL_B / "metadata.json")
_calib_b: dict[str, np.ndarray] = _pkl(MODEL_B / "score_calibration.pkl")

# Model C artefacts
_iso_c   = _pkl(MODEL_C / "isolation_forest.pkl")
_imp_c   = _pkl(MODEL_C / "imputer.pkl")
_scl_c   = _pkl(MODEL_C / "scaler.pkl")
_feat_c  = _pkl(MODEL_C / "feature_columns.pkl")
_meta_c  = _json(MODEL_C / "metadata.json")
_calib_c: dict[str, np.ndarray] = _pkl(MODEL_C / "pde_score_calibration.pkl")

# Reference data
_stats_b = _json(REF_DIR / "medical_claim_type_stats.json")
_calib_pde_meta = _json(REF_DIR / "pde_calibration.json")

# Pre-warm LEIE index
get_leie_index()

# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="CTS Healthcare Anomaly Detection API",
    description=(
        "Scores medical claims (Model B) and PDE prescriptions (Model C) "
        "for statistical anomalies. Includes LEIE exclusion verification. "
        "All scores are statistical anomaly indicators — not fraud determinations."
    ),
    version="1.0.0",
)


# ── request models ────────────────────────────────────────────────────────────

class MedicalClaimRequest(BaseModel):
    transaction_type: Literal["MEDICAL_CLAIM"]
    claim_id:         str | int
    bene_id:          str | int
    provider_id:      str | int | None = None
    at_physn_npi:     str | int | None = None
    org_npi_num:      str | int | None = None
    claim_type:       Literal["carrier","dme","hha","hospice","inpatient","outpatient","snf"]
    claim_start_date: str                             # YYYY-MM-DD
    claim_end_date:   str | None = None
    clm_pmt_amt:      float
    clm_tot_chrg_amt: float
    line_count:       int   | None = None
    unit_count:       float | None = None
    diag_count:       int   | None = None
    proc_count:       int   | None = None

    @model_validator(mode="after")
    def _compute_duration(self):
        try:
            if self.claim_end_date:
                s = pd.to_datetime(self.claim_start_date)
                e = pd.to_datetime(self.claim_end_date)
                self._duration = max(0, (e - s).days)
            else:
                self._duration = 0
        except Exception:
            self._duration = 0
        return self

    model_config = {"arbitrary_types_allowed": True}


class PDERequest(BaseModel):
    transaction_type:   Literal["PDE"]
    pde_id:             str | int
    bene_id:            str | int
    prscrbr_id:         str | int
    srvc_dt:            str                   # DD-Mon-YYYY  or  YYYY-MM-DD
    qty_dspnsd_num:     float
    days_suply_num:     float
    fill_num:           int
    tot_rx_cst_amt:     float
    ptnt_pay_amt:       float = 0.0
    cvrd_d_plan_pd_amt: float = 0.0
    ncvrd_plan_pd_amt:  float = 0.0
    gdc_blw_oopt_amt:   float = 0.0
    gdc_abv_oopt_amt:   float = 0.0
    othr_troop_amt:     float = 0.0
    lics_amt:           float = 0.0
    plro_amt:           float = 0.0
    brnd_gnrc_cd:       str | None = None
    phrmcy_srvc_type_cd: int | None = None


# Union request
class PredictRequest(BaseModel):
    transaction_type: str
    model_config = {"extra": "allow"}


# ── response models ───────────────────────────────────────────────────────────

class LEIEResult(BaseModel):
    leie_match:            bool
    leie_active_exclusion: bool
    leie_status:           str
    leie_details:          str
    exclusion_type:        str | None
    exclusion_type_label:  str | None
    exclusion_date:        int | None
    reinstatement_date:    int | None
    npi_used:              str | None


class PredictResponse(BaseModel):
    model_config = {"protected_namespaces": (), "arbitrary_types_allowed": True}

    transaction_type:   str
    transaction_id:     str
    bene_id:            str
    provider_id:        str | None
    ml_risk_score:      float
    ml_risk_level:      str
    leie_result:        LEIEResult
    leie_adjustment:    float
    final_risk_score:   float
    final_risk_level:   str
    evidence:           list[dict]
    explanation:        str
    model_used:         str
    disclaimer:         str
    scored_at:          str


# ── helpers ───────────────────────────────────────────────────────────────────

def _risk_level_b(score: float) -> str:
    """Model B risk level from calibrated score."""
    if score >= 80:  return "CRITICAL"
    if score >= 60:  return "HIGH"
    if score >= 40:  return "MEDIUM"
    return "LOW"


def _risk_level_c(score: float) -> str:
    """Model C risk level from calibrated score."""
    if score >= 80:  return "CRITICAL"
    if score >= 60:  return "HIGH"
    if score >= 40:  return "MEDIUM"
    return "LOW"


def _pct_rank_vec(value: float, ref: np.ndarray) -> float:
    n = len(ref)
    n_below = float(np.searchsorted(ref, value, side="left"))
    n_right = float(np.searchsorted(ref, value, side="right"))
    n_equal = n_right - n_below
    return float(np.clip((n_below + n_equal / 2) / n * 100, 0, 100))


def _calibrate_b(raw_score: float, claim_type: str) -> float:
    ref = _calib_b.get(claim_type, _calib_b.get("overall", list(_calib_b.values())[0]))
    pct = _pct_rank_vec(raw_score, ref)
    return float((1 - pct / 100) * 100)


def _calibrate_c(raw_score: float) -> float:
    ref = _calib_c.get("overall")
    if ref is None:
        ref = list(_calib_c.values())[0]
    pct = _pct_rank_vec(raw_score, ref)
    return float((1 - pct / 100) * 100)


def _date_to_int(date_str: str | None) -> int | None:
    if not date_str:
        return None
    try:
        for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%Y%m%d"):
            try:
                return int(pd.to_datetime(date_str, format=fmt).strftime("%Y%m%d"))
            except Exception:
                pass
    except Exception:
        pass
    return None


def _extract_shap_evidence(feat_dict: dict, feat_cols: list,
                            iso, imp, scl) -> list[dict]:
    """
    Compute top 5 SHAP anomaly drivers and top 3 normalizing features.
    Returns list of evidence dicts sorted by anomaly contribution.
    """
    try:
        import shap
        X = features_to_array(feat_dict, feat_cols)
        X_imp = imp.transform(X)
        X_scl = scl.transform(X_imp)
        explainer = shap.TreeExplainer(iso)
        sv = np.array(explainer.shap_values(X_scl))[0]

        paired = sorted(
            zip(feat_cols, sv.tolist(), X_imp[0].tolist()),
            key=lambda x: x[1]
        )
        evidence = []
        # Top 5 anomaly drivers (most negative SHAP)
        for feat_name, shap_val, raw_val in paired[:5]:
            evidence.append({
                "feature":       feat_name,
                "value":         round(float(raw_val), 4),
                "shap_contribution": round(float(shap_val), 6),
                "driver_type":   "anomaly_driver",
                "interpretation": (
                    f"{feat_name} = {raw_val:.3g} deviates from training population norm. "
                    f"Statistical anomaly evidence (SHAP: {shap_val:+.4f})."
                ),
            })
        # Top 3 normal drivers (most positive SHAP)
        for feat_name, shap_val, raw_val in sorted(paired, key=lambda x: -x[1])[:3]:
            evidence.append({
                "feature":       feat_name,
                "value":         round(float(raw_val), 4),
                "shap_contribution": round(float(shap_val), 6),
                "driver_type":   "normal_driver",
                "interpretation": (
                    f"{feat_name} = {raw_val:.3g} is within typical training population range. "
                    f"Normalising factor (SHAP: {shap_val:+.4f})."
                ),
            })
        return evidence
    except Exception as exc:
        return [{"error": f"SHAP computation failed: {exc}",
                 "driver_type": "unavailable"}]


# ── main endpoint ─────────────────────────────────────────────────────────────

@app.post("/api/v1/predict", response_model=PredictResponse)
async def predict(payload: dict):
    """
    Score a single medical claim or PDE transaction.

    Send raw transaction fields — the API builds all required features
    internally using frozen reference statistics and pre-computed
    historical feature tables.
    """
    txn_type = str(payload.get("transaction_type", "")).upper()

    if txn_type == "MEDICAL_CLAIM":
        return _predict_medical(payload)
    elif txn_type == "PDE":
        return _predict_pde(payload)
    else:
        raise HTTPException(
            status_code=422,
            detail=f"transaction_type must be 'MEDICAL_CLAIM' or 'PDE', got '{txn_type}'"
        )


def _predict_medical(raw: dict) -> PredictResponse:
    # ── validate required fields ───────────────────────────────────────────
    for req in ["bene_id", "claim_type", "claim_start_date",
                "clm_pmt_amt", "clm_tot_chrg_amt"]:
        if raw.get(req) is None:
            raise HTTPException(status_code=422, detail=f"Missing required field: {req}")

    claim_type = str(raw["claim_type"]).lower()
    if claim_type not in ["carrier","dme","hha","hospice","inpatient","outpatient","snf"]:
        raise HTTPException(status_code=422,
                            detail=f"Invalid claim_type: {claim_type}")

    # Duration
    raw["claim_duration_days"] = 0
    try:
        if raw.get("claim_end_date"):
            s = pd.to_datetime(raw["claim_start_date"])
            e = pd.to_datetime(raw["claim_end_date"])
            raw["claim_duration_days"] = max(0, (e - s).days)
    except Exception:
        pass

    # ── build features ─────────────────────────────────────────────────────
    feat_dict, meta = build_model_b_features(raw)

    # ── score ──────────────────────────────────────────────────────────────
    X     = features_to_array(feat_dict, _feat_b)
    X_imp = _imp_b.transform(X)
    X_scl = _scl_b.transform(X_imp)
    raw_score = float(_iso_b.decision_function(X_scl)[0])

    # Calibrated ML risk score
    ml_score = _calibrate_b(raw_score, claim_type)
    ml_level = _risk_level_b(ml_score)

    # ── LEIE check ─────────────────────────────────────────────────────────
    provider_npi = None
    for raw_id in [raw.get("provider_id"), raw.get("at_physn_npi"),
                   raw.get("org_npi_num")]:
        npi = normalise_npi(raw_id)
        if npi:
            provider_npi = npi
            break

    svc_date_int = _date_to_int(raw.get("claim_start_date"))
    leie_res     = leie_lookup(provider_npi, svc_date_int)
    adj_score, adj_reason = apply_adjustment(ml_score, leie_res)
    leie_adj  = round(adj_score - ml_score, 4)
    final_lvl = _risk_level_b(adj_score)

    # ── SHAP evidence ──────────────────────────────────────────────────────
    evidence = _extract_shap_evidence(feat_dict, _feat_b, _iso_b, _imp_b, _scl_b)

    return PredictResponse(
        transaction_type  = "MEDICAL_CLAIM",
        transaction_id    = str(raw.get("claim_id", "UNKNOWN")),
        bene_id           = str(raw.get("bene_id", "")),
        provider_id       = provider_npi or str(raw.get("provider_id", "") or ""),
        ml_risk_score     = round(ml_score, 4),
        ml_risk_level     = ml_level,
        leie_result       = LEIEResult(
            leie_match            = leie_res["leie_match"],
            leie_active_exclusion = leie_res["leie_active_exclusion"],
            leie_status           = leie_res["leie_status"],
            leie_details          = leie_res["leie_details"],
            exclusion_type        = leie_res["exclusion_type"],
            exclusion_type_label  = leie_res["exclusion_type_label"],
            exclusion_date        = leie_res["exclusion_date"],
            reinstatement_date    = leie_res["reinstatement_date"],
            npi_used              = provider_npi,
        ),
        leie_adjustment   = leie_adj,
        final_risk_score  = round(adj_score, 4),
        final_risk_level  = final_lvl,
        evidence          = evidence,
        explanation       = adj_reason,
        model_used        = "Model B — Medical Claim IsolationForest (n_estimators=300)",
        disclaimer        = (
            "Risk scores represent statistical anomaly indicators based on "
            "deviation from training population patterns. "
            "They are NOT proof of fraud, abuse, or policy violation. "
            "All findings require human review before any compliance action."
        ),
        scored_at         = datetime.utcnow().isoformat() + "Z",
    )


def _predict_pde(raw: dict) -> PredictResponse:
    # ── validate required fields ───────────────────────────────────────────
    for req in ["bene_id", "prscrbr_id", "srvc_dt",
                "qty_dspnsd_num", "days_suply_num", "fill_num", "tot_rx_cst_amt"]:
        if raw.get(req) is None:
            raise HTTPException(status_code=422, detail=f"Missing required field: {req}")

    # ── build features ─────────────────────────────────────────────────────
    feat_dict, meta = build_model_c_features(raw)

    # ── score ──────────────────────────────────────────────────────────────
    X     = features_to_array(feat_dict, _feat_c)
    X_imp = _imp_c.transform(X)
    X_scl = _scl_c.transform(X_imp)
    raw_score = float(_iso_c.decision_function(X_scl)[0])

    ml_score = _calibrate_c(raw_score)
    ml_level = _risk_level_c(ml_score)

    # ── LEIE check ─────────────────────────────────────────────────────────
    prscrbr_npi  = normalise_npi(raw.get("prscrbr_id"))
    svc_date_int = _date_to_int(str(raw.get("srvc_dt", "")))
    leie_res     = leie_lookup(prscrbr_npi, svc_date_int)
    adj_score, adj_reason = apply_adjustment(ml_score, leie_res)
    leie_adj  = round(adj_score - ml_score, 4)
    final_lvl = _risk_level_c(adj_score)

    # ── SHAP evidence ──────────────────────────────────────────────────────
    evidence = _extract_shap_evidence(feat_dict, _feat_c, _iso_c, _imp_c, _scl_c)

    return PredictResponse(
        transaction_type  = "PDE",
        transaction_id    = str(raw.get("pde_id", "UNKNOWN")),
        bene_id           = str(raw.get("bene_id", "")),
        provider_id       = prscrbr_npi or str(raw.get("prscrbr_id", "")),
        ml_risk_score     = round(ml_score, 4),
        ml_risk_level     = ml_level,
        leie_result       = LEIEResult(
            leie_match            = leie_res["leie_match"],
            leie_active_exclusion = leie_res["leie_active_exclusion"],
            leie_status           = leie_res["leie_status"],
            leie_details          = leie_res["leie_details"],
            exclusion_type        = leie_res["exclusion_type"],
            exclusion_type_label  = leie_res["exclusion_type_label"],
            exclusion_date        = leie_res["exclusion_date"],
            reinstatement_date    = leie_res["reinstatement_date"],
            npi_used              = prscrbr_npi,
        ),
        leie_adjustment   = leie_adj,
        final_risk_score  = round(adj_score, 4),
        final_risk_level  = final_lvl,
        evidence          = evidence,
        explanation       = adj_reason,
        model_used        = "Model C — PDE IsolationForest (n_estimators=300)",
        disclaimer        = (
            "Risk scores represent statistical anomaly indicators based on "
            "deviation from training population patterns. "
            "They are NOT proof of fraud, abuse, or policy violation. "
            "All findings require human review before any compliance action."
        ),
        scored_at         = datetime.utcnow().isoformat() + "Z",
    )


# ── health endpoint ───────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status":   "ok",
        "model_b":  _meta_b.get("trained_at"),
        "model_c":  _meta_c.get("trained_at"),
        "leie_npis": len(get_leie_index()),
    }


# ── hybrid endpoint ────────────────────────────────────────────────────────────

@app.post("/api/v1/predict_hybrid")
async def predict_hybrid(payload: dict):
    """
    Hybrid Payment Integrity Score — Model B + XGBoost v2 combined.

    Accepts the same MEDICAL_CLAIM fields as /api/v1/predict.
    Runs two models in parallel and returns a weighted blend:

        final_risk_score = 0.40 × claim_score (Model B)
                         + 0.60 × provider_score (XGBoost v2)

    Layer 0: If the provider NPI matches an active LEIE exclusion,
             final_risk_score is overridden to 1.0 (Critical).

    Example request body:
    {
      "transaction_type": "MEDICAL_CLAIM",
      "claim_id": "CLM-001",
      "bene_id": "BENE-123",
      "provider_id": "1234567890",
      "claim_type": "inpatient",
      "claim_start_date": "2009-01-15",
      "claim_end_date": "2009-01-20",
      "clm_pmt_amt": 12500.00,
      "clm_tot_chrg_amt": 38000.00,
      "line_count": 10,
      "diag_count": 5,
      "proc_count": 4
    }
    """
    from backend.hybrid_engine import score_hybrid

    txn_type = str(payload.get("transaction_type", "")).upper()
    if txn_type not in ("MEDICAL_CLAIM", ""):
        raise HTTPException(
            status_code=422,
            detail="/predict_hybrid only supports MEDICAL_CLAIM transactions. Use /predict for PDE."
        )

    try:
        result = score_hybrid(payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Hybrid scoring failed: {exc}")

    # Build a human-readable explanation
    tier = result["final_risk_tier"]
    if result["leie_override"]:
        explanation = (
            "CRITICAL: Provider is listed on the HHS OIG LEIE active exclusion list. "
            "Payment must be blocked immediately. Score overridden to 1.0."
        )
    elif tier == "Critical":
        explanation = (
            f"CRITICAL risk detected. Claim anomaly score: {result['claim_score']:.2%}, "
            f"Provider behavioral fraud probability: {result['provider_score']:.2%}. "
            "Both models indicate high-confidence fraud patterns. Immediate review required."
        )
    elif tier == "High":
        explanation = (
            f"HIGH risk. Claim score: {result['claim_score']:.2%}, "
            f"Provider score: {result['provider_score']:.2%}. "
            "Significant anomaly detected. Prioritise for investigation."
        )
    elif tier == "Medium":
        explanation = (
            f"MEDIUM risk. Claim score: {result['claim_score']:.2%}, "
            f"Provider score: {result['provider_score']:.2%}. "
            "Some anomaly indicators present. Monitor and review if pattern persists."
        )
    else:
        explanation = (
            f"LOW risk. Claim score: {result['claim_score']:.2%}, "
            f"Provider score: {result['provider_score']:.2%}. "
            "Both models indicate typical behaviour. No immediate action required."
        )

    return {
        "transaction_type":   str(payload.get("transaction_type", "MEDICAL_CLAIM")),
        "transaction_id":     str(payload.get("claim_id", "UNKNOWN")),
        "bene_id":            str(payload.get("bene_id", "")),
        "provider_id":        str(payload.get("provider_id") or payload.get("at_physn_npi") or ""),
        # ── Individual model scores ──────────────────────────────────────────
        "claim_score":        result["claim_score"],
        "effective_claim_score": result.get("effective_claim_score", result["claim_score"]),
        "claim_score_label":  "Model B — IsolationForest (claim-level anomaly)",
        "provider_score":     result["provider_score"],
        "provider_score_label": "Model V2 — XGBoost (provider behavioral fraud)",
        # ── Hybrid blended score ─────────────────────────────────────────────
        "final_risk_score":   result["final_risk_score"],
        "final_risk_tier":    result["final_risk_tier"],
        "model_weights":      result["model_weights"],
        # ── LEIE ─────────────────────────────────────────────────────────────
        "leie_override":      result["leie_override"],
        "leie_details":       result["leie_details"],
        # ── Explainability ───────────────────────────────────────────────────
        "claim_evidence":     result["claim_evidence"],
        "provider_evidence":  result["provider_evidence"],
        # ── Meta ─────────────────────────────────────────────────────────────
        "explanation":        explanation,
        "disclaimer":         (
            "Risk scores represent statistical anomaly indicators. "
            "They are NOT proof of fraud. All findings require human review."
        ),
        "scored_at":          result["scored_at"],
    }
