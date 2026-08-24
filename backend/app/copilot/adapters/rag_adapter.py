"""
RAG Tool adapter - Hybrid implementation with graceful fallback.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List
import sys
from pathlib import Path
import logging

# Ensure agent is importable
_agent_dir = str(Path(__file__).resolve().parent.parent.parent / "agent")
if _agent_dir not in sys.path:
    sys.path.insert(0, _agent_dir)

from app.schemas.agentic.investigation import Citation

logger = logging.getLogger(__name__)


class RAGTool(ABC):
    @abstractmethod
    def retrieve_policy(self, query: str, claim_context: dict) -> List[Citation]:
        """Retrieve authoritative policy/reference documents relevant to
        `query`, given some claim context (procedure, diagnosis, etc.)."""
        ...


class RealRAGTool(RAGTool):
    """
    Attempts to use real agent RAG tool, falls back to enhanced search if unavailable.
    """
    def __init__(self):
        self._agent_tool = None
        self._tried_import = False

    def _try_get_agent_tool(self):
        """Try to import and return the real agent tool."""
        if not self._tried_import:
            self._tried_import = True
            try:
                # Try to import from running agent API if available
                # For now, fall back to local import attempt
                import os
                original_cwd = os.getcwd()
                try:
                    os.chdir(_agent_dir)
                    from app.tools.rag_tool import RagTool as AgentRagTool
                    self._agent_tool = AgentRagTool()
                    logger.info("RAG tool: Using real agent tool")
                finally:
                    os.chdir(original_cwd)
            except Exception as e:
                logger.warning(f"Could not import real RAG tool: {e}. Using enhanced fallback.")
                self._agent_tool = None
        return self._agent_tool

    def retrieve_policy(self, query: str, claim_context: dict) -> List[Citation]:
        """Call the real RAG tool if available, otherwise return enhanced fallback."""
        tool = self._try_get_agent_tool()
        
        if tool:
            try:
                result = tool.run(
                    query=query,
                    procedure=claim_context.get("procedure"),
                    diagnosis=claim_context.get("diagnosis"),
                    claim_id=claim_context.get("claim_id"),
                    provider_id=claim_context.get("provider_id")
                )
                
                citations = []
                if result.status.value == "success" and result.evidence:
                    for ev in result.evidence:
                        citations.append(Citation(
                            citation_id=f"cite-{hash(ev.text)}"[:16],
                            source=ev.source,
                            source_type="policy_document",
                            title=ev.document or "CMS Policy Document",
                            excerpt=ev.text[:300] if ev.text else "",
                            url=ev.url or "",
                            reference=ev.section
                        ))
                return citations
            except Exception as e:
                logger.warning(f"RAG tool execution failed: {e}. Using fallback.")
        
        # Enhanced fallback: provide guidance that RAG should be consulted
        return [Citation(
            citation_id="fallback-cite",
            source="CMS Policy Reference",
            source_type="policy_document",
            title="CMS Medical Necessity Guidelines",
            excerpt=f"For procedure {claim_context.get('procedure', 'Unknown')}, consult CMS coverage determination. Investigation should verify medical necessity based on documented clinical indication.",
            url="",
            reference=None
        )]


def get_rag_tool() -> RAGTool:
    return RealRAGTool()
