"""
Investigation Trace Schema for Member 3 Investigator Copilot Consumption.

Provides a clean, structured, privacy-safe timeline of the investigation execution.
Excludes secrets, internal API keys, raw infrastructure errors, and sensitive internals.
"""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field

from app.schemas.agentic.investigation import InvestigationState, InvestigationStatus


class TraceIteration(BaseModel):
    iteration: int
    question: str
    selected_tool: str
    tool_status: str
    observation: str
    evidence_count: int
    decision: str


class TraceCounterAnalysis(BaseModel):
    counter_questions: list[str] = Field(default_factory=list)
    alternative_explanations: list[str] = Field(default_factory=list)
    counter_evidence_count: int = 0


class TraceCritic(BaseModel):
    status: str
    issues: list[str] = Field(default_factory=list)
    revision_count: int = 0


class LLMUsageSummary(BaseModel):
    total_calls: int = 0
    primary_provider: str = "groq"
    fallback_provider: str = "groq"
    fallback_trigger_count: int = 0
    last_provider_used: str = "groq"


class InvestigationTrace(BaseModel):
    investigation_id: str
    claim_id: str
    iterations: list[TraceIteration] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    counter_analysis: Optional[TraceCounterAnalysis] = None
    critic: Optional[TraceCritic] = None
    llm_usage: LLMUsageSummary = Field(default_factory=LLMUsageSummary)
    final_status: str


def build_investigation_trace(state: InvestigationState) -> InvestigationTrace:
    """Build a sanitized InvestigationTrace from InvestigationState."""
    iterations: list[TraceIteration] = []

    for idx, q in enumerate(state.questions):
        tool_call = state.tool_calls[idx] if idx < len(state.tool_calls) else None
        obs = state.observations[idx] if idx < len(state.observations) else None
        suff = state.sufficiency_history[idx] if idx < len(state.sufficiency_history) else None

        iterations.append(
            TraceIteration(
                iteration=q.iteration,
                question=q.question,
                selected_tool=tool_call.tool if tool_call else q.preferred_tool or "none",
                tool_status=tool_call.status if tool_call else "NOT_CALLED",
                observation=obs.text if obs else "",
                evidence_count=len(state.evidence),
                decision=suff.next_action if suff else "in_progress",
            )
        )

    clean_tool_calls = [
        {
            "tool_call_id": tc.tool_call_id,
            "tool": tc.tool,
            "question": tc.question,
            "status": tc.status,
            "timestamp": tc.timestamp,
        }
        for tc in state.tool_calls
    ]

    clean_evidence = [
        {
            "evidence_id": e.evidence_id,
            "type": e.type,
            "description": e.description,
            "source": e.source,
            "confidence": e.confidence,
            "related_question": e.related_question,
            "tool_used": e.tool_used,
        }
        for e in state.evidence
    ]

    ca_summary = None
    if state.counter_evidence or state.alternative_explanations:
        ca_summary = TraceCounterAnalysis(
            counter_questions=[q.question for q in state.questions if q.is_counter_question],
            alternative_explanations=state.alternative_explanations,
            counter_evidence_count=len(state.counter_evidence),
        )

    critic_summary = None
    if state.critic_result:
        critic_summary = TraceCritic(
            status=state.critic_result.status,
            issues=state.critic_result.issues,
            revision_count=state.revision_count,
        )

    decisions = [suff.reason for suff in state.sufficiency_history]

    return InvestigationTrace(
        investigation_id=state.investigation_id,
        claim_id=state.claim_id,
        iterations=iterations,
        questions=state.question_history,
        tool_calls=clean_tool_calls,
        observations=[o.text for o in state.observations],
        evidence=clean_evidence,
        decisions=decisions,
        counter_analysis=ca_summary,
        critic=critic_summary,
        llm_usage=LLMUsageSummary(
            total_calls=len(state.questions) + len(state.sufficiency_history) + 1,
            primary_provider="groq",
            fallback_provider="groq",
            fallback_trigger_count=0,
            last_provider_used="groq",
        ),
        final_status=state.status if isinstance(state.status, str) else state.status.value,
    )
