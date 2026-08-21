from __future__ import annotations

import uuid
from typing import Any

from schemas.investigation import (
    InvestigationState,
    InvestigationStatus,
    RiskFactor,
    DetectedPattern,
)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def initialize_investigation(
    claim_id: str,
    claim_data: dict[str, Any],
    risk_score: float,
    risk_level: str,
    shap_contributors: list[dict],
    detected_patterns: list[dict],
    max_iterations: int = 5,
    max_revisions: int = 2,
) -> InvestigationState:
    """
    Build the initial InvestigationState from a claim that has just entered
    the investigator queue (i.e. output of the existing deterministic
    pipeline). This does NOT call the LLM -- objective derivation happens
    separately in orchestrator.py so it can be tested/mocked independently.
    """
    risk_factors = [
        RiskFactor(
            name=c.get("feature", "unknown"),
            shap_value=c.get("value"),
            magnitude="HIGH" if abs(c.get("value", 0)) >= 0.25 else "MEDIUM",
        )
        for c in shap_contributors
    ]
    patterns = [DetectedPattern(name=p.get("name", "unknown"), description=p.get("description")) for p in detected_patterns]

    state = InvestigationState(
        investigation_id=new_id("inv"),
        claim_id=claim_id,
        claim_data=claim_data,
        risk_score=risk_score,
        risk_level=risk_level,
        risk_factors=risk_factors,
        detected_patterns=patterns,
        status=InvestigationStatus.INITIALIZED,
        max_iterations=max_iterations,
        max_revisions=max_revisions,
    )
    return state


def normalize_question_text(text: str) -> str:
    return " ".join(text.lower().strip().split())
