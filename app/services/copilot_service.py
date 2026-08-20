"""
Copilot service — coordinates the full Investigator Copilot flow:

Question -> Guardrails -> Classify -> Retrieve InvestigationState ->
Check existing info -> (answer OR call approved tool) -> Grounded answer

This is the only place that ties the pieces together; individual services
(question_classifier, evidence_resolver, tool_router, guardrails) stay
independent and unit-testable.
"""

from __future__ import annotations

from app.adapters.investigation_state_adapter import InvestigationStateProvider
from app.schemas.copilot import (
    CopilotQueryRequest,
    CopilotQueryResponse,
    ToolUsageRecord,
)
from app.services import guardrails
from app.services.evidence_resolver import resolve_from_state
from app.services.question_classifier import classify_question
from app.services.tool_router import ToolRouter
from app.schemas.copilot import QuestionType


class CopilotService:
    def __init__(self, state_provider: InvestigationStateProvider, tool_router: ToolRouter) -> None:
        self._state_provider = state_provider
        self._tool_router = tool_router

    def answer_question(self, request: CopilotQueryRequest) -> CopilotQueryResponse:
        # 1. Guardrails on the incoming question (prompt injection, etc.)
        injection_check = guardrails.check_question_for_injection(request.question)
        if not injection_check.ok:
            return CopilotQueryResponse(
                investigation_id=request.investigation_id,
                question_type=QuestionType.UNKNOWN,
                answer=f"This request could not be processed: {injection_check.reason}",
                confidence=0.0,
            )

        # 2. Retrieve InvestigationState for the authorized investigation only
        state = self._state_provider.get_state(request.investigation_id)
        access_check = guardrails.check_investigation_access(
            request.investigation_id, state.investigation_id if state else None
        )
        if not access_check.ok:
            return CopilotQueryResponse(
                investigation_id=request.investigation_id,
                question_type=QuestionType.UNKNOWN,
                answer=access_check.reason or "This investigation could not be accessed.",
                confidence=0.0,
            )

        assert state is not None  # access_check guarantees this

        # 3. Classify the question
        question_type = classify_question(request.question)
        if question_type == QuestionType.UNKNOWN:
            return CopilotQueryResponse(
                investigation_id=request.investigation_id,
                question_type=question_type,
                answer=(
                    "I couldn't classify that question into a supported category. Try asking about risk, "
                    "evidence, counter-evidence, policy, provider history, the model score, a what-if scenario, "
                    "evidence gaps, the investigation trace, or the final recommendation."
                ),
                confidence=0.0,
            )

        # 4. Check whether existing InvestigationState already answers it
        resolved = resolve_from_state(question_type, state, request.question)

        if resolved.can_answer:
            answer_text = guardrails.sanitize_outgoing_answer(resolved.answer)
            return CopilotQueryResponse(
                investigation_id=request.investigation_id,
                question_type=question_type,
                answer=answer_text,
                evidence=resolved.evidence,
                citations=resolved.citations,
                tools_used=[],
                confidence=resolved.confidence,
                caveat=resolved.caveat,
            )

        # 5. Not answerable from state alone -> route to the single approved tool
        tool_result = self._tool_router.route(question_type, request.question, state)

        if tool_result is None:
            return CopilotQueryResponse(
                investigation_id=request.investigation_id,
                question_type=question_type,
                answer=(
                    "I don't currently have sufficient evidence in this investigation to answer that question, "
                    "and no approved tool is available for this type of question."
                ),
                confidence=0.2,
            )

        # 6. If the tool produced new evidence, attach it to InvestigationState
        #    (preserving provenance) rather than overwriting existing findings.
        if tool_result.new_evidence is not None:
            state.evidence.append(tool_result.new_evidence)
            self._state_provider.save_state(state)

        answer_text = guardrails.sanitize_outgoing_answer(tool_result.answer)
        tools_used = [tool_result.tool_usage] if tool_result.tool_usage else []

        return CopilotQueryResponse(
            investigation_id=request.investigation_id,
            question_type=question_type,
            answer=answer_text,
            evidence=tool_result.evidence,
            citations=tool_result.citations,
            tools_used=tools_used,
            confidence=tool_result.confidence,
            caveat=tool_result.caveat,
        )
