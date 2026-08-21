"""
ML Tool adapter.

INTEGRATION POINT (ML/Risk-scoring team):
Replace `MockMLTool` with a client that calls the real XGBoost + SHAP
explanation service. The Copilot depends only on the `MLTool` interface.

Do NOT train or embed a real model here. In practice this adapter is
rarely needed because SHAP/model factors normally already live in
InvestigationState — it exists mainly as a fallback for when that data is
missing or the investigator wants a refreshed explanation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List

from schemas.investigation import SHAPFactor


class MLTool(ABC):
    @abstractmethod
    def explain_risk_score(self, claim_id: str, risk_score: float) -> List[SHAPFactor]:
        """Return SHAP-style factor explanations for a given claim's risk
        score. Used only as a fallback when InvestigationState does not
        already contain shap_factors."""
        ...


class MockMLTool(MLTool):
    """
    MVP mock implementation returning a plausible canned explanation.

    INTEGRATION POINT: replace with a call into the real model service, e.g.
        response = ml_client.explain(claim_id=claim_id)
    """

    def explain_risk_score(self, claim_id: str, risk_score: float) -> List[SHAPFactor]:
        return [
            SHAPFactor(
                feature="provider_monthly_procedure_count",
                shap_value=0.29,
                direction="increases_risk",
                description="Provider's monthly procedure count is the largest contributor to the risk score.",
            ),
            SHAPFactor(
                feature="claim_amount_zscore",
                shap_value=0.18,
                direction="increases_risk",
                description="Claim amount deviates from the regional peer average for this procedure.",
            ),
        ]


def get_ml_tool() -> MLTool:
    return MockMLTool()
