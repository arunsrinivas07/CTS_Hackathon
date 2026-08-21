"""
Evaluates whether collected evidence is sufficient to proceed to
counter-analysis, using explicit criteria (spec section 16) rather than a
bare boolean.
"""
from __future__ import annotations

import json
import logging

from agent.state import new_id
from llm.client import LLMClient, LLMError
from schemas.evidence import EvidenceGap, EvidenceSufficiencyResult
from schemas.investigation import InvestigationState

logger = logging.getLogger("agent.evidence_evaluator")

SYSTEM_PROMPT = """You are the evidence-sufficiency evaluator for a healthcare
claims fraud investigation agent.

Evaluate whether the evidence collected so far is sufficient to move to
counter-analysis and a final report, using these explicit criteria:
1. important_risk_signal_supported: the top risk factor(s) have supporting
   or refuting evidence, not just the raw ML score
2. evidence_relevant: evidence actually relates to the claim/provider/objectives
3. claim_or_provider_verified: at least one independent data source (not
   just the ML model) has been checked
4. authoritative_source_available: if a policy/clinical question exists, an
   authoritative source (e.g. RAG) has been consulted where required
5. contradictions_considered: any conflicting evidence has been noted, not ignored
6. critical_gaps_resolved: no HIGH-priority evidence gap remains open
7. citations_present: important findings have a traceable source/citation
8. conclusion_supportable: a reasonable conclusion could be written that
   is actually backed by the evidence gathered

Respond with ONLY a JSON object, no prose, no markdown fences:
{
  "sufficient": true|false,
  "reason": "concise explanation",
  "missing_evidence": ["..."],
  "next_action": "generate_question" | "counter_analysis" | "escalate",
  "criteria_met": {
    "important_risk_signal_supported": true|false,
    "evidence_relevant": true|false,
    "claim_or_provider_verified": true|false,
    "authoritative_source_available": true|false,
    "contradictions_considered": true|false,
    "critical_gaps_resolved": true|false,
    "citations_present": true|false,
    "conclusion_supportable": true|false
  }
}
Use "escalate" for next_action only if a critical tool has failed repeatedly
and no path to sufficient evidence remains.
"""


def _build_user_prompt(state: InvestigationState) -> str:
    payload = {
        "risk_factors": [rf.model_dump() for rf in state.risk_factors],
        "detected_patterns": [p.model_dump() for p in state.detected_patterns],
        "investigation_objectives": [o.model_dump() for o in state.investigation_objectives],
        "evidence": [e.model_dump() for e in state.evidence],
        "tool_calls_summary": [
            {"tool": tc.tool, "status": tc.status, "question": tc.question} for tc in state.tool_calls
        ],
        "iteration": state.iteration_count,
        "max_iterations": state.max_iterations,
    }
    return "Current investigation state:\n" + json.dumps(payload, indent=2, default=str)


def evaluate_sufficiency(state: InvestigationState, llm: LLMClient | None = None) -> EvidenceSufficiencyResult:
    llm = llm or LLMClient()
    try:
        raw = llm.complete_json(SYSTEM_PROMPT, _build_user_prompt(state))
    except LLMError as exc:
        logger.error("Evidence evaluation LLM call failed: %s", exc)
        # Fail safe: treat as insufficient so the loop doesn't wrongly finalize,
        # but flag it as a gap the human should know about.
        return EvidenceSufficiencyResult(
            sufficient=False,
            reason=f"Evaluation could not be performed due to an internal error: {exc}",
            missing_evidence=["Automated evidence evaluation failed"],
            next_action="escalate",
        )

    result = EvidenceSufficiencyResult(
        sufficient=bool(raw.get("sufficient", False)),
        reason=raw.get("reason", ""),
        missing_evidence=raw.get("missing_evidence", []) or [],
        next_action=raw.get("next_action", "generate_question"),
        criteria_met=raw.get("criteria_met", {}) or {},
    )

    state.sufficiency_history.append(result)

    # Record/refresh evidence gaps for anything newly flagged as missing.
    existing_gap_texts = {g.description for g in state.evidence_gaps}
    for missing in result.missing_evidence:
        if missing not in existing_gap_texts:
            state.evidence_gaps.append(EvidenceGap(description=missing))

    if result.sufficient:
        for gap in state.evidence_gaps:
            gap.resolved = True

    state.touch()
    return result
