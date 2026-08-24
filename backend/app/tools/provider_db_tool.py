"""
MOCK implementations of Member 2's provider-related DB tools.

Real contract for provider_statistics (section 26):
{
  "status": "success",
  "provider_statistics": {...},
  "peer_statistics": {...},
  "comparison": {...},
  "evidence": [...]
}

provider_history and provider_peer_comparison follow the same pattern with
their own payload shapes; we normalize all of them into the generic
ToolOutput envelope so the executor/evaluator don't need tool-specific
branches.
"""
from __future__ import annotations
import logging

from app.tools.base import BaseTool
from app.schemas.agentic.tool import ToolOutput, ToolResultStatus, EvidenceItem
from app.services.agentic.database.database_service import DatabaseService

logger = logging.getLogger(__name__)

class ProviderStatisticsTool(BaseTool):
    name = "provider_statistics"
    description = "Returns a provider's procedure-volume statistics compared against a peer cohort."

    def __init__(self):
        super().__init__()
        self._service = None
        
    def _get_service(self):
        if self._service is None:
            self._service = DatabaseService()
        return self._service

    def run(self, *, provider_id: str, procedure: str, **_) -> ToolOutput:
        if not provider_id or not procedure:
            return ToolOutput(
                status=ToolResultStatus.TOOL_FAILURE,
                error="Missing required 'provider_id' or 'procedure' input.",
            )

        try:
            service = self._get_service()
            response = service.get_provider_statistics(provider_id, procedure)
            
            if getattr(response, "status", None) == "error":
                return ToolOutput(status=ToolResultStatus.TOOL_FAILURE, error=getattr(response, "message", "Unknown error"))
            
            return ToolOutput(
                status=ToolResultStatus.SUCCESS,
                data={
                    "provider_statistics": {
                        "monthly_volume": response.provider_count, 
                        "procedure": response.procedure,
                        "specialty": response.specialty,
                        "total_claims_submitted": response.total_claims_submitted,
                        "total_billed_amount": response.total_billed_amount,
                        "denial_rate": response.denial_rate
                    },
                    "peer_statistics": {
                        "avg_monthly_volume": response.peer_average,
                        "median_monthly_volume": response.peer_median,
                        "p95_monthly_volume": response.peer_95_percentile
                    },
                    "comparison": {
                        "above_peer_p95": response.provider_count > response.peer_95_percentile,
                        "multiple_of_average": round(response.provider_count / response.peer_average, 2) if response.peer_average else 0,
                    },
                },
                evidence=[
                    EvidenceItem(
                        source="Provider Claims Database",
                        document="Provider Statistics",
                        text=f"Provider {procedure} volume ({response.provider_count}/month) compared to peer 95th percentile ({response.peer_95_percentile}/month).",
                        retrieval_score=1.0,
                        evidence_score=1.0
                    )
                ],
                confidence=0.95,
            )
        except Exception as e:
            logger.exception("Error in ProviderStatisticsTool")
            return ToolOutput(status=ToolResultStatus.TOOL_FAILURE, error=str(e))


class ProviderHistoryTool(BaseTool):
    name = "provider_history"
    description = "Returns a provider's historical billing behavior and any prior fraud/audit flags."

    def __init__(self):
        super().__init__()
        self._service = None
        
    def _get_service(self):
        if self._service is None:
            self._service = DatabaseService()
        return self._service

    def run(self, *, provider_id: str, **_) -> ToolOutput:
        if not provider_id:
            return ToolOutput(status=ToolResultStatus.TOOL_FAILURE, error="Missing required 'provider_id' input.")

        try:
            service = self._get_service()
            response = service.get_provider_history(provider_id)
            
            if getattr(response, "status", None) == "error":
                return ToolOutput(status=ToolResultStatus.TOOL_FAILURE, error=getattr(response, "message", "Unknown error"))

            history = response.history or []
            evidence_items = []
            if history:
                # Format history entries into readable text
                history_parts = []
                for h in history[:6]:
                    # Handle both mock format (period/mri_claims) and real DB format (claim_number/service_date/billed_amount)
                    if "claim_number" in h:
                        history_parts.append(f"{h['claim_number']} ({h.get('service_date','')}, ${h.get('billed_amount',0):,.0f}, {h.get('status','')})")
                    elif "period" in h:
                        history_parts.append(f"{h['period']}: {h.get('mri_claims', h.get('billed', ''))}")
                    elif "event" in h:
                        history_parts.append(f"{h['event']}: {h.get('details', h.get('date', ''))}")
                    else:
                        history_parts.append(str(h)[:80])
                
                history_summary = "; ".join(history_parts) if history_parts else "No detailed history"
                total_claims = len(history)
                total_billed = sum(float(h.get("billed_amount", h.get("billed", 0)) or 0) for h in history)
                
                evidence_text = (
                    f"Provider {provider_id} has {total_claims} historical claims"
                    f"{f' totaling ${total_billed:,.0f}' if total_billed > 0 else ''}. "
                    f"Recent: {history_summary}."
                )
                
                evidence_items.append(
                    EvidenceItem(
                        source="Provider Claims Database",
                        document="Provider Billing History",
                        section="Historical Trend",
                        text=evidence_text,
                        retrieval_score=1.0,
                        evidence_score=0.85,
                    )
                )
            
            return ToolOutput(
                status=ToolResultStatus.SUCCESS if history else ToolResultStatus.NO_EVIDENCE_FOUND,
                data={
                    "history": history,
                    "prior_flags": [],
                },
                evidence=evidence_items,
                confidence=0.85,
            )
        except Exception as e:
            logger.exception("Error in ProviderHistoryTool")
            return ToolOutput(status=ToolResultStatus.TOOL_FAILURE, error=str(e))


class ProviderPeerComparisonTool(BaseTool):
    name = "provider_peer_comparison"
    description = "Compares a provider against a cohort of similarly-specialized peers (not just global average)."
    
    def __init__(self):
        super().__init__()
        self._service = None
        
    def _get_service(self):
        if self._service is None:
            self._service = DatabaseService()
        return self._service

    def run(self, *, provider_id: str, specialty: str | None = None, procedure: str | None = None, **_) -> ToolOutput:
        if not provider_id:
            return ToolOutput(status=ToolResultStatus.TOOL_FAILURE, error="Missing required 'provider_id' input.")

        try:
            service = self._get_service()
            response = service.get_provider_peer_comparison(provider_id, procedure)
            
            if getattr(response, "status", None) == "error":
                return ToolOutput(status=ToolResultStatus.TOOL_FAILURE, error=getattr(response, "message", "Unknown error"))

            metrics = response.metrics or {}
            evidence_items = []
            if metrics:
                metrics_text = "; ".join(f"{k}: {v}" for k, v in list(metrics.items())[:5]) if isinstance(metrics, dict) else str(metrics)
                evidence_items.append(
                    EvidenceItem(
                        source="Provider Claims Database",
                        document="Peer Comparison Analysis",
                        section=f"Specialty: {response.specialty}",
                        text=f"Provider {provider_id} peer comparison ({response.specialty}): {metrics_text}",
                        retrieval_score=1.0,
                        evidence_score=0.9,
                    )
                )

            return ToolOutput(
                status=ToolResultStatus.SUCCESS if metrics else ToolResultStatus.NO_EVIDENCE_FOUND,
                data={
                    "cohort_size": metrics.get("cohort_size", 0) if isinstance(metrics, dict) else 0,
                    "cohort_specialty": response.specialty,
                    "provider_percentile": metrics.get("percentile", 0) if isinstance(metrics, dict) else 0,
                    "metrics": metrics
                },
                evidence=evidence_items,
                confidence=0.9,
            )
        except Exception as e:
            logger.exception("Error in ProviderPeerComparisonTool")
            return ToolOutput(status=ToolResultStatus.TOOL_FAILURE, error=str(e))
