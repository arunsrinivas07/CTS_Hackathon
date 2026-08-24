"""
MOCK implementation of Member 2's ML Risk tool.

Real contract (section 26):
{
  "status": "success",
  "risk_score": 0.87,
  "risk_level": "HIGH",
  "shap_features": [...]
}

Note: in practice the initial risk score/SHAP already arrive with the claim
from the deterministic pipeline (see InvestigationState init). This tool
exists for cases where the agent wants to re-score or re-check the model
output mid-investigation (e.g. after new information surfaces).
"""
from __future__ import annotations
import logging

from app.tools.base import BaseTool
from app.schemas.agentic.tool import ToolOutput, ToolResultStatus
from app.services.agentic.ml.model_service import ModelService

logger = logging.getLogger(__name__)

class MlTool(BaseTool):
    name = "ml"
    description = "Re-queries the ML risk model for the current claim/provider state."

    def __init__(self):
        super().__init__()
        self._service = None
        
    def _get_service(self):
        if self._service is None:
            self._service = ModelService()
        return self._service

    def run(self, *, claim_id: str, **_) -> ToolOutput:
        if not claim_id:
            return ToolOutput(status=ToolResultStatus.TOOL_FAILURE, error="Missing required 'claim_id' input.")

        try:
            service = self._get_service()
            response = service.predict_risk(claim_id)
            
            if getattr(response, "status", None) == "error":
                return ToolOutput(status=ToolResultStatus.TOOL_FAILURE, error=getattr(response, "message", "Unknown error"))
            
            return ToolOutput(
                status=ToolResultStatus.SUCCESS,
                data={
                    "risk_score": response.risk_score,
                    "risk_level": response.risk_level,
                    "shap_features": [f.dict() for f in response.shap_features],
                    "disclaimer": "SHAP features are statistical explanations and do not represent causal evidence. This model output does not make a legal fraud determination."
                },
                confidence=0.87,
            )
        except Exception as e:
            logger.exception("Error running MlTool")
            return ToolOutput(status=ToolResultStatus.TOOL_FAILURE, error=str(e))

# Export for direct class import (backwards compatibility)
MLTool = MlTool
