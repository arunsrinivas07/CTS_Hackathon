"""
RAG Tool adapter.

INTEGRATION POINT (RAG team):
Replace `MockRAGTool` with a client that calls the real RAG pipeline
(policy/medical-necessity retrieval). The Copilot only depends on the
`RAGTool` interface, so no Copilot logic needs to change when the real
implementation is wired in.

Do NOT implement a new RAG pipeline here. This file returns a small set of
canned mock documents only so the Copilot's policy_question flow can be
demonstrated end-to-end.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from app.data.mock_data import POLICY_DOCUMENTS
from schemas.investigation import Citation


class RAGTool(ABC):
    @abstractmethod
    def retrieve_policy(self, query: str, claim_context: dict) -> List[Citation]:
        """Retrieve authoritative policy/reference documents relevant to
        `query`, given some claim context (procedure, diagnosis, etc.)."""
        ...


class MockRAGTool(RAGTool):
    """
    MVP mock implementation. Performs a trivial keyword match over a small
    canned set of policy documents.

    INTEGRATION POINT: replace with a call into the real RAG service, e.g.
        response = rag_client.query(query, filters=claim_context)
    """

    def retrieve_policy(self, query: str, claim_context: dict) -> List[Citation]:
        query_lower = query.lower()
        matches: List[Citation] = []
        for doc in POLICY_DOCUMENTS:
            haystack = f"{doc['title']} {doc['excerpt']}".lower()
            if any(term in haystack for term in _extract_keywords(query_lower)):
                matches.append(Citation(**doc))
        return matches


def _extract_keywords(query_lower: str) -> List[str]:
    candidates = [
        "policy", "necessity", "necessary", "mri", "imaging", "frequency",
        "volume", "conservative", "treatment", "billing", "review",
    ]
    return [c for c in candidates if c in query_lower] or ["policy"]


def get_rag_tool() -> RAGTool:
    return MockRAGTool()
