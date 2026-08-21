"""
retrieval_tool.py
=================

TOOL definition for RAG-based document retrieval.
Agent-facing interface providing search, evidence evaluation, and citations.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from tools.rag.retrieval_service import RetrievalService
from schemas.tool import ClaimContext, RAGSearchRequest, RAGSearchResponse, ToolErrorResponse
from tools.utils.tool_helpers import format_tool_error


class RetrievalTool:
    """
    Tool-facing wrapper around RetrievalService.
    """

    name: str = "retrieval_tool"
    description: str = "Retrieves authoritative CMS medical necessity coverage policies and evidence."

    def __init__(self, retrieval_service: Optional[RetrievalService] = None) -> None:
        self._retrieval_service = retrieval_service or RetrievalService()

    def search(
        self, request: RAGSearchRequest | Dict[str, Any]
    ) -> RAGSearchResponse | ToolErrorResponse:
        """
        Execute RAG search with query generation, hybrid retrieval, and evidence scoring.
        """
        if isinstance(request, dict):
            question = request.get("question", "")
            claim_ctx_dict = request.get("claim_context")
            claim_context = ClaimContext(**claim_ctx_dict) if claim_ctx_dict else None
            top_k = request.get("top_k")
            metadata_filters = request.get("metadata_filters")
        else:
            question = request.question
            claim_context = request.claim_context
            top_k = request.top_k
            metadata_filters = request.metadata_filters

        if not question:
            return format_tool_error(
                error_code="INVALID_INPUT",
                message="A question must be provided for RAG search.",
            )

        try:
            return self._retrieval_service.search(
                question=question,
                claim_context=claim_context,
                top_k=top_k,
                metadata_filters=metadata_filters,
            )
        except Exception as exc:
            return format_tool_error(
                error_code="RAG_SERVICE_ERROR",
                message=f"An error occurred during RAG search: {str(exc)}",
                details={"question": question},
            )

    def run(self, payload: Dict[str, Any]) -> Any:
        """
        Generic run entrypoint for tool registry dispatch.
        """
        return self.search(payload)
