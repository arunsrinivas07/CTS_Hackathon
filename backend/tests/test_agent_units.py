from agent.evidence_evaluator import evaluate_sufficiency
from agent.question_generator import generate_next_question
from agent.state import initialize_investigation
from agent.tool_executor import deterministic_observation_text, execute_tool, record_observation
from agent.tool_router import build_tool_input, resolve_tool
from schemas.investigation import InvestigationStatus
from schemas.question import InvestigationQuestion, Priority
from schemas.tool import ToolResultStatus
from tests.conftest import ScriptedLLMClient


def make_state(sample_claim, risk_score=0.87):
    return initialize_investigation(
        claim_id="C10234",
        claim_data=sample_claim,
        risk_score=risk_score,
        risk_level="HIGH",
        shap_contributors=[
            {"feature": "procedure_frequency", "value": 0.34},
            {"feature": "provider_deviation", "value": 0.28},
        ],
        detected_patterns=[{"name": "high_procedure_frequency"}, {"name": "provider_outlier"}],
    )


# ---------------------------------------------------------------------------
# Question generation
# ---------------------------------------------------------------------------

def test_question_generation_produces_structured_question(sample_claim):
    state = make_state(sample_claim)
    llm = ScriptedLLMClient(
        [
            {
                "reasoning": "Procedure frequency is a top risk driver and unverified.",
                "question": "Is this provider's MRI volume significantly above comparable providers?",
                "reason": "Procedure frequency is a major contributor to model risk.",
                "required_evidence": "Provider and peer MRI statistics",
                "preferred_tool": "provider_statistics",
                "priority": "HIGH",
                "no_useful_question_remains": False,
            }
        ]
    )
    question = generate_next_question(state, llm)
    assert isinstance(question, InvestigationQuestion)
    assert question.preferred_tool == "provider_statistics"
    assert question.priority == Priority.HIGH


def test_question_generation_respects_no_useful_question(sample_claim):
    state = make_state(sample_claim)
    llm = ScriptedLLMClient([{"no_useful_question_remains": True}])
    question = generate_next_question(state, llm)
    assert question is None


def test_question_generation_dedup_treated_as_exhausted(sample_claim):
    state = make_state(sample_claim)
    state.question_history.append("Is this provider's MRI volume significantly above comparable providers?")
    llm = ScriptedLLMClient(
        [
            {
                "question": "Is this provider's MRI volume significantly above comparable providers?",
                "reason": "x",
                "required_evidence": "x",
                "preferred_tool": "provider_statistics",
                "priority": "HIGH",
                "no_useful_question_remains": False,
            }
        ]
    )
    question = generate_next_question(state, llm)
    assert question is None  # duplicate -> treated as nothing new


def test_question_generation_unregistered_tool_is_dropped(sample_claim):
    state = make_state(sample_claim)
    llm = ScriptedLLMClient(
        [
            {
                "question": "Some question?",
                "reason": "x",
                "required_evidence": "x",
                "preferred_tool": "sql_admin_console",  # NOT in registry
                "priority": "HIGH",
                "no_useful_question_remains": False,
            }
        ]
    )
    question = generate_next_question(state, llm)
    assert question.preferred_tool == ""  # sanitized, not the dangerous value


# ---------------------------------------------------------------------------
# Tool routing / execution
# ---------------------------------------------------------------------------

def test_resolve_tool_uses_valid_preferred_tool():
    q = InvestigationQuestion(
        question_id="q1", question="x", reason="x", required_evidence="x",
        preferred_tool="provider_statistics", priority=Priority.HIGH, iteration=1,
    )
    assert resolve_tool(q) == "provider_statistics"


def test_resolve_tool_rejects_unregistered_and_falls_back_on_keywords():
    q = InvestigationQuestion(
        question_id="q1", question="Is there applicable policy for MRI?", reason="x",
        required_evidence="x", preferred_tool="not_a_real_tool", priority=Priority.HIGH, iteration=1,
    )
    resolved = resolve_tool(q)
    assert resolved == "rag"  # fallback keyword match, never the invalid tool name


def test_execute_tool_invalid_tool_records_invalid_status(sample_claim):
    state = make_state(sample_claim)
    record = execute_tool("totally_made_up_tool", None, state)
    assert record.status == ToolResultStatus.INVALID_TOOL
    assert state.tool_calls[-1].tool == "totally_made_up_tool"


def test_execute_tool_success_lifts_evidence(sample_claim):
    state = make_state(sample_claim)
    q = InvestigationQuestion(
        question_id="q1", question="Is provider volume an outlier?", reason="x",
        required_evidence="x", preferred_tool="provider_statistics", priority=Priority.HIGH, iteration=1,
    )
    record = execute_tool("provider_statistics", q, state)
    assert record.status == ToolResultStatus.SUCCESS
    assert len(state.evidence) == 1
    assert state.evidence[0].tool_used == "provider_statistics"


def test_execute_tool_no_evidence_found_is_distinct_from_failure(sample_claim):
    state = make_state(sample_claim)
    # RAG mock returns NO_EVIDENCE_FOUND for non-MRI procedures
    q = InvestigationQuestion(
        question_id="q1", question="policy question", reason="x",
        required_evidence="x", preferred_tool="rag", priority=Priority.HIGH, iteration=1,
    )
    state.claim_data["procedure"] = "X-Ray"
    record = execute_tool("rag", q, state)
    assert record.status == ToolResultStatus.NO_EVIDENCE_FOUND
    assert record.status != ToolResultStatus.TOOL_FAILURE
    text = deterministic_observation_text(record)
    assert "no relevant evidence" in text.lower()


def test_execute_tool_missing_required_input_is_tool_failure(sample_claim):
    state = make_state(sample_claim)
    state.claim_data["provider_id"] = None
    q = InvestigationQuestion(
        question_id="q1", question="x", reason="x", required_evidence="x",
        preferred_tool="provider_statistics", priority=Priority.HIGH, iteration=1,
    )
    record = execute_tool("provider_statistics", q, state)
    assert record.status == ToolResultStatus.TOOL_FAILURE


def test_build_tool_input_maps_claim_fields(sample_claim):
    state = make_state(sample_claim)
    q = InvestigationQuestion(
        question_id="q1", question="x", reason="x", required_evidence="x",
        preferred_tool="provider_statistics", priority=Priority.HIGH, iteration=1,
    )
    inp = build_tool_input("provider_statistics", q, state)
    assert inp["provider_id"] == "ABC123"
    assert inp["procedure"] == "MRI"


# ---------------------------------------------------------------------------
# Evidence sufficiency
# ---------------------------------------------------------------------------

def test_evidence_sufficiency_insufficient_creates_gap(sample_claim):
    state = make_state(sample_claim)
    llm = ScriptedLLMClient(
        [
            {
                "sufficient": False,
                "reason": "Clinical documentation missing.",
                "missing_evidence": ["Clinical documentation supporting medical necessity"],
                "next_action": "generate_question",
                "criteria_met": {},
            }
        ]
    )
    result = evaluate_sufficiency(state, llm)
    assert result.sufficient is False
    assert len(state.evidence_gaps) == 1
    assert state.evidence_gaps[0].resolved is False


def test_evidence_sufficiency_sufficient_resolves_gaps(sample_claim):
    state = make_state(sample_claim)
    from schemas.evidence import EvidenceGap
    state.evidence_gaps.append(EvidenceGap(description="something"))
    llm = ScriptedLLMClient(
        [{"sufficient": True, "reason": "ok", "missing_evidence": [], "next_action": "counter_analysis", "criteria_met": {}}]
    )
    result = evaluate_sufficiency(state, llm)
    assert result.sufficient is True
    assert all(g.resolved for g in state.evidence_gaps)


def test_evidence_sufficiency_llm_failure_escalates_safely(sample_claim):
    state = make_state(sample_claim)
    llm = ScriptedLLMClient(raise_on_call=True)
    result = evaluate_sufficiency(state, llm)
    assert result.sufficient is False
    assert result.next_action == "escalate"
