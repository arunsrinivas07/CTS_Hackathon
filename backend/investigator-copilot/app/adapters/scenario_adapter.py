"""
ML Scenario ("what-if") Tool adapter.

INTEGRATION POINT (ML team):
Replace `MockScenarioTool` with a client that calls the real model's
scenario/what-if simulation endpoint. The Copilot depends only on the
`ScenarioTool` interface.

CRITICAL: this tool must NEVER modify the actual claim or InvestigationState.
Its output is always a hypothetical, clearly labeled as such by the caller
(see services/copilot_service.py).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class ScenarioTool(ABC):
    @abstractmethod
    def run_scenario(
        self,
        claim_id: str,
        base_risk_score: float,
        feature: str,
        hypothetical_change: str,
    ) -> dict:
        """Run a hypothetical what-if simulation. Must not mutate any real
        claim or investigation data. Returns a dict describing the
        simulated outcome."""
        ...


class MockScenarioTool(ScenarioTool):
    """
    MVP mock implementation. Applies a small heuristic adjustment to the
    base risk score to produce a plausible hypothetical result.

    INTEGRATION POINT: replace with a call into the real scenario service, e.g.
        response = ml_client.simulate(claim_id=claim_id, changes={...})
    """

    # crude illustrative deltas per known feature keyword
    _KNOWN_ADJUSTMENTS = {
        "frequency": -0.15,
        "volume": -0.15,
        "amount": -0.10,
        "diagnosis": -0.05,
    }

    def run_scenario(
        self,
        claim_id: str,
        base_risk_score: float,
        feature: str,
        hypothetical_change: str,
    ) -> dict:
        feature_lower = feature.lower()
        adjustment = 0.0
        for keyword, delta in self._KNOWN_ADJUSTMENTS.items():
            if keyword in feature_lower:
                adjustment = delta
                break

        simulated_score = max(0.0, min(1.0, base_risk_score + adjustment))

        return {
            "is_hypothetical": True,
            "claim_id": claim_id,
            "base_risk_score": base_risk_score,
            "simulated_risk_score": round(simulated_score, 2),
            "feature": feature,
            "hypothetical_change": hypothetical_change,
            "note": "This is a simulated result only. No claim or investigation data was modified.",
        }


def get_scenario_tool() -> ScenarioTool:
    return MockScenarioTool()
