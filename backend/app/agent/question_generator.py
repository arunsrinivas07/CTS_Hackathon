"""
Generates ONE highest-value unresolved investigation question per iteration.

Design (per project spec section 10/11):
  - never dump a list of questions; always exactly one
  - reasoning is "what do we know / don't know / what reduces the most
    uncertainty / which tool can provide it"
  - must avoid repeating previous questions unless the prior answer was
    incomplete/contradictory
  - output is a structured InvestigationQuestion, validated against the
    registered tool list before being handed to the router
"""
from __future__ import annotations

import json
import logging

from app.agent.state import new_id, normalize_question_text
from app.llm.client import LLMClient, LLMError
from app.schemas.agentic.investigation import InvestigationState
from app.schemas.agentic.question import InvestigationQuestion, Priority
from app.tools.base import TOOL_REGISTRY

logger = logging.getLogger("agent.question_generator")

SYSTEM_PROMPT = """You are the reasoning module of a healthcare claims fraud investigation agent.

Your ONLY job: given the current investigation state, decide the SINGLE
highest-value next question to investigate, and which tool should answer it.

Rules:
- Output exactly ONE question, not a list.
- The question must target an unresolved risk factor, pattern, or evidence
  gap -- not something already answered by existing evidence.
- Do not repeat a question that is semantically equivalent to one in
  question_history, unless the prior answer was incomplete or contradictory
  (explain why if you do).
- The question must be answerable by exactly one of the available tools.
- Prefer questions that reduce the most uncertainty about whether the risk
  signal has a legitimate explanation or not.
- Respond with ONLY a JSON object, no prose, no markdown fences:
{
  "reasoning": "brief: what we know / what we don't know / why this question",
  "question": "the question text",
  "reason": "why this question matters given the risk factors",
  "required_evidence": "what evidence would answer it",
  "preferred_tool": "one of the available tool names",
  "priority": "HIGH" | "MEDIUM" | "LOW",
  "no_useful_question_remains": false
}
If truly no useful question remains (all objectives resolved or no tool can
help further), set "no_useful_question_remains": true and leave other
question fields empty strings.
"""


def _build_user_prompt(state: InvestigationState) -> str:
    available_tools = {name: t.description for name, t in TOOL_REGISTRY.items()}

    known_evidence = [
        {
            "description": e.description,
            "related_question": e.related_question,
            "confidence": e.confidence,
        }
        for e in state.evidence
    ]

    payload = {
        "claim_data": state.claim_data,
        "risk_score": state.risk_score,
        "risk_level": state.risk_level,
        "risk_factors": [rf.model_dump() for rf in state.risk_factors],
        "detected_patterns": [p.model_dump() for p in state.detected_patterns],
        "investigation_objectives": [o.model_dump() for o in state.investigation_objectives],
        "known_evidence": known_evidence,
        "evidence_gaps": [g.model_dump() for g in state.evidence_gaps if not g.resolved],
        "question_history": state.question_history,
        "available_tools": available_tools,
        "current_hypothesis": state.current_hypothesis,
        "iteration": state.iteration_count,
    }
    return "Current investigation state:\n" + json.dumps(payload, indent=2, default=str)


def generate_next_question(
    state: InvestigationState, llm: LLMClient | None = None
) -> InvestigationQuestion | None:
    """
    Returns the next InvestigationQuestion, or None if no useful question
    remains (caller should then move to counter-analysis/report).
    """
    llm = llm or LLMClient()

    if state.iteration_count == 1:
        return InvestigationQuestion(
            question_id=new_id("q"),
            question="Does the available claim data actually support the ML risk prediction?",
            reason="We must verify ML signals before proceeding with external evidence gathering.",
            required_evidence="ML verification report comparing claim features against risk factors.",
            preferred_tool="ml_verification",
            priority=Priority.HIGH,
            iteration=state.iteration_count,
        )

    try:
        result = llm.complete_json(SYSTEM_PROMPT, _build_user_prompt(state))
    except LLMError as exc:
        logger.error("Question generation LLM call failed: %s", exc)
        raise

    if result.get("no_useful_question_remains"):
        return None

    question_text = result.get("question", "").strip()
    if not question_text:
        return None

    normalized = normalize_question_text(question_text)
    if normalized in {normalize_question_text(q) for q in state.question_history}:
        # Model ignored the dedup instruction -- treat as "nothing new to ask".
        logger.warning("Question generator produced a duplicate question; treating as exhausted.")
        return None

    preferred_tool = result.get("preferred_tool", "")
    if preferred_tool not in TOOL_REGISTRY:
        logger.warning(
            "Question generator proposed unregistered tool '%s'; leaving unset for router fallback.",
            preferred_tool,
        )
        preferred_tool = ""

    priority_raw = result.get("priority", "MEDIUM").upper()
    priority = Priority(priority_raw) if priority_raw in Priority._value2member_map_ else Priority.MEDIUM

    # Iteration 2: if LLM didn't pick a DB/provider tool, force a RAG policy question
    # so we always get CMS policy evidence before concluding.
    if state.iteration_count == 2 and preferred_tool not in ("rag", "provider_history", "provider_statistics", "claim_history"):
        preferred_tool = "rag"
        # Also rewrite the question to be policy-focused if the LLM generated an ML question
        question_lower = question_text.lower()
        if any(kw in question_lower for kw in ["ml model", "risk score", "risk prediction", "ml risk"]):
            # Replace with a concrete policy question based on claim type/procedure
            procedure = state.claim_data.get("procedure", state.claim_data.get("primary_procedure", ""))
            claim_type = state.claim_data.get("claim_type", "")
            diagnosis = state.claim_data.get("diagnosis", state.claim_data.get("primary_diagnosis", ""))
            question_text = (
                f"What are the CMS medical necessity and coverage requirements for "
                f"{procedure or claim_type or 'this type of claim'}"
                f"{(' for diagnosis ' + diagnosis) if diagnosis and diagnosis != 'Unspecified' else ''}?"
            )

    question = InvestigationQuestion(
        question_id=new_id("q"),
        question=question_text,
        reason=result.get("reason", ""),
        required_evidence=result.get("required_evidence", ""),
        preferred_tool=preferred_tool,
        priority=priority,
        iteration=state.iteration_count,
    )
    return question
