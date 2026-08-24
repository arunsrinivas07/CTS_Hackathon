"""
Provider DB Tool and Claim DB Tool adapters - Hybrid implementations with graceful fallback.
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

logger = logging.getLogger(__name__)


class ProviderDBTool(ABC):
    @abstractmethod
    def get_mri_history(self, provider_name: str) -> List[dict]:
        """Return historical monthly procedure volume for a provider."""
        ...


class ClaimDBTool(ABC):
    @abstractmethod
    def get_related_claims(self, claim_id: str) -> List[dict]:
        """Return claims related to the given claim (e.g. same patient)."""
        ...


class RealProviderDBTool(ProviderDBTool):
    """
    Attempts to use real agent provider DB tool, provides guidance if unavailable.
    """
    def __init__(self):
        self._agent_tool = None
        self._tried_import = False

    def _try_get_agent_tool(self):
        if not self._tried_import:
            self._tried_import = True
            try:
                import os
                original_cwd = os.getcwd()
                try:
                    os.chdir(_agent_dir)
                    from app.tools.provider_db_tool import ProviderHistoryTool as AgentProviderHistoryTool
                    self._agent_tool = AgentProviderHistoryTool()
                    logger.info("Provider DB tool: Using real agent tool")
                finally:
                    os.chdir(original_cwd)
            except Exception as e:
                logger.warning(f"Could not import real Provider DB tool: {e}. Using fallback.")
                self._agent_tool = None
        return self._agent_tool

    def get_mri_history(self, provider_id: str) -> List[dict]:
        """Get provider history using real tool if available."""
        tool = self._try_get_agent_tool()
        
        if tool:
            try:
                result = tool.run(provider_id=provider_id)
                
                if result.status.value == "success" and result.data:
                    return result.data.get("history", [])
            except Exception as e:
                logger.warning(f"Provider DB tool execution failed: {e}")
        
        # Fallback: return guidance
        return [{
            "event": "provider_history_check_needed",
            "details": f"Provider {provider_id} billing history should be reviewed in investigation evidence."
        }]


class RealClaimDBTool(ClaimDBTool):
    """
    Attempts to use real agent claim DB tool, provides guidance if unavailable.
    """
    def __init__(self):
        self._agent_tool = None
        self._tried_import = False

    def _try_get_agent_tool(self):
        if not self._tried_import:
            self._tried_import = True
            try:
                import os
                original_cwd = os.getcwd()
                try:
                    os.chdir(_agent_dir)
                    from app.tools.claim_db_tool import ClaimHistoryTool as AgentClaimHistoryTool
                    self._agent_tool = AgentClaimHistoryTool()
                    logger.info("Claim DB tool: Using real agent tool")
                finally:
                    os.chdir(original_cwd)
            except Exception as e:
                logger.warning(f"Could not import real Claim DB tool: {e}. Using fallback.")
                self._agent_tool = None
        return self._agent_tool

    def get_related_claims(self, claim_id: str) -> List[dict]:
        """Get related claims using real tool if available."""
        tool = self._try_get_agent_tool()
        
        if tool:
            try:
                result = tool.run(claim_id=claim_id)
                
                if result.status.value == "success" and result.data:
                    return result.data.get("related_claims", [])
            except Exception as e:
                logger.warning(f"Claim DB tool execution failed: {e}")
        
        # Fallback: return guidance
        return [{
            "note": "Related claims analysis",
            "details": f"Check investigation evidence for related claims to {claim_id}."
        }]


def get_provider_db_tool() -> ProviderDBTool:
    return RealProviderDBTool()


def get_claim_db_tool() -> ClaimDBTool:
    return RealClaimDBTool()
