"""
FastAPI Router — ClaimGuard Live ML Risk Engine
================================================
Endpoints:
  POST /api/v1/ml/predict          — Single Model B / Model C inference
  POST /api/v1/ml/predict_hybrid   — Hybrid Scoring Engine (Model B + Model V2 + LEIE Gatekeeper)
  POST /api/v1/ml/score_claim/{id} — Score DB claim live and record to risk_scores table
  GET  /api/v1/ml/health           — Health status of ML models & LEIE database
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.dependencies import get_current_active_user
from app.ml.hybrid_engine import score_hybrid
from app.ml.leie_checker import get_leie_index, normalise_npi, lookup as leie_lookup
from app.models.claim import Claim
from app.models.risk import RiskScore
from app.models.anomaly import Anomaly

router = APIRouter(prefix="/ml", tags=["ML Risk Engine"])


@router.get("/health")
def ml_health():
    """Return status of ML engines and LEIE database index."""
    try:
        leie_cnt = len(get_leie_index())
    except Exception:
        leie_cnt = 0
    return {
        "status": "healthy",
        "models_loaded": ["Model_B_IsolationForest", "Model_C_PDE_IsolationForest", "Model_V2_XGBoost"],
        "leie_records_indexed": leie_cnt,
        "engine_version": "v2.5-hybrid-adaptive",
    }


@router.post("/predict_hybrid")
def predict_hybrid_endpoint(payload: Dict[str, Any], _=Depends(get_current_active_user)):
    """
    Run Hybrid Payment Integrity Scoring on raw medical claim payload.
    Blends Model B (Claim Anomaly) + Model V2 (Provider XGBoost Fraud) + Layer 0 LEIE Gatekeeper.
    """
    try:
        result = score_hybrid(payload)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hybrid ML scoring failed: {str(e)}")


@router.post("/predict")
def predict_endpoint(payload: Dict[str, Any], _=Depends(get_current_active_user)):
    """
    Run single claim or PDE anomaly detection.
    """
    txn_type = str(payload.get("transaction_type", "MEDICAL_CLAIM")).upper()
    try:
        # Default to hybrid engine for medical claims as recommended
        if txn_type == "MEDICAL_CLAIM":
            return score_hybrid(payload)
        else:
            # PDE transaction
            from app.ml.feature_engine import build_model_c_features, features_to_array
            from app.ml.hybrid_engine import _iso_c, _imp_c, _scl_c, _feat_c, _calibrate_c, _risk_level_c
            feat_dict, meta = build_model_c_features(payload)
            X = features_to_array(feat_dict, _feat_c)
            X_imp = _imp_c.transform(X)
            X_scl = _scl_c.transform(X_imp)
            raw_score = float(_iso_c.decision_function(X_scl)[0])
            ml_score = _calibrate_c(raw_score)
            
            prscrbr_npi = normalise_npi(payload.get("prscrbr_id"))
            leie_res = leie_lookup(prscrbr_npi, None)
            
            return {
                "transaction_type": "PDE",
                "ml_risk_score": round(ml_score, 4),
                "ml_risk_level": _risk_level_c(ml_score),
                "leie_result": leie_res,
                "model_used": "Model C — PDE IsolationForest",
                "scored_at": datetime.utcnow().isoformat() + "Z",
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ML prediction failed: {str(e)}")


@router.post("/score_claim/{claim_id}")
def score_db_claim(claim_id: int, db: Session = Depends(get_db), _=Depends(get_current_active_user)):
    """
    Fetch claim from database, run live Hybrid ML scoring, update `risk_scores` table,
    and return detailed risk analysis.
    """
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    # Map database Claim model to raw ML payload schema
    from app.models.provider import Provider
    prv = db.query(Provider).filter(Provider.id == claim.provider_id).first()
    npi = prv.npi if prv and prv.npi else "1234567890"
    bene_id = f"PAT-{claim.patient_id}" if claim.patient_id else "BENE-001"
    claim_type_clean = (claim.claim_type or "carrier").lower().replace(" ", "_")
    if claim_type_clean not in ["carrier","dme","hha","hospice","inpatient","outpatient","snf"]:
        claim_type_clean = "inpatient" if "inpatient" in claim_type_clean else "outpatient"

    line_count = getattr(claim, 'line_count', None) or len(getattr(claim, 'line_items', [])) or 1
    diag_count = getattr(claim, 'diag_count', None) or 1
    proc_count = getattr(claim, 'proc_count', None) or line_count
    state_code = getattr(claim, 'state', None) or "OH"

    payload = {
        "transaction_type": "MEDICAL_CLAIM",
        "claim_id": claim.claim_number,
        "bene_id": bene_id,
        "provider_id": npi,
        "at_physn_npi": npi,
        "claim_type": claim_type_clean,
        "claim_start_date": str(claim.service_date or "2024-01-01"),
        "clm_pmt_amt": float(claim.total_paid_amount or claim.total_billed_amount or 0.0),
        "clm_tot_chrg_amt": float(claim.total_billed_amount or 0.0),
        "line_count": line_count,
        "diag_count": diag_count,
        "proc_count": proc_count,
        "state": state_code,
    }

    import os
    import httpx
    ml_url = os.environ.get("ML_SERVICE_URL", "http://localhost:8000").rstrip('/')
    
    # Check if we should route to external ML service
    if "localhost" not in ml_url and "127.0.0.1" not in ml_url:
        try:
            # External ML service uses /api/v1/predict_hybrid (not /api/v1/ml/predict_hybrid)
            resp = httpx.post(f"{ml_url}/api/v1/predict_hybrid", json=payload, timeout=30.0)
            resp.raise_for_status()
            res = resp.json()
            
            # Map external service response to internal format if needed
            # External service returns same structure as local, so direct use is OK
        except httpx.ConnectError as e:
            raise HTTPException(status_code=503, detail=f"Cannot connect to External ML Service at {ml_url}. Service may be down or unreachable: {str(e)}")
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail=f"External ML Service at {ml_url} timed out after 30 seconds")
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"External ML Service error at {ml_url}: {str(e)}")
    else:
        res = score_hybrid(payload)

    # Update or insert into RiskScore DB table
    risk_rec = db.query(RiskScore).filter(RiskScore.claim_id == claim.id).first()
    final_100 = round(res["final_risk_score"] * 100.0, 2)
    risk_level_str = res["final_risk_tier"].lower()

    explanation_str = (
        f"Hybrid Model Score: {final_100}/100 ({res['final_risk_tier']}). "
        f"Claim Anomaly: {res['claim_score']:.2%}, Provider Fraud: {res['provider_score']:.2%}. "
        f"Weighting: {res['model_weights'].get('mode', 'adaptive')}."
    )
    if res["leie_override"]:
        explanation_str = f"CRITICAL LEIE EXCLUSION: {res['leie_details']}"

    if not risk_rec:
        risk_rec = RiskScore(
            claim_id=claim.id,
            claim_number=claim.claim_number,
            overall_score=final_100,
            fraud_score=round(res["provider_score"] * 100.0, 2),
            waste_score=round(res["claim_score"] * 50.0, 2),
            abuse_score=round(res["claim_score"] * 80.0, 2),
            risk_level=risk_level_str,
            explanation=explanation_str,
            model_version="v2.5-hybrid-adaptive",
        )
        db.add(risk_rec)
    else:
        risk_rec.claim_number = claim.claim_number
        risk_rec.overall_score = final_100
        risk_rec.fraud_score = round(res["provider_score"] * 100.0, 2)
        risk_rec.risk_level = risk_level_str
        risk_rec.explanation = explanation_str
        risk_rec.model_version = "v2.5-hybrid-adaptive"

    db.commit()
    
    # ✅ Save or update complete details in ml_outputs table
    from app.models.ml_output import MLOutput
    from datetime import datetime
    
    # Check if ML output already exists for this claim
    existing_ml_output = db.query(MLOutput).filter(
        MLOutput.transaction_id == claim.claim_number,
        MLOutput.transaction_type == "MEDICAL_CLAIM"
    ).first()
    
    if existing_ml_output:
        # Update existing record
        existing_ml_output.bene_id = payload.get("bene_id")
        existing_ml_output.provider_id = payload.get("provider_id")
        existing_ml_output.claim_score = res.get("claim_score", 0.0)
        existing_ml_output.effective_claim_score = res.get("effective_claim_score", 0.0)
        existing_ml_output.claim_score_label = res.get("claim_score_label", "")
        existing_ml_output.provider_score = res.get("provider_score", 0.0)
        existing_ml_output.provider_score_label = res.get("provider_score_label", "")
        existing_ml_output.final_risk_score = res.get("final_risk_score", 0.0)
        existing_ml_output.final_risk_tier = res.get("final_risk_tier", "LOW")
        existing_ml_output.model_weights = res.get("model_weights", {})
        existing_ml_output.leie_override = res.get("leie_override", False)
        existing_ml_output.leie_details = res.get("leie_details")
        existing_ml_output.claim_evidence = res.get("claim_evidence", {})
        existing_ml_output.provider_evidence = res.get("provider_evidence", {})
        existing_ml_output.explanation = explanation_str
        existing_ml_output.disclaimer = res.get("disclaimer", "")
        existing_ml_output.scored_at = datetime.utcnow()
        ml_output = existing_ml_output
        print(f"[ML OUTPUT] Updated existing ML scoring in ml_outputs table (ID: {ml_output.id})")
    else:
        # Create new record
        ml_output = MLOutput(
            transaction_type="MEDICAL_CLAIM",
            transaction_id=claim.claim_number,
            bene_id=payload.get("bene_id"),
            provider_id=payload.get("provider_id"),
            claim_score=res.get("claim_score", 0.0),
            effective_claim_score=res.get("effective_claim_score", 0.0),
            claim_score_label=res.get("claim_score_label", ""),
            provider_score=res.get("provider_score", 0.0),
            provider_score_label=res.get("provider_score_label", ""),
            final_risk_score=res.get("final_risk_score", 0.0),
            final_risk_tier=res.get("final_risk_tier", "LOW"),
            model_weights=res.get("model_weights", {}),
            leie_override=res.get("leie_override", False),
            leie_details=res.get("leie_details"),
            claim_evidence=res.get("claim_evidence", {}),
            provider_evidence=res.get("provider_evidence", {}),
            explanation=explanation_str,
            disclaimer=res.get("disclaimer", ""),
            scored_at=datetime.utcnow(),
        )
        db.add(ml_output)
        print(f"[ML OUTPUT] Saved new ML scoring to ml_outputs table")
    
    db.commit()
    db.refresh(ml_output)
    if not existing_ml_output:
        print(f"[ML OUTPUT] ML output ID: {ml_output.id}")

    return {
        "claim_id": claim.id,
        "claim_number": claim.claim_number,
        "hybrid_result": res,
        "db_risk_score_id": risk_rec.id,
        "ml_output_id": ml_output.id,
    }
