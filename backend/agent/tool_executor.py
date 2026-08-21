"""
Executes a validated tool call, records the raw call, converts the result
into a human-readable Observation, and lifts any evidence dicts the tool
returned into typed Evidence objects on the state.

Distinguishes explicitly (per spec section 13):
  - SUCCESS: tool ran and found something
  - NO_EVIDENCE_FOUND: tool ran fine, nothing relevant exists
  - TOOL_FAILURE: tool raised / errored / timed out
  - INVALID_TOOL: tool name wasn't in the registry (should be rare -- the
    router should have already caught this, this is defense in depth)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from agent.state import new_id
from schemas.evidence import Evidence, EvidenceType
from schemas.investigation import InvestigationState
from schemas.question import InvestigationQuestion, Observation, ToolCallRecord
from schemas.tool import ToolResultStatus
from tools.base import get_tool, is_registered

logger = logging.getLogger("agent.tool_executor")

_EVIDENCE_TYPE_MAP = {
    "provider_statistics": EvidenceType.PROVIDER_STATISTIC,
    "provider_history": EvidenceType.PROVIDER_HISTORY,
    "provider_peer_comparison": EvidenceType.PEER_COMPARISON,
    "claim_history": EvidenceType.CLAIM_HISTORY,
    "rag": EvidenceType.POLICY,
    "ml": EvidenceType.ML_SCORE,
    "ml_scenario": EvidenceType.ML_SCENARIO,
}


def execute_tool(tool_name: str, question: InvestigationQuestion | None, state: InvestigationState) -> ToolCallRecord:
    """Executes the tool and appends a ToolCallRecord to state. Never raises."""
    from agent.tool_router import build_tool_input  # local import avoids circularity

    tool_call_id = new_id("tc")
    timestamp = datetime.now(timezone.utc).isoformat()

    if not is_registered(tool_name):
        record = ToolCallRecord(
            tool_call_id=tool_call_id,
            tool=tool_name,
            question_id=question.question_id if question else None,
            question=question.question if question else None,
            input={},
            result=None,
            status=ToolResultStatus.INVALID_TOOL,
            error=f"Tool '{tool_name}' is not registered.",
            timestamp=timestamp,
            iteration=state.iteration_count,
        )
        state.tool_calls.append(record)
        state.touch()
        return record

    tool = get_tool(tool_name)
    tool_input = build_tool_input(tool_name, question, state) if question else {}

    try:
        output = tool.run(**tool_input)
        status = output.status
        result_dict = output.model_dump()
        error = output.error
    except Exception as exc:  # unexpected tool crash
        logger.exception("Tool '%s' raised an exception", tool_name)
        status = ToolResultStatus.TOOL_FAILURE
        result_dict = None
        error = str(exc)
        output = None

    record = ToolCallRecord(
        tool_call_id=tool_call_id,
        tool=tool_name,
        question_id=question.question_id if question else None,
        question=question.question if question else None,
        input=tool_input,
        result=result_dict,
        status=status,
        error=error,
        timestamp=timestamp,
        iteration=state.iteration_count,
    )
    state.tool_calls.append(record)
    state.tool_results.append(result_dict or {})
    state.touch()

    if output is not None and status == ToolResultStatus.SUCCESS:
        _lift_evidence(tool_name, output, question, state)

    return record


def _lift_evidence(tool_name, output, question: InvestigationQuestion | None, state: InvestigationState) -> None:
    """Converts a tool's raw `evidence` dicts into typed Evidence on state, and stores citations."""
    ev_type = _EVIDENCE_TYPE_MAP.get(tool_name, EvidenceType.OTHER)
    for raw in output.evidence:
        # raw is an EvidenceItem (Pydantic model)
        evidence = Evidence(
            evidence_id=new_id("E"),
            type=ev_type,
            description=getattr(raw, "description", getattr(raw, "text", "")),
            source=getattr(raw, "source", tool_name),
            source_type=getattr(raw, "source_type", "tool_output"),
            supporting_data=getattr(output, "data", {}),
            confidence=getattr(raw, "confidence", getattr(output, "confidence", 0.5) or 0.5),
            related_question=question.question if question else None,
            tool_used=tool_name,
            created_at_iteration=state.iteration_count,
        )
        state.evidence.append(evidence)

    if hasattr(output, "citations"):
        for c in getattr(output, "citations", []):
            if isinstance(c, dict):
                state.citations.append(c)
            elif hasattr(c, "model_dump"):
                state.citations.append(c.model_dump())
            else:
                state.citations.append(dict(c))


def record_observation(record: ToolCallRecord, state: InvestigationState, text: str) -> Observation:
    """
    Stores a human-readable observation alongside the raw tool result.
    `text` is produced by the caller (orchestrator), typically via a short
    LLM summarization call -- kept out of this module so execution stays
    testable without an LLM.
    """
    obs = Observation(
        observation_id=new_id("obs"),
        tool_call_id=record.tool_call_id,
        question_id=record.question_id,
        text=text,
        iteration=state.iteration_count,
    )
    state.observations.append(obs)
    state.touch()
    return obs


def deterministic_observation_text(record: ToolCallRecord) -> str:
    """Fallback observation text (no LLM) used for TOOL_FAILURE/NO_EVIDENCE_FOUND
    or when LLM summarization is unavailable/fails."""
    if record.status == ToolResultStatus.TOOL_FAILURE:
        return f"Tool '{record.tool}' failed to execute: {record.error or 'unknown error'}."
    if record.status == ToolResultStatus.NO_EVIDENCE_FOUND:
        return f"Tool '{record.tool}' ran successfully but found no relevant evidence for: {record.question or 'the question'}."
    if record.status == ToolResultStatus.INVALID_TOOL:
        return f"Requested tool '{record.tool}' is not available."
    return f"Tool '{record.tool}' returned a result; see stored data for details."
