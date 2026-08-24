"""
ML Tool adapter - Hybrid implementation with graceful fallback.
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

from app.schemas.agentic.investigation import SHAPFactor

logger = logging.getLogger(__name__)


class MLTool(ABC):
    @abstractmethod
    def explain_risk_score(self, claim_id: str, risk_score: float) -> List[SHAPFactor]:
        """Return SHAP-style factor explanations for a given claim's risk
        score. Used only as a fallback when InvestigationState does not
        already contain shap_factors."""
        ...


class RealMLTool(MLTool):
    """
    Attempts to use real agent ML tool, falls back to plausible explanation if unavailable.
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
                    from app.tools.ml_tool import MlTool as AgentMlTool
                    self._agent_tool = AgentMlTool()
                    logger.info("ML tool: Using real agent tool")
                finally:
                    os.chdir(original_cwd)
            except Exception as e:
                logger.warning(f"Could not import real ML tool: {e}. Using fallback.")
                self._agent_tool = None
        return self._agent_tool

    def explain_risk_score(self, claim_id: str, risk_score: float) -> List[SHAPFactor]:
        """Call the real ML tool if available, otherwise return plausible factors."""
        tool = self._try_get_agent_tool()
        
        if tool:
            try:
                result = tool.run(claim_id=claim_id)
                
                if result.status.value == "success" and result.data:
                    shap_features = result.data.get("shap_features", [])
                    factors = []
                    for sf in shap_features:
                        factors.append(SHAPFactor(
                            feature=sf.get("feature", ""),
                            shap_value=sf.get("shap_value", 0.0),
                            direction=sf.get("direction", "increases_risk"),
                            description=sf.get("description", "")
                        ))
                    return factors
            except Exception as e:
                logger.warning(f"ML tool execution failed: {e}. Using fallback.")
        
        # Fallback: return guidance that ML factors should be checked
        return [
            SHAPFactor(
                feature="ml_risk_assessment",
                shap_value=risk_score,
                direction="increases_risk" if risk_score > 0.5 else "decreases_risk",
                description=f"ML model assigned risk score {risk_score:.3f}. Check investigation state for detailed SHAP factors from initial scoring."
            )
        ]


def get_ml_tool() -> MLTool:
    return RealMLTool()
