"""
MOCK implementation of Member 2's ML Scenario tool.

Real contract (section 26):
{
  "status": "success",
  "original_score": 0.87,
  "scenario_score": 0.61,
  "difference": -0.26
}

Used to answer "what-if" questions, e.g. "if provider volume were at the
peer median, would the risk score still be elevated?" -- helps the agent
test whether a single feature is really driving the risk.
"""
from __future__ import annotations
import logging

from app.tools.base import BaseTool
from app.schemas.agentic.tool import ToolOutput, ToolResultStatus
from app.services.agentic.ml.model_service import ModelService

logger = logging.getLogger(__name__)

class MlScenarioTool(BaseTool):
    name = "ml_scenario"
    description = "Re-runs the ML model with a hypothetical feature change to test its impact on risk score."

    def __init__(self):
        super().__init__()
        self._service = None
        
    def _get_service(self):
        if self._service is None:
            self._service = ModelService()
        return self._service

    def run(self, *, claim_id: str, feature: str, hypothetical_value: float | str, **_) -> ToolOutput:
        if not claim_id or not feature:
            return ToolOutput(
                status=ToolResultStatus.TOOL_FAILURE,
                error="Missing required 'claim_id' or 'feature' input.",
            )

        try:
            service = self._get_service()
            changes = {feature: hypothetical_value}
            response = service.simulate_scenario(claim_id, changes)
            
            if getattr(response, "status", None) == "error":
                return ToolOutput(status=ToolResultStatus.TOOL_FAILURE, error=getattr(response, "message", "Unknown error"))
            
            return ToolOutput(
                status=ToolResultStatus.SUCCESS,
                data={
                    "original_score": response.original_score,
                    "scenario_score": response.scenario_score,
                    "difference": response.difference,
                    "explanation": f"{response.explanation} Note: Model scenario analysis is statistical and does not constitute causal evidence."
                },
                confidence=0.8,
            )
        except Exception as e:
            logger.exception("Error running MlScenarioTool")
            return ToolOutput(status=ToolResultStatus.TOOL_FAILURE, error=str(e))
