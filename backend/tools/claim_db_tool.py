"""
MOCK implementation of Member 2's Claim History tool.
"""
from __future__ import annotations
import logging

from tools.base import BaseTool
from schemas.tool import ToolOutput, ToolResultStatus
from services.database.database_service import DatabaseService

logger = logging.getLogger(__name__)

class ClaimHistoryTool(BaseTool):
    name = "claim_history"
    description = "Returns related/prior claims for the same patient or provider to detect repeated billing patterns."
    
    def __init__(self):
        super().__init__()
        self._service = None
        
    def _get_service(self):
        if self._service is None:
            self._service = DatabaseService()
        return self._service

    def run(self, *, claim_id: str, provider_id: str | None = None, patient_id: str | None = None, **_) -> ToolOutput:
        if not claim_id:
            return ToolOutput(status=ToolResultStatus.TOOL_FAILURE, error="Missing required 'claim_id' input.")

        try:
            service = self._get_service()
            response = service.get_related_claims(claim_id)
            
            if getattr(response, "status", None) == "error":
                return ToolOutput(status=ToolResultStatus.TOOL_FAILURE, error=getattr(response, "message", "Unknown error"))
            
            return ToolOutput(
                status=ToolResultStatus.SUCCESS,
                data={
                    "related_claims": response.related_claims,
                    "patterns": [],
                },
                confidence=0.75,
            )
        except Exception as e:
            logger.exception("Error in ClaimHistoryTool")
            return ToolOutput(status=ToolResultStatus.TOOL_FAILURE, error=str(e))
