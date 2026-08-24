"""
MOCK implementation of Member 2's RAG tool.

Replace the body of `run()` with a real HTTP/SDK call to Member 2's service
once available. The contract (input kwargs -> ToolOutput shape) must stay
the same so nothing else in the orchestrator needs to change.

Expected real contract (per project spec section 26):
{
  "status": "success",
  "answer_context": "...",
  "evidence": [...],
  "citations": [...],
  "confidence": 0.91,
  "sufficient": true
}
"""
from __future__ import annotations
import logging

from app.tools.base import BaseTool
from app.schemas.agentic.tool import ToolOutput, ToolResultStatus, EvidenceItem, CMSEvidenceMetadata, LCDEvidenceMetadata, ContradictionDetail
from app.services.agentic.rag.retrieval_service import RetrievalService
from app.schemas.agentic.tool import ClaimContext  # or wherever ClaimContext is


logger = logging.getLogger(__name__)

class RagTool(BaseTool):
    name = "rag"
    description = (
        "Retrieves policy, medical-necessity, and coding-guideline evidence "
        "relevant to a claim/procedure/diagnosis question."
    )
    
    def __init__(self):
        super().__init__()
        # Lazy initialization
        self._service = None

    def _get_service(self):
        if self._service is None:
            self._service = RetrievalService()
        return self._service

    def run(self, *, query: str, procedure: str | None = None, diagnosis: str | None = None, claim_id: str | None = None, claim_amount: float | None = None, provider_id: str | None = None, **_) -> ToolOutput:
        if not query:
            return ToolOutput(status=ToolResultStatus.TOOL_FAILURE, error="Missing required 'query' input.")

        try:
            service = self._get_service()
            claim_ctx = ClaimContext(
                claim_id=claim_id,
                procedure=procedure,
                diagnosis=diagnosis,
                provider_id=provider_id,
                claim_amount=claim_amount
            )
            
            response = service.search(question=query, claim_context=claim_ctx)
            
            if response.status == "error":
                return ToolOutput(status=ToolResultStatus.TOOL_FAILURE, error=getattr(response, "message", "Unknown error"))
                
            status = ToolResultStatus.SUCCESS if response.sufficient else ToolResultStatus.NO_EVIDENCE_FOUND
            
            # Map Member 2 schema to Member 1 schema
            evidence_items = []
            for ev in response.evidence:
                # ev is schemas.tool.EvidenceItem
                cms_meta = None
                lcd_meta = None
                meta = getattr(ev, "metadata", {}) or {}
                
                # Check for LCD vs general CMS
                if "lcd_id" in meta:
                    lcd_meta = LCDEvidenceMetadata(
                        lcd_id=meta.get("lcd_id", ""),
                        mac_contractor=meta.get("mac_contractor", ""),
                        jurisdiction=meta.get("jurisdiction", ""),
                        effective_date=meta.get("effective_date", ""),
                        version_status=meta.get("version_status", "")
                    )
                else:
                    # General CMS
                    cms_meta = CMSEvidenceMetadata(
                        official_cms_url=meta.get("url") or getattr(ev, "url", ""),
                        document_id=meta.get("document_id", getattr(ev, "document", "")),
                        document_title=meta.get("document_title", getattr(ev, "document", "")),
                        section=getattr(ev, "section", "") or meta.get("section", ""),
                        page=getattr(ev, "page", None) or meta.get("page", None),
                        effective_date=meta.get("effective_date", None),
                        jurisdiction=meta.get("jurisdiction", None),
                        verification_status=meta.get("verification_status", "verified")
                    )

                evidence_items.append(
                    EvidenceItem(
                        source=ev.source,
                        document=ev.document,
                        section=ev.section,
                        page=ev.page,
                        text=ev.text,
                        retrieval_score=ev.retrieval_score,
                        evidence_score=ev.evidence_score,
                        url=ev.url or meta.get("url"),
                        cms_metadata=cms_meta,
                        lcd_metadata=lcd_meta
                    )
                )
            
            contradictions = []
            if response.contradictions:
                for c in response.contradictions:
                    contradictions.append(
                        ContradictionDetail(
                            evidence_a=c.evidence_a,
                            evidence_b=c.evidence_b,
                            reason=c.reason,
                            resolution=c.resolution,
                            preferred_evidence=c.preferred_evidence
                        )
                    )

            # Do not encode structured contradiction info only inside a text reason string
            # We preserve reason, but rely on has_contradiction
            return ToolOutput(
                status=status,
                data={
                    "answer_context": response.synthesis,
                    "sufficient": response.sufficient,
                    "has_contradiction": response.has_contradiction,
                    "contradictions": [c.model_dump() for c in contradictions],
                    "reason": response.reason
                },
                evidence=evidence_items,
                citations=[e.model_dump() for e in evidence_items],
                confidence=response.confidence
            )
            
        except Exception as e:
            logger.exception("Error running RagTool")
            return ToolOutput(status=ToolResultStatus.TOOL_FAILURE, error=str(e))

# Export for direct class import (backwards compatibility)
RAGTool = RagTool
