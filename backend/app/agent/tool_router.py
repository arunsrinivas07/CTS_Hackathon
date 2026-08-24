"""
Validates the LLM-proposed tool against the registered TOOL_REGISTRY and
builds the concrete input payload for that tool call from claim_data/state.

SECURITY: this is the enforcement boundary described in section 12/32 of
the spec. The LLM never calls a function directly -- it only names a tool.
If the name isn't in TOOL_REGISTRY, we never execute anything; we fall back
to a safe default or raise so the executor can record INVALID_TOOL.
"""
from __future__ import annotations

from app.schemas.agentic.investigation import InvestigationState
from app.schemas.agentic.question import InvestigationQuestion
from app.tools.base import TOOL_REGISTRY, is_registered

# Fallback mapping used only when the LLM omits/invalidates a tool choice,
# so a plausible question doesn't just get silently dropped.
KEYWORD_FALLBACK_ORDER = [
    ("policy", "rag"),
    ("medical necessity", "rag"),
    ("guideline", "rag"),
    ("peer", "provider_peer_comparison"),
    ("comparable provider", "provider_peer_comparison"),
    ("history", "provider_history"),
    ("historical", "provider_history"),
    ("prior claim", "claim_history"),
    ("related claim", "claim_history"),
    ("what if", "ml_scenario"),
    ("scenario", "ml_scenario"),
    ("risk score", "ml"),
    ("outlier", "provider_statistics"),
    ("volume", "provider_statistics"),
    ("statistic", "provider_statistics"),
]


def resolve_tool(question: InvestigationQuestion) -> str | None:
    """Returns a validated, registered tool name, or None if nothing fits."""
    if question.preferred_tool and is_registered(question.preferred_tool):
        return question.preferred_tool

    text = f"{question.question} {question.required_evidence}".lower()
    for keyword, tool_name in KEYWORD_FALLBACK_ORDER:
        if keyword in text and is_registered(tool_name):
            return tool_name

    return None


def build_tool_input(tool_name: str, question: InvestigationQuestion, state: InvestigationState) -> dict:
    """
    Builds the kwargs dict for a given tool call using claim_data and prior
    state. This is intentionally simple/deterministic for the MVP rather
    than another LLM call -- claim_data field names are the contract with
    the upstream pipeline.
    """
    claim = state.claim_data
    provider_id = claim.get("provider_id") or claim.get("provider")
    procedure = claim.get("procedure")

    if tool_name == "ml_verification":
        return {
            "claim_data": state.claim_data,
            "risk_score": state.risk_score,
            "risk_level": state.risk_level,
            "risk_factors": [rf.model_dump() for rf in state.risk_factors],
            "shap_factors": [],
            "detected_patterns": [p.model_dump() for p in state.detected_patterns],
        }
    if tool_name == "rag_search":
        return {
            "query": question.question,
            "procedure": procedure,
            "diagnosis": claim.get("diagnosis"),
        }
    if tool_name == "rag":
        return {
            "query": question.question,
            "procedure": procedure,
            "diagnosis": claim.get("diagnosis"),
        }
    if tool_name == "ml":
        return {"claim_id": state.claim_id}
    if tool_name == "ml_scenario":
        top_factor = state.risk_factors[0].name if state.risk_factors else "procedure_frequency"
        return {"claim_id": state.claim_id, "feature": top_factor, "hypothetical_value": "peer_median"}
    if tool_name == "provider_statistics":
        return {"provider_id": provider_id, "procedure": procedure}
    if tool_name == "provider_history":
        return {"provider_id": provider_id}
    if tool_name == "provider_peer_comparison":
        return {"provider_id": provider_id, "specialty": claim.get("provider_specialty")}
    if tool_name == "claim_history":
        return {"claim_id": state.claim_id, "provider_id": provider_id, "patient_id": claim.get("patient_id")}

    return {}


def available_tool_names() -> list[str]:
    return list(TOOL_REGISTRY.keys())
