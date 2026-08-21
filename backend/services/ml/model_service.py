"""
model_service.py
================

SERVICE layer for ML model interactions.
Decoupled from public tool interface; interacts through BaseMLRepository.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from llm.config import settings
from services.ml.repository import BaseMLRepository, MockMLRepository, RealMLRepository
from schemas.tool import MLRiskResponse, MLScenarioResponse, ToolErrorResponse
from utils.tool_helpers import format_tool_error, logger, timed


class ModelService:
    """
    Service coordinating ML model loading, predictions, and scenario simulations.
    """

    def __init__(self, repository: Optional[BaseMLRepository] = None) -> None:
        self.last_status = "mock"
        self.last_provider = "mock-ml"
        self.last_prediction = None
        
        if repository is not None:
            self._repo = repository
            self.last_status = "custom"
        elif settings.data_mode == "real":
            from services.ml.repository import LiveMLRepository
            self._repo = LiveMLRepository()
            self.last_status = "live"
            self.last_provider = "careguard-ml"
        else:
            self._repo = MockMLRepository()

    @timed
    def predict_risk(self, claim_id: str) -> MLRiskResponse | ToolErrorResponse:
        """
        Run risk prediction and SHAP analysis for a specific claim.
        """
        try:
            if self.last_status == "live":
                try:
                    prediction = self._repo.get_risk_prediction(claim_id)
                    if prediction is None:
                        return format_tool_error(
                            error_code="CLAIM_NOT_FOUND",
                            message=f"Claim '{claim_id}' was not found in the ML model repository.",
                            details={"claim_id": claim_id},
                        )
                    self.last_prediction = prediction.model_dump()
                    return prediction
                except Exception as exc:
                    logger.warning("Live ML call failed, falling back to mock: %s", exc)
                    self.last_status = "fallback"
                    self.last_provider = "careguard-ml"
                    mock_repo = MockMLRepository()
                    self._repo = mock_repo  # Persist the fallback repo
                    prediction = mock_repo.get_risk_prediction(claim_id)
                    if prediction is None:
                        return format_tool_error(
                            error_code="CLAIM_NOT_FOUND",
                            message=f"Claim '{claim_id}' was not found in the fallback ML model repository.",
                            details={"claim_id": claim_id},
                        )
                    self.last_prediction = prediction.model_dump()
                    return prediction
            else:
                prediction = self._repo.get_risk_prediction(claim_id)
                if prediction is None:
                    return format_tool_error(
                        error_code="CLAIM_NOT_FOUND",
                        message=f"Claim '{claim_id}' was not found in the ML model repository.",
                        details={"claim_id": claim_id},
                    )
                self.last_prediction = prediction.model_dump()
                return prediction
        except Exception as exc:
            logger.error("Error during ML risk prediction for %s: %s", claim_id, exc)
            self.last_status = "failed"
            return format_tool_error(
                error_code="ML_SERVICE_ERROR",
                message=f"An error occurred during ML risk prediction: {str(exc)}",
                details={"claim_id": claim_id},
            )

    @timed
    def simulate_scenario(
        self, claim_id: str, changes: Dict[str, Any]
    ) -> MLScenarioResponse | ToolErrorResponse:
        """
        Run counterfactual scenario simulation on a claim.
        """
        try:
            scenario = self._repo.simulate_scenario(claim_id, changes)
            if scenario is None:
                return format_tool_error(
                    error_code="CLAIM_NOT_FOUND",
                    message=f"Claim '{claim_id}' was not found for scenario analysis.",
                    details={"claim_id": claim_id},
                )
            return scenario
        except Exception as exc:
            logger.error("Error during ML scenario simulation for %s: %s", claim_id, exc)
            return format_tool_error(
                error_code="ML_SERVICE_ERROR",
                message=f"An error occurred during scenario simulation: {str(exc)}",
                details={"claim_id": claim_id, "changes": changes},
            )
