"""
Claim History tool — queries the real database for related/prior claims.
"""
from __future__ import annotations
import logging

from app.tools.base import BaseTool
from app.schemas.agentic.tool import ToolOutput, ToolResultStatus, EvidenceItem
from app.services.agentic.database.database_service import DatabaseService

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

            related = response.related_claims or []
            evidence_items = []

            if related:
                count = len(related)
                summary_parts = []
                for rc in related[:5]:
                    cid = rc.get("claim_id", "")
                    date = rc.get("service_date", "")
                    amt = rc.get("billed_amount", rc.get("total_billed_amount", ""))
                    status = rc.get("status", "")
                    summary_parts.append(f"{cid} ({date}, ${amt}, {status})")
                summary = "; ".join(summary_parts)

                evidence_items.append(EvidenceItem(
                    source="Claims Database",
                    document="Related Claims History",
                    section=f"Patient/Provider Claims for {claim_id}",
                    text=f"Found {count} related claims for this patient/provider: {summary}.",
                    retrieval_score=1.0,
                    evidence_score=0.8,
                ))

            return ToolOutput(
                status=ToolResultStatus.SUCCESS if related else ToolResultStatus.NO_EVIDENCE_FOUND,
                data={
                    "related_claims": related,
                    "patterns": [],
                },
                evidence=evidence_items,
                confidence=0.75,
            )
        except Exception as e:
            logger.exception("Error in ClaimHistoryTool")
            return ToolOutput(status=ToolResultStatus.TOOL_FAILURE, error=str(e))
