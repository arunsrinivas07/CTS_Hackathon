"""
Runs once evidence is deemed sufficient, BEFORE the final report. Challenges
the current hypothesis by generating and (where useful) answering
counter-questions, per spec section 19.

For the MVP this reuses the tool-call machinery: the LLM proposes 1-3
counter-questions, we route/execute the most tool-answerable ones (up to a
small cap so this can't itself become an unbounded loop), and store the
results as counter_evidence / alternative_explanations / contradictions.
"""
from __future__ import annotations

import json
import logging

from app.agent.tool_executor import deterministic_observation_text, execute_tool, record_observation
from app.agent.tool_router import resolve_tool
from app.agent.state import new_id
from app.llm.client import LLMClient, LLMError
from app.schemas.agentic.evidence import Evidence, EvidenceType
from app.schemas.agentic.investigation import InvestigationState
from app.schemas.agentic.question import InvestigationQuestion, Priority
from app.schemas.agentic.tool import ToolResultStatus

logger = logging.getLogger("agent.counter_analysis")

MAX_COUNTER_QUESTIONS = 2

SYSTEM_PROMPT = """You are the counter-analysis module of a healthcare claims
fraud investigation agent. Evidence has been deemed sufficient to support
the current hypothesis. Your job is to actively try to DISPROVE or QUALIFY
that hypothesis before any report is written.

Given the investigation state, propose up to 2 counter-questions that test
legitimate alternative explanations (e.g. specialty mix, patient population,
seasonal variation, data quality, temporary anomaly). For each, name the
best available tool to answer it, or "none" if no tool can help (in which
case it becomes a purely reasoning-based alternative explanation).

Respond with ONLY a JSON object, no prose, no markdown fences:
{
  "current_hypothesis_restated": "...",
  "counter_questions": [
    {"question": "...", "preferred_tool": "tool_name_or_none", "rationale": "..."}
  ],
  "alternative_explanations_without_tooling": ["..."]
}
"""


def _build_user_prompt(state: InvestigationState) -> str:
    payload = {
        "current_hypothesis": state.current_hypothesis,
        "risk_factors": [rf.model_dump() for rf in state.risk_factors],
        "evidence": [e.model_dump() for e in state.evidence],
        "available_tools": list({tc.tool for tc in state.tool_calls}) or "see registry",
    }
    return "Current investigation state:\n" + json.dumps(payload, indent=2, default=str)


def run_counter_analysis(state: InvestigationState, llm: LLMClient | None = None) -> None:
    llm = llm or LLMClient()
    try:
        raw = llm.complete_json(SYSTEM_PROMPT, _build_user_prompt(state))
    except LLMError as exc:
        logger.error("Counter-analysis LLM call failed: %s", exc)
        state.alternative_explanations.append(
            "Automated counter-analysis could not be completed due to an internal error; "
            "human reviewer should independently consider alternative explanations."
        )
        state.touch()
        return

    for explanation in raw.get("alternative_explanations_without_tooling", []) or []:
        if explanation not in state.alternative_explanations:
            state.alternative_explanations.append(explanation)

    counter_questions = (raw.get("counter_questions") or [])[:MAX_COUNTER_QUESTIONS]
    for cq in counter_questions:
        question_text = cq.get("question", "").strip()
        if not question_text:
            continue

        question = InvestigationQuestion(
            question_id=new_id("cq"),
            question=question_text,
            reason=cq.get("rationale", "Counter-analysis check."),
            required_evidence="Evidence for/against alternative explanation",
            preferred_tool=cq.get("preferred_tool", ""),
            priority=Priority.MEDIUM,
            iteration=state.iteration_count,
            is_counter_question=True,
        )
        state.questions.append(question)
        state.question_history.append(question_text)

        tool_name = resolve_tool(question)
        if not tool_name:
            state.alternative_explanations.append(
                f"{question_text} (no automated tool available to verify; noted for human reviewer)"
            )
            continue

        record = execute_tool(tool_name, question, state)
        obs_text = deterministic_observation_text(record)
        record_observation(record, state, obs_text)

        if record.status == ToolResultStatus.SUCCESS and record.result and record.result.get("evidence"):
            # Evidence gathered during counter-analysis is explicitly tagged
            # as counter_evidence, distinct from the primary evidence trail.
            for raw_ev in record.result["evidence"]:
                counter_ev = Evidence(
                    evidence_id=new_id("CE"),
                    type=EvidenceType.OTHER,
                    description=raw_ev.get("description", ""),
                    source=raw_ev.get("source", tool_name),
                    source_type=raw_ev.get("source_type", "tool_output"),
                    supporting_data=record.result.get("data", {}),
                    confidence=raw_ev.get("confidence", 0.5),
                    related_question=question_text,
                    tool_used=tool_name,
                    is_counter_evidence=True,
                    created_at_iteration=state.iteration_count,
                )
                state.counter_evidence.append(counter_ev)

    state.touch()
