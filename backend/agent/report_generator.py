"""
Generates the draft conclusion (fed to the critic) and, once the critic
passes, assembles the full structured FinalReport from InvestigationState.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from llm.client import LLMClient, LLMError
from schemas.investigation import CriticResult, FinalReport, InvestigationState

logger = logging.getLogger("agent.report_generator")

DRAFT_SYSTEM_PROMPT = """You are drafting the conclusion section of a
healthcare claims fraud investigation report.

STRICT LANGUAGE RULES:
- An ML risk score is NOT proof of fraud.
- SHAP/feature importance is NOT proof of causality.
- A statistical outlier is NOT automatically fraud.
- Policy evidence is NOT proof of intentional violation.
- Use careful, calibrated language: "presents elevated fraud risk",
  "exhibits anomalous billing behavior", "evidence supports further
  investigation", "consistent with...". NEVER assert that fraud was
  committed or confirmed.
- Explicitly acknowledge counter-evidence, alternative explanations, and
  remaining evidence gaps rather than omitting them.

Respond with ONLY a JSON object, no prose, no markdown fences:
{
  "claim_summary": "...",
  "risk_summary": "...",
  "findings": ["finding 1", "finding 2", "..."],
  "conclusion": "2-4 sentence calibrated conclusion paragraph",
  "confidence": 0.0-1.0
}
"""


def _build_draft_prompt(state: InvestigationState) -> str:
    payload = {
        "claim_data": state.claim_data,
        "risk_score": state.risk_score,
        "risk_level": state.risk_level,
        "risk_factors": [rf.model_dump() for rf in state.risk_factors],
        "detected_patterns": [p.model_dump() for p in state.detected_patterns],
        "objectives": [o.model_dump() for o in state.investigation_objectives],
        "evidence": [e.model_dump() for e in state.evidence],
        "counter_evidence": [e.model_dump() for e in state.counter_evidence],
        "alternative_explanations": state.alternative_explanations,
        "evidence_gaps": [g.model_dump() for g in state.evidence_gaps],
    }
    return "Investigation state:\n" + json.dumps(payload, indent=2, default=str)


def draft_conclusion(state: InvestigationState, llm: LLMClient | None = None) -> dict:
    llm = llm or LLMClient(max_tokens=1200)
    try:
        return llm.complete_json(DRAFT_SYSTEM_PROMPT, _build_draft_prompt(state))
    except LLMError as exc:
        logger.error("Draft conclusion LLM call failed: %s", exc)
        return {
            "claim_summary": f"Claim {state.claim_id}.",
            "risk_summary": f"ML risk score {state.risk_score} ({state.risk_level}).",
            "findings": ["Draft could not be generated automatically due to an internal error."],
            "conclusion": (
                "An automated draft conclusion could not be generated due to an internal "
                "error. This case requires human review."
            ),
            "confidence": 0.0,
        }


def build_final_report(state: InvestigationState, draft: dict, critic_result: CriticResult) -> FinalReport:
    report = FinalReport(
        investigation_id=state.investigation_id,
        claim_summary=draft.get("claim_summary", ""),
        risk_summary=draft.get("risk_summary", ""),
        risk_factors=state.risk_factors,
        detected_patterns=state.detected_patterns,
        investigation_objectives=state.investigation_objectives,
        questions_asked=[q.question for q in state.questions],
        tools_used=sorted({tc.tool for tc in state.tool_calls}),
        evidence_collected=state.evidence,
        citations=state.citations,
        counter_evidence=state.counter_evidence,
        alternative_explanations=state.alternative_explanations,
        evidence_gaps=state.evidence_gaps,
        findings=draft.get("findings", []) or [],
        confidence=float(draft.get("confidence", 0.0) or 0.0),
        critic_result=critic_result,
        conclusion=draft.get("conclusion", ""),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    state.final_report = report
    state.touch()
    return report
