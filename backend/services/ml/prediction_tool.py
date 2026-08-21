"""
prediction_tool.py
===================

TOOL definition for ML predictions and counterfactual scenarios.
Exposes structured methods for agents and orchestrator.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from services.ml.model_service import ModelService
from schemas.tool import (
    MLRiskRequest,
    MLRiskResponse,
    MLScenarioRequest,
    MLScenarioResponse,
    ToolErrorResponse,
)
from utils.tool_helpers import format_tool_error


class PredictionTool:
    """
    Tool-facing wrapper around ModelService.
    Provides structured risk scoring and counterfactual scenario modeling.
    """

    name: str = "prediction_tool"
    description: str = "Runs ML fraud risk prediction and counterfactual scenario analysis."

    def __init__(self, model_service: Optional[ModelService] = None) -> None:
        self._model_service = model_service or ModelService()

    def predict_risk(self, request: MLRiskRequest | Dict[str, Any] | str) -> MLRiskResponse | ToolErrorResponse:
        """
        Execute risk prediction for a claim ID.
        """
        if isinstance(request, str):
            claim_id = request
        elif isinstance(request, dict):
            claim_id = request.get("claim_id", "")
        else:
            claim_id = request.claim_id

        if not claim_id:
            return format_tool_error(
                error_code="INVALID_INPUT",
                message="claim_id must be provided for risk prediction.",
            )

        return self._model_service.predict_risk(claim_id)

    def simulate_scenario(
        self, request: MLScenarioRequest | Dict[str, Any]
    ) -> MLScenarioResponse | ToolErrorResponse:
        """
        Execute counterfactual scenario analysis on a claim.
        """
        if isinstance(request, dict):
            claim_id = request.get("claim_id", "")
            changes = request.get("changes", {})
        else:
            claim_id = request.claim_id
            changes = request.changes

        if not claim_id:
            return format_tool_error(
                error_code="INVALID_INPUT",
                message="claim_id must be provided for scenario analysis.",
            )
        if not isinstance(changes, dict) or not changes:
            return format_tool_error(
                error_code="INVALID_INPUT",
                message="changes dictionary must be provided with at least one feature change.",
            )

        return self._model_service.simulate_scenario(claim_id, changes)

    def run(self, payload: Dict[str, Any]) -> Any:
        """
        Generic run entrypoint for tool registry compatibility.
        """
        action = payload.get("action", payload.get("tool"))
        if action == "ml_scenario" or "changes" in payload:
            return self.simulate_scenario(payload)
        return self.predict_risk(payload)
