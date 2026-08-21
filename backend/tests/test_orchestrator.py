from agent.orchestrator import finalize_investigation, run_iteration, run_to_completion, start_investigation
from schemas.investigation import InvestigationStatus
from tests.conftest import ScriptedLLMClient

CLAIM = {"provider_id": "ABC123", "procedure": "MRI", "diagnosis": "Lower back pain", "amount": 4800, "patient_id": "P001"}
SHAP = [{"feature": "procedure_frequency", "value": 0.34}, {"feature": "provider_deviation", "value": 0.28}]
PATTERNS = [{"name": "high_procedure_frequency"}, {"name": "provider_outlier"}]


def test_start_investigation_derives_objectives_and_initializes_state():
    llm = ScriptedLLMClient(
        [{"objectives": [{"description": "Check if MRI volume is anomalous.", "related_risk_factors": ["procedure_frequency"]}]}]
    )
    state = start_investigation("C10234", CLAIM, 0.87, "HIGH", SHAP, PATTERNS, llm=llm)
    assert state.status == InvestigationStatus.IN_PROGRESS
    assert len(state.investigation_objectives) == 1
    assert state.current_hypothesis is not None


def test_start_investigation_guardrail_rejects_bad_risk_score():
    import pytest
    with pytest.raises(ValueError):
        start_investigation("C1", CLAIM, 1.5, "HIGH", SHAP, PATTERNS, llm=ScriptedLLMClient([]))


def test_full_normal_investigation_reaches_completed_report():
    llm = ScriptedLLMClient(
        [
            # start_investigation: objectives
            {"objectives": [{"description": "Check provider volume anomaly.", "related_risk_factors": ["procedure_frequency"]}]},
            # iteration 1: question
            {
                "question": "Is provider MRI volume above peer 95th percentile?",
                "reason": "top risk factor",
                "required_evidence": "provider vs peer stats",
                "preferred_tool": "provider_statistics",
                "priority": "HIGH",
                "no_useful_question_remains": False,
            },
            # iteration 1: sufficiency -> sufficient
            {
                "sufficient": True,
                "reason": "Provider statistic evidence obtained and strong.",
                "missing_evidence": [],
                "next_action": "counter_analysis",
                "criteria_met": {},
            },
            # counter-analysis
            {
                "current_hypothesis_restated": "Provider is an outlier.",
                "counter_questions": [],
                "alternative_explanations_without_tooling": ["Provider specialty could explain some volume."],
            },
            # draft conclusion
            {
                "claim_summary": "MRI claim from ABC Medical Center.",
                "risk_summary": "High risk score driven by procedure frequency.",
                "findings": ["Provider volume exceeds peer 95th percentile."],
                "conclusion": "The claim presents elevated fraud risk and warrants further investigation.",
                "confidence": 0.8,
            },
            # critic -> PASS
            {"status": "PASS", "issues": [], "confidence": 0.9},
        ]
    )
    state = start_investigation("C10234", CLAIM, 0.87, "HIGH", SHAP, PATTERNS, llm=llm)
    state = run_to_completion(state, llm)

    assert state.status == InvestigationStatus.COMPLETED
    assert state.final_report is not None
    assert "fraud risk" in state.final_report.conclusion
    assert "committed fraud" not in state.final_report.conclusion.lower()
    assert len(state.evidence) >= 1  # provider_statistics mock evidence was captured


def test_max_iterations_reached_then_finalized():
    # Question generator ALWAYS returns a new (non-duplicate) question, and
    # sufficiency ALWAYS says insufficient -> loop should hit max_iterations.
    responses = [
        {"objectives": [{"description": "obj", "related_risk_factors": []}]},
    ]
    for i in range(5):
        responses.append(
            {
                "question": f"Question number {i}?",
                "reason": "x", "required_evidence": "x",
                "preferred_tool": "provider_statistics", "priority": "MEDIUM",
                "no_useful_question_remains": False,
            }
        )
        responses.append(
            {"sufficient": False, "reason": "still missing", "missing_evidence": ["gap"], "next_action": "generate_question", "criteria_met": {}}
        )
    # finalize path after MAX_ITERATIONS_REACHED
    responses.append({"current_hypothesis_restated": "x", "counter_questions": [], "alternative_explanations_without_tooling": []})
    responses.append({"claim_summary": "s", "risk_summary": "r", "findings": [], "conclusion": "Evidence supports further investigation.", "confidence": 0.5})
    responses.append({"status": "PASS", "issues": [], "confidence": 0.6})

    llm = ScriptedLLMClient(responses)
    state = start_investigation("C10234", CLAIM, 0.87, "HIGH", SHAP, PATTERNS, max_iterations=5, llm=llm)
    state = run_to_completion(state, llm)

    assert state.iteration_count == 5
    assert state.status == InvestigationStatus.COMPLETED  # finalized even after hitting the cap


def test_critic_fail_triggers_revision_then_passes():
    llm = ScriptedLLMClient(
        [
            {"objectives": [{"description": "obj", "related_risk_factors": []}]},
            {"question": "Q1?", "reason": "x", "required_evidence": "x", "preferred_tool": "provider_statistics", "priority": "HIGH", "no_useful_question_remains": False},
            {"sufficient": True, "reason": "ok", "missing_evidence": [], "next_action": "counter_analysis", "criteria_met": {}},
            {"current_hypothesis_restated": "x", "counter_questions": [], "alternative_explanations_without_tooling": []},
            # draft 1 (bad conclusion)
            {"claim_summary": "s", "risk_summary": "r", "findings": [], "conclusion": "The provider committed fraud.", "confidence": 0.9},
            # critic FAIL
            {"status": "FAIL", "issues": ["Conclusion implies fraud without sufficient evidence."], "confidence": 0.2},
            # draft 2 (fixed)
            {"claim_summary": "s", "risk_summary": "r", "findings": [], "conclusion": "The evidence supports further investigation.", "confidence": 0.8},
            # critic PASS
            {"status": "PASS", "issues": [], "confidence": 0.85},
        ]
    )
    state = start_investigation("C10234", CLAIM, 0.87, "HIGH", SHAP, PATTERNS, llm=llm)
    state = run_to_completion(state, llm)

    assert state.status == InvestigationStatus.COMPLETED
    assert state.revision_count == 1
    assert len(state.critic_history) == 2
    assert state.critic_history[0].status == "FAIL"
    assert state.critic_history[1].status == "PASS"


def test_critic_max_revisions_escalates_to_human_review():
    responses = [
        {"objectives": [{"description": "obj", "related_risk_factors": []}]},
        {"question": "Q1?", "reason": "x", "required_evidence": "x", "preferred_tool": "provider_statistics", "priority": "HIGH", "no_useful_question_remains": False},
        {"sufficient": True, "reason": "ok", "missing_evidence": [], "next_action": "counter_analysis", "criteria_met": {}},
        {"current_hypothesis_restated": "x", "counter_questions": [], "alternative_explanations_without_tooling": []},
    ]
    # draft + FAIL, repeated for initial + 2 revisions = 3 draft/critic pairs, all FAIL
    for _ in range(3):
        responses.append({"claim_summary": "s", "risk_summary": "r", "findings": [], "conclusion": "bad", "confidence": 0.1})
        responses.append({"status": "FAIL", "issues": ["still bad"], "confidence": 0.1})

    llm = ScriptedLLMClient(responses)
    state = start_investigation("C10234", CLAIM, 0.87, "HIGH", SHAP, PATTERNS, max_revisions=2, llm=llm)
    state = run_to_completion(state, llm)

    assert state.status == InvestigationStatus.REQUIRES_HUMAN_REVIEW
    assert state.revision_count == 2
    assert state.final_report is None  # never finalized an unvetted report


def test_evidence_evaluator_escalation_path_sets_human_review():
    llm = ScriptedLLMClient(
        [
            {"objectives": [{"description": "obj", "related_risk_factors": []}]},
            {"question": "Q1?", "reason": "x", "required_evidence": "x", "preferred_tool": "provider_statistics", "priority": "HIGH", "no_useful_question_remains": False},
            {"sufficient": False, "reason": "critical tool failure", "missing_evidence": ["x"], "next_action": "escalate", "criteria_met": {}},
        ]
    )
    state = start_investigation("C10234", CLAIM, 0.87, "HIGH", SHAP, PATTERNS, llm=llm)
    state = run_iteration(state, llm)
    assert state.status == InvestigationStatus.REQUIRES_HUMAN_REVIEW


def test_no_useful_question_moves_straight_to_counter_analysis():
    llm = ScriptedLLMClient(
        [
            {"objectives": [{"description": "obj", "related_risk_factors": []}]},
            {"no_useful_question_remains": True},
        ]
    )
    state = start_investigation("C10234", CLAIM, 0.87, "HIGH", SHAP, PATTERNS, llm=llm)
    state = run_iteration(state, llm)
    assert state.status == InvestigationStatus.COUNTER_ANALYSIS
    assert len(state.questions) == 0
