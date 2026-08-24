"""
repository.py
=============

ML Repository Abstraction Layer.
Decouples prediction tools and services from the underlying ML model source
(Mock Dummy Data vs. Real XGBoost Model).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from app.schemas.agentic.tool import (
    MLRiskResponse,
    MLScenarioResponse,
    ShapFeature,
    ChangedFeatureDetail,
)
from app.tools.utils.tool_helpers import logger


class BaseMLRepository(ABC):
    """Abstract interface for ML model prediction and scenario simulation."""

    @abstractmethod
    def get_risk_prediction(self, claim_id: str) -> Optional[MLRiskResponse]:
        """Retrieve or compute risk score and SHAP explanations for a claim."""
        pass

    @abstractmethod
    def simulate_scenario(
        self, claim_id: str, changes: Dict[str, Any]
    ) -> Optional[MLScenarioResponse]:
        """Simulate counterfactual feature alterations on a claim."""
        pass


class MockMLRepository(BaseMLRepository):
    """
    Mock ML Repository providing realistic structured fraud risk outputs
    and counterfactual scenario simulations for development and testing.
    """

    def __init__(self) -> None:
        # Coherent dummy dataset centered on claim C10234
        self._mock_claims: Dict[str, Dict[str, Any]] = {
            "C10234": {
                "risk_score": 0.87,
                "risk_level": "HIGH",
                "features": {
                    "procedure_frequency": 520,
                    "claim_amount": 4800.0,
                    "claim_amount_vs_peer": 2.4,
                    "prior_denial_rate": 0.28,
                    "conservative_therapy_documented": 0,
                    "imaging_interval_days": 12,
                },
                "shap_features": [
                    ShapFeature(
                        feature="procedure_frequency",
                        impact=0.21,
                        direction="increases_risk",
                        description="Provider frequency (520) exceeds 95th peer percentile (310)",
                    ),
                    ShapFeature(
                        feature="claim_amount_vs_peer",
                        impact=0.18,
                        direction="increases_risk",
                        description="Billed amount ($4,800) is 2.4x higher than peer average ($1,850)",
                    ),
                    ShapFeature(
                        feature="prior_denial_rate",
                        impact=0.12,
                        direction="increases_risk",
                        description="Prior claims denial rate of 28% for lumbar procedures",
                    ),
                    ShapFeature(
                        feature="conservative_therapy_documented",
                        impact=0.15,
                        direction="increases_risk",
                        description="Lack of documented 6-week conservative physical therapy",
                    ),
                ],
                "model_version": "xgboost_fraud_v1.0",
            },
            "C99999": {
                "risk_score": 0.15,
                "risk_level": "LOW",
                "features": {
                    "procedure_frequency": 95,
                    "claim_amount": 1200.0,
                    "claim_amount_vs_peer": 0.8,
                    "prior_denial_rate": 0.02,
                    "conservative_therapy_documented": 1,
                    "imaging_interval_days": 90,
                },
                "shap_features": [
                    ShapFeature(
                        feature="conservative_therapy_documented",
                        impact=-0.25,
                        direction="decreases_risk",
                        description="Full 8-week physical therapy trial documented",
                    ),
                    ShapFeature(
                        feature="procedure_frequency",
                        impact=-0.15,
                        direction="decreases_risk",
                        description="Procedure frequency within normal peer distribution",
                    ),
                ],
                "model_version": "xgboost_fraud_v1.0",
            },
        }

    def get_risk_prediction(self, claim_id: str) -> Optional[MLRiskResponse]:
        claim_data = self._mock_claims.get(claim_id)
        if not claim_data:
            return None

        return MLRiskResponse(
            status="success",
            tool="ml_risk",
            claim_id=claim_id,
            risk_score=claim_data["risk_score"],
            risk_level=claim_data["risk_level"],
            shap_features=claim_data["shap_features"],
            model_version=claim_data.get("model_version", "xgboost_fraud_v1.0"),
        )

    def simulate_scenario(
        self, claim_id: str, changes: Dict[str, Any]
    ) -> Optional[MLScenarioResponse]:
        claim_data = self._mock_claims.get(claim_id)
        if not claim_data:
            return None

        original_score = claim_data["risk_score"]
        current_features = dict(claim_data["features"])
        changed_features_detail: Dict[str, ChangedFeatureDetail] = {}

        # Heuristic sensitivity calculation for counterfactuals
        score_delta = 0.0

        for feat_name, new_val in changes.items():
            if feat_name in current_features:
                orig_val = current_features[feat_name]
                changed_features_detail[feat_name] = ChangedFeatureDetail(
                    original=orig_val, scenario=new_val
                )

                if feat_name == "procedure_frequency":
                    # Dropping from 520 to 180 yields -0.26
                    delta_ratio = (float(new_val) - float(orig_val)) / 520.0
                    score_delta += delta_ratio * 0.40
                elif feat_name == "claim_amount":
                    delta_ratio = (float(new_val) - float(orig_val)) / 4800.0
                    score_delta += delta_ratio * 0.25
                elif feat_name == "conservative_therapy_documented":
                    if new_val in (1, True, "yes"):
                        score_delta -= 0.18
                    elif new_val in (0, False, "no"):
                        score_delta += 0.15
                elif feat_name == "prior_denial_rate":
                    score_delta += (float(new_val) - float(orig_val)) * 0.35
                else:
                    # General numeric adjustment
                    try:
                        delta_ratio = (float(new_val) - float(orig_val)) / (float(orig_val) or 1.0)
                        score_delta += delta_ratio * 0.10
                    except (ValueError, TypeError):
                        pass
            else:
                changed_features_detail[feat_name] = ChangedFeatureDetail(
                    original="N/A", scenario=new_val
                )

        scenario_score = round(max(0.01, min(0.99, original_score + score_delta)), 2)
        difference = round(scenario_score - original_score, 2)

        return MLScenarioResponse(
            status="success",
            tool="ml_scenario",
            claim_id=claim_id,
            original_score=original_score,
            scenario_score=scenario_score,
            difference=difference,
            changed_features=changed_features_detail,
            is_causal=False,
            explanation=(
                "Scenario simulation demonstrates model sensitivity. SHAP and scenario tests "
                "are statistical explanations and do not prove causality or legal fraud."
            ),
        )


class RealMLRepository(BaseMLRepository):
    """
    Real ML Repository interface connecting to a trained XGBoost model and SHAP explainer.
    Plug your trained artifact/endpoint here when migrating from mock to production.
    """

    def __init__(self, model_path: Optional[str] = None) -> None:
        self.model_path = model_path
        self.model = None
        self.explainer = None
        self._load_model()

    def _load_model(self) -> None:
        """Load XGBoost model artifact if available."""
        if not self.model_path:
            logger.warning("RealMLRepository initialized without model_path.")
            return
        try:
            # Placeholder for actual model loading:
            # import xgboost as xgb
            # self.model = xgb.Booster()
            # self.model.load_model(self.model_path)
            pass
        except Exception as e:
            logger.error("Failed to load real ML model from %s: %s", self.model_path, e)

    def get_risk_prediction(self, claim_id: str) -> Optional[MLRiskResponse]:
        if self.model is None:
            raise RuntimeError(
                "Real ML model is not loaded. Please configure model path or set DATA_MODE=mock."
            )
        # Real inference and SHAP computation logic goes here
        raise NotImplementedError("Real ML model inference logic not yet connected.")

    def simulate_scenario(
        self, claim_id: str, changes: Dict[str, Any]
    ) -> Optional[MLScenarioResponse]:
        if self.model is None:
            raise RuntimeError(
                "Real ML model is not loaded. Please configure model path or set DATA_MODE=mock."
            )
        # Real scenario feature perturbation & re-scoring goes here
        raise NotImplementedError("Real ML scenario logic not yet connected.")


class LiveMLRepository(BaseMLRepository):
    """
    Live ML Repository interface connecting to the external Render ML service.
    Queries the /api/v1/predict_hybrid endpoint with enriched claim data.
    """

    def __init__(self, service_url: Optional[str] = None, timeout: float = 10.0) -> None:
        import os
        from app.tools.config import settings
        self.service_url = service_url or getattr(settings, "ML_SERVICE_URL", os.environ.get("ML_SERVICE_URL", "http://localhost:8000"))
        self.timeout = timeout

    def get_risk_prediction(self, claim_id: str) -> Optional[MLRiskResponse]:
        import httpx
        from app.tools.config import settings
        from app.services.agentic.database.database_service import DatabaseService

        db_service = DatabaseService()
        claim = db_service.get_claim(claim_id)
        if not claim:
            logger.warning("Claim %s not found in Database repository. Cannot query live ML.", claim_id)
            return None

        # Ensure NPI is 10 digits for the external service, fallback to a valid one if missing/invalid
        raw_provider_id = str(claim.get("provider_id", "1033472386"))
        npi_to_use = raw_provider_id if raw_provider_id.isdigit() and len(raw_provider_id) == 10 else "1033472386"

        # Map the real ClaimGuard claim fields into these ML fields exactly as expected
        payload = {
            "transaction_type": claim.get("transaction_type", "MEDICAL_CLAIM"),
            "claim_id": claim.get("claim_id", claim_id),
            "bene_id": claim.get("patient_id", "BENE-005"),
            "provider_id": npi_to_use,
            "at_physn_npi": claim.get("at_physn_npi", npi_to_use),
            "claim_type": claim.get("claim_type", "carrier"),
            "claim_start_date": claim.get("service_date", "2026-03-01"),
            "claim_end_date": claim.get("service_date", "2026-03-01"),
            "clm_pmt_amt": float(claim.get("billed_amount", 200.0)),
            "clm_tot_chrg_amt": float(claim.get("total_charge", claim.get("billed_amount", 250.0))),
            "line_count": int(claim.get("line_count", 2)),
            "diag_count": int(claim.get("diag_count", 1)),
            "proc_count": int(claim.get("proc_count", 1)),
            "state": claim.get("state", "OH")
        }

        url = f"{self.service_url.rstrip('/')}/api/v1/predict_hybrid"
        
        # Output exact request payload for verification (secrets/PII already excluded as this is internal ID-based)
        print("\n--- EXACT REQUEST PAYLOAD SENT TO predict_hybrid ---")
        import json
        print(json.dumps(payload, indent=2))
        print("----------------------------------------------------\n")
        
        logger.info("Sending Live ML request to %s for claim %s", url, claim_id)

        try:
            response = httpx.post(url, json=payload, timeout=self.timeout)
            
            print(f"HTTP Status: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            
            if response.status_code != 200:
                logger.error("Live ML Service returned status %d: %s", response.status_code, response.text)
                raise httpx.HTTPStatusError(
                    f"ML service error: {response.status_code}",
                    request=response.request,
                    response=response
                )
            
            res_data = response.json()
            logger.info("Live ML Service successfully returned score for claim %s", claim_id)

            # Build shap features from evidence
            shap_feats = []
            if "claim_evidence" in res_data:
                for ev in res_data["claim_evidence"]:
                    if "feature" in ev:
                        shap_feats.append(
                            ShapFeature(
                                feature=ev.get("feature", "unknown"),
                                impact=ev.get("shap_contribution", 0.0),
                                direction="increases_risk" if ev.get("shap_contribution", 0.0) > 0 else "decreases_risk",
                                description=f"Model B Anomaly Driver: {ev.get('feature')}"
                            )
                        )
            if "provider_evidence" in res_data:
                for ev in res_data["provider_evidence"]:
                    if "feature" in ev:
                        shap_feats.append(
                            ShapFeature(
                                feature=ev.get("feature", "unknown"),
                                impact=ev.get("importance", 0.0),
                                direction="increases_risk",
                                description=f"Provider Behavior Risk: {ev.get('feature')} = {ev.get('value')}"
                            )
                        )

            # Add LEIE override as a strong indicator if active
            if res_data.get("leie_override"):
                shap_feats.append(
                    ShapFeature(
                        feature="LEIE_MATCH",
                        impact=1.0,
                        direction="increases_risk",
                        description=f"CRITICAL: {res_data.get('leie_details', 'Provider on Exclusion List')}"
                    )
                )

            # Map to MLRiskResponse
            return MLRiskResponse(
                status="success",
                tool="ml_risk",
                claim_id=claim_id,
                risk_score=res_data.get("final_risk_score", res_data.get("ml_risk_score", 0.87)),
                risk_level=res_data.get("final_risk_tier", res_data.get("ml_risk_level", "HIGH")).upper(),
                shap_features=shap_feats,
                model_version=res_data.get("model_used", "hybrid_model_v2.5")
            )
        except Exception as exc:
            logger.exception("Error calling Live ML service for claim %s", claim_id)
            raise exc

    def simulate_scenario(
        self, claim_id: str, changes: Dict[str, Any]
    ) -> Optional[MLScenarioResponse]:
        # Return mock simulate scenario since Render model does not have scenario endpoints
        return MockMLRepository().simulate_scenario(claim_id, changes)

