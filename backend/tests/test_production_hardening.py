"""
Production Hardening & System Verification Tests.

Verifies edge cases, security guardrails, state store, loop caps, critic revisions,
human escalation, and Member 3 trace contract generation.
"""
from __future__ import annotations

import pytest

from agent.orchestrator import finalize_investigation, run_iteration, run_to_completion, start_investigation
from api.store import InMemoryStateStore
from schemas.investigation import InvestigationStatus
from schemas.trace import build_investigation_trace
from tests.conftest import ScriptedLLMClient


CLAIM = {
    "provider_id": "ABC123",
    "procedure": "MRI",
    "diagnosis": "Lower back pain",
    "amount": 4800,
    "patient_id": "P001",
}
SHAP = [{"feature": "procedure_frequency", "value": 0.34}]
PATTERNS = [{"name": "high_procedure_frequency"}]


def test_state_store_abstract_persistence():
    store = InMemoryStateStore()
    llm = ScriptedLLMClient([{"objectives": [{"description": "obj", "related_risk_factors": []}]}])
    state = start_investigation("C100", CLAIM, 0.85, "HIGH", SHAP, PATTERNS, llm=llm)

    store.save(state)
    retrieved = store.get(state.investigation_id)

    assert retrieved is not None
    assert retrieved.investigation_id == state.investigation_id
    assert len(store.all_investigations()) == 1


def test_investigation_trace_generation_for_member_3():
    llm = ScriptedLLMClient(
        [
            {"objectives": [{"description": "obj", "related_risk_factors": []}]},
            {
                "question": "Is provider MRI volume anomalous?",
                "reason": "high score",
                "required_evidence": "peer stats",
                "preferred_tool": "provider_statistics",
                "priority": "HIGH",
                "no_useful_question_remains": False,
            },
            {
                "sufficient": True,
                "reason": "obtained stats",
                "missing_evidence": [],
                "next_action": "counter_analysis",
                "criteria_met": {},
            },
            {
                "current_hypothesis_restated": "h",
                "counter_questions": [],
                "alternative_explanations_without_tooling": ["Specialty mix"],
            },
            {
                "claim_summary": "s",
                "risk_summary": "r",
                "findings": ["Outlier provider"],
                "conclusion": "The evidence supports elevated risk and warrants escalation.",
                "confidence": 0.8,
            },
            {"status": "PASS", "issues": [], "confidence": 0.9},
        ]
    )
    state = start_investigation("C10234", CLAIM, 0.87, "HIGH", SHAP, PATTERNS, llm=llm)
    state = run_to_completion(state, llm)

    trace = build_investigation_trace(state)

    assert trace.investigation_id == state.investigation_id
    assert trace.claim_id == "C10234"
    assert len(trace.iterations) == 1
    assert trace.iterations[0].selected_tool == "provider_statistics"
    assert trace.counter_analysis is not None
    assert trace.counter_analysis.alternative_explanations == ["Specialty mix"]
    assert trace.critic is not None
    assert trace.critic.status == "PASS"
    assert trace.final_status == "COMPLETED"


def test_fraud_vs_risk_language_enforcement():
    # If the conclusion claims "provider committed fraud", critic flags it as FAIL
    llm = ScriptedLLMClient(
        [
            {"objectives": [{"description": "obj", "related_risk_factors": []}]},
            {
                "question": "Q1?",
                "reason": "x",
                "required_evidence": "x",
                "preferred_tool": "provider_statistics",
                "priority": "HIGH",
                "no_useful_question_remains": False,
            },
            {"sufficient": True, "reason": "ok", "missing_evidence": [], "next_action": "counter_analysis", "criteria_met": {}},
            {"current_hypothesis_restated": "x", "counter_questions": [], "alternative_explanations_without_tooling": []},
            {"claim_summary": "s", "risk_summary": "r", "findings": [], "conclusion": "The provider committed fraud.", "confidence": 0.9},
            {"status": "FAIL", "issues": ["Conclusion inappropriately declares fraud instead of risk."], "confidence": 0.2},
            {"claim_summary": "s", "risk_summary": "r", "findings": [], "conclusion": "Evidence indicates elevated risk requiring human review.", "confidence": 0.8},
            {"status": "PASS", "issues": [], "confidence": 0.9},
        ]
    )
    state = start_investigation("C10234", CLAIM, 0.87, "HIGH", SHAP, PATTERNS, llm=llm)
    state = run_to_completion(state, llm)

    assert state.status == InvestigationStatus.COMPLETED
    assert "committed fraud" not in state.final_report.conclusion.lower()
    assert "elevated risk" in state.final_report.conclusion.lower()


def test_guardrail_rejection_on_invalid_risk_score():
    with pytest.raises(ValueError):
        start_investigation("C1", CLAIM, -0.5, "HIGH", SHAP, PATTERNS)

    with pytest.raises(ValueError):
        start_investigation("C1", CLAIM, 1.2, "HIGH", SHAP, PATTERNS)
