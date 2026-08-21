"""
citation_builder.py
===================

Builds structured EvidenceItem objects with preserved provenance, metadata,
citation markers, and heuristic evaluation scores.
"""

from __future__ import annotations

from typing import Any, Dict, List
from schemas.tool import EvidenceItem


class CitationBuilder:
    """
    Constructs clean, structured EvidenceItem models from evaluated search chunks.
    """

    @staticmethod
    def build_citations(evaluated_items: List[Dict[str, Any]]) -> List[EvidenceItem]:
        """
        Converts evaluated dictionary chunks into Pydantic EvidenceItem records.
        """
        citations: List[EvidenceItem] = []

        for item in evaluated_items:
            meta = item.get("metadata", {})
            scores = item.get("scores")
            if isinstance(scores, dict):
                scores = EvidenceScores(**scores)

            citation = EvidenceItem(
                source=meta.get("source", "CMS Knowledge Base"),
                document=meta.get("document_title", meta.get("document", "CMS Policy Document")),
                section=meta.get("section_name", meta.get("section", "N/A")),
                page=int(meta.get("page", 1)),
                text=item.get("text", ""),
                retrieval_score=float(item.get("retrieval_score", 0.0)),
                evidence_score=float(item.get("evidence_score", 0.0)),
                scores=scores,
                effective_date=meta.get("effective_date", None),
                url=meta.get("url", None),
            )
            citations.append(citation)

        return citations
