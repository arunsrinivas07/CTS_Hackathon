"""
Generates the draft conclusion (fed to the critic) and, once the critic
passes, assembles the full structured FinalReport from InvestigationState.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from app.llm.client import LLMClient, LLMError
from app.schemas.agentic.investigation import CriticResult, FinalReport, InvestigationState

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


def _derive_findings_from_evidence(state: InvestigationState) -> list[str]:
    """Derive concrete findings directly from collected evidence — used as fallback when LLM draft is empty."""
    findings = []
    for ev in state.evidence:
        desc = ev.description or ""
        if not desc:
            continue
        ev_type = str(ev.type.value if hasattr(ev.type, 'value') else ev.type)
        if ev_type == "ml_score":
            findings.append(f"ML Assessment: {desc[:200]}")
        elif ev_type == "provider_history":
            findings.append(f"Provider History: {desc[:200]}")
        elif ev_type == "provider_statistic":
            findings.append(f"Provider Statistics: {desc[:200]}")
        elif ev_type == "peer_comparison":
            findings.append(f"Peer Comparison: {desc[:200]}")
        elif ev_type == "policy":
            findings.append(f"Policy Evidence: {desc[:200]}")
        elif ev_type == "claim_history":
            findings.append(f"Claim History: {desc[:200]}")
        else:
            findings.append(desc[:200])

    if state.alternative_explanations:
        for exp in state.alternative_explanations[:2]:
            findings.append(f"Alternative Explanation: {exp[:200]}")

    if state.evidence_gaps:
        gap_count = len([g for g in state.evidence_gaps if not g.resolved])
        if gap_count:
            findings.append(f"{gap_count} evidence gap(s) remain unresolved and require human review.")

    if not findings:
        findings.append(
            f"Claim {state.claim_id} assigned ML risk score {state.risk_score:.3f} ({state.risk_level}). "
            f"Investigation collected {len(state.evidence)} evidence items across "
            f"{len(state.tool_calls)} tool executions. Human review is recommended."
        )
    return findings


def build_final_report(state: InvestigationState, draft: dict, critic_result: CriticResult) -> FinalReport:
    conclusion = draft.get("conclusion", "")
    claim_summary = draft.get("claim_summary", "")
    risk_summary = draft.get("risk_summary", "")

    # Use LLM-drafted findings if available, otherwise derive from real evidence
    findings = draft.get("findings") or []
    if not findings:
        findings = _derive_findings_from_evidence(state)

    # Build a human-readable recommendation based on confidence and critic
    confidence = float(draft.get("confidence", 0.0) or 0.0)
    if state.risk_score >= 0.75 or confidence >= 0.70:
        recommendation = "Recommend referral to SIU for formal audit given elevated risk and collected evidence."
    elif state.risk_score >= 0.50 or confidence >= 0.40:
        recommendation = "Evidence is inconclusive. Recommend additional investigation before payment decision."
    else:
        recommendation = "Insufficient evidence to support a fraud finding. Consider approving with standard monitoring."

    if not claim_summary:
        claim_summary = (
            f"Claim {state.claim_id} ({state.claim_data.get('claim_type','')}) "
            f"billed ${state.claim_amount:,.2f} by provider {state.provider_name}."
        )
    if not risk_summary:
        risk_summary = (
            f"ML hybrid engine assigned risk score {state.risk_score:.3f} ({state.risk_level}). "
            f"{len(state.risk_factors)} risk factor(s) identified."
        )
    if not conclusion:
        conclusion = (
            f"This claim presents a {state.risk_level.lower()} risk profile with score {state.risk_score:.3f}. "
            f"Investigation collected {len(state.evidence)} evidence items. "
            f"{'Critic flagged issues requiring human review.' if critic_result.status == 'FAIL' else 'Evidence supports the risk assessment.'}"
        )

    report = FinalReport(
        investigation_id=state.investigation_id,
        claim_summary=claim_summary,
        risk_summary=risk_summary,
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
        findings=findings,
        confidence=confidence,
        critic_result=critic_result,
        conclusion=conclusion,
        generated_at=datetime.now(timezone.utc).isoformat(),
        summary=claim_summary,
        recommendation=recommendation,
        rationale=conclusion or risk_summary,
    )
    state.final_report = report
    state.touch()
    return report
