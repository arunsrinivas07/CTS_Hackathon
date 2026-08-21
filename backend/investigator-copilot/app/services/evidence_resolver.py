"""
State evidence resolver.

Responsible for:
1. Deciding whether the existing InvestigationState already contains
   enough information to answer a classified question (`can_answer`).
2. Building the grounded answer directly from InvestigationState when it can.

Tool calls are only ever triggered when this resolver reports it cannot
answer from existing state (see tool_router.py / copilot_service.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from app.schemas.copilot import CitationItemOut, EvidenceItemOut, QuestionType
from schemas.investigation import InvestigationState


@dataclass
class ResolvedAnswer:
    can_answer: bool
    answer: str = ""
    evidence: List[EvidenceItemOut] = field(default_factory=list)
    citations: List[CitationItemOut] = field(default_factory=list)
    confidence: float = 0.0
    caveat: Optional[str] = None
    # populated when can_answer=False, to tell the tool router what's needed
    missing_reason: Optional[str] = None


def resolve_from_state(question_type: QuestionType, state: InvestigationState, question: str) -> ResolvedAnswer:
    handler = _HANDLERS.get(question_type)
    if handler is None:
        return ResolvedAnswer(
            can_answer=False,
            missing_reason="Question type is not recognized by the Copilot.",
        )
    return handler(state, question)


# ---------------------------------------------------------------------------
# Per-question-type handlers
# ---------------------------------------------------------------------------

def _investigation_summary(state: InvestigationState, _q: str) -> ResolvedAnswer:
    if not state.final_report:
        return ResolvedAnswer(can_answer=False, missing_reason="No final report available yet in InvestigationState.")
    answer = (
        f"{state.final_report.summary} "
        f"Risk score: {state.risk_score:.2f}. "
        f"{len(state.evidence)} evidence item(s), {len(state.counter_evidence)} counter-evidence item(s), "
        f"and {len(state.evidence_gaps)} evidence gap(s) were recorded during the investigation."
    )
    return ResolvedAnswer(
        can_answer=True,
        answer=answer,
        evidence=[_ev_out(e) for e in state.evidence],
        citations=[_cit_out(c) for c in state.citations],
        confidence=0.9,
    )


def _risk_explanation(state: InvestigationState, _q: str) -> ResolvedAnswer:
    if not state.risk_factors and not state.shap_factors:
        return ResolvedAnswer(can_answer=False, missing_reason="No risk_factors or shap_factors in InvestigationState.")

    factor_lines = [f"{rf.name}: {rf.description}" for rf in state.risk_factors]
    shap_lines = [f"{sf.feature} ({sf.direction}): {sf.description}" for sf in state.shap_factors]

    answer = (
        f"This claim has a risk score of {state.risk_score:.2f}. "
        f"The strongest contributing factors are: " + "; ".join(factor_lines) + ". "
        f"Model-level (SHAP) explanation: " + "; ".join(shap_lines) + "."
    )
    return ResolvedAnswer(
        can_answer=True,
        answer=answer,
        evidence=[_ev_out(e) for e in state.evidence if e.supports in ("provider_anomaly", "amount_outlier")],
        confidence=0.88,
        caveat="A high risk score is an indicator for review, not proof of fraud.",
    )


def _evidence_question(state: InvestigationState, _q: str) -> ResolvedAnswer:
    if not state.evidence:
        return ResolvedAnswer(can_answer=False, missing_reason="No evidence recorded in InvestigationState.")
    lines = [f"{e.summary or e.description} ({e.source})" for e in state.evidence]
    answer = "The evidence gathered so far includes: " + "; ".join(lines) + "."
    return ResolvedAnswer(
        can_answer=True,
        answer=answer,
        evidence=[_ev_out(e) for e in state.evidence],
        citations=[_cit_out(c) for c in state.citations],
        confidence=0.85,
    )


def _counter_evidence(state: InvestigationState, _q: str) -> ResolvedAnswer:
    if not state.counter_evidence:
        return ResolvedAnswer(
            can_answer=True,
            answer="No counter-evidence has been recorded for this investigation so far.",
            confidence=0.7,
        )
    lines = [f"{ce.summary or ce.description} ({ce.source})" for ce in state.counter_evidence]
    answer = "The following counter-evidence was found: " + "; ".join(lines) + "."
    return ResolvedAnswer(can_answer=True, answer=answer, confidence=0.85)


def _evidence_gap(state: InvestigationState, _q: str) -> ResolvedAnswer:
    if not state.evidence_gaps:
        return ResolvedAnswer(
            can_answer=True,
            answer="No outstanding evidence gaps are currently recorded for this investigation.",
            confidence=0.7,
        )
    lines = [f"{g.description} (why it matters: {g.why_it_matters})" for g in state.evidence_gaps]
    answer = "The following evidence is still missing: " + "; ".join(lines) + "."
    return ResolvedAnswer(can_answer=True, answer=answer, confidence=0.88)


def _investigation_trace(state: InvestigationState, _q: str) -> ResolvedAnswer:
    if not state.investigation_trace:
        return ResolvedAnswer(can_answer=False, missing_reason="No investigation_trace recorded in InvestigationState.")
    steps = sorted(state.investigation_trace, key=lambda s: s.step_number)
    lines = [f"{s.step_number}. {s.description}" for s in steps]
    answer = "The investigation performed the following steps: " + " ".join(lines)
    return ResolvedAnswer(can_answer=True, answer=answer, confidence=0.9)


def _final_recommendation_explanation(state: InvestigationState, _q: str) -> ResolvedAnswer:
    if not state.final_report:
        return ResolvedAnswer(can_answer=False, missing_reason="No final_report in InvestigationState.")
    answer = (
        f"The available evidence supports the recommendation of "
        f"\"{state.final_report.recommendation.replace('_', ' ')}\" because {state.final_report.rationale}"
    )
    return ResolvedAnswer(
        can_answer=True,
        answer=answer,
        evidence=[_ev_out(e) for e in state.evidence],
        citations=[_cit_out(c) for c in state.citations],
        confidence=0.87,
        caveat="This reflects the evidence gathered so far. The final decision remains with the human investigator.",
    )


def _policy_question(state: InvestigationState, _q: str) -> ResolvedAnswer:
    if not state.citations:
        return ResolvedAnswer(can_answer=False, missing_reason="No citations in InvestigationState; RAG lookup needed.")
    lines = [f"{c.title} — {c.excerpt} (source: {c.source})" for c in state.citations]
    answer = "The following policy evidence supports this: " + " ".join(lines)
    return ResolvedAnswer(
        can_answer=True,
        answer=answer,
        citations=[_cit_out(c) for c in state.citations],
        confidence=0.86,
    )


def _provider_history(state: InvestigationState, _q: str) -> ResolvedAnswer:
    # The current InvestigationState only has a snapshot ("this month"),
    # not multi-month history, so this generally requires the Provider DB tool.
    history_evidence = [e for e in state.evidence if "history" in (e.summary or e.description).lower() or "12 month" in (e.summary or e.description).lower()]
    if history_evidence:
        lines = [f"{e.summary or e.description} ({e.source})" for e in history_evidence]
        return ResolvedAnswer(can_answer=True, answer=" ".join(lines), confidence=0.85)
    return ResolvedAnswer(
        can_answer=False,
        missing_reason="InvestigationState only has a current-month snapshot; multi-month history requires the Provider DB tool.",
    )


def _ml_explanation(state: InvestigationState, _q: str) -> ResolvedAnswer:
    if not state.shap_factors:
        return ResolvedAnswer(can_answer=False, missing_reason="No shap_factors in InvestigationState; ML tool needed.")
    lines = [f"{sf.feature} ({sf.direction}, contribution {sf.shap_value:+.2f}): {sf.description}" for sf in state.shap_factors]
    answer = (
        f"The model assigned a risk score of {state.risk_score:.2f}. "
        f"The largest contributing factors are: " + "; ".join(lines) + "."
    )
    return ResolvedAnswer(
        can_answer=True,
        answer=answer,
        confidence=0.87,
        caveat="A high risk score reflects statistical anomalies flagged by the model; it does not by itself confirm fraud.",
    )


def _scenario_question(_state: InvestigationState, _q: str) -> ResolvedAnswer:
    # Scenario/what-if questions always require the scenario tool — this is
    # a hypothetical simulation, never something answerable from stored state.
    return ResolvedAnswer(can_answer=False, missing_reason="Scenario questions always require the ML Scenario tool.")


_HANDLERS = {
    QuestionType.INVESTIGATION_SUMMARY: _investigation_summary,
    QuestionType.RISK_EXPLANATION: _risk_explanation,
    QuestionType.EVIDENCE_QUESTION: _evidence_question,
    QuestionType.COUNTER_EVIDENCE: _counter_evidence,
    QuestionType.EVIDENCE_GAP: _evidence_gap,
    QuestionType.INVESTIGATION_TRACE: _investigation_trace,
    QuestionType.FINAL_RECOMMENDATION_EXPLANATION: _final_recommendation_explanation,
    QuestionType.POLICY_QUESTION: _policy_question,
    QuestionType.PROVIDER_HISTORY: _provider_history,
    QuestionType.ML_EXPLANATION: _ml_explanation,
    QuestionType.SCENARIO_QUESTION: _scenario_question,
}


def _ev_out(e) -> EvidenceItemOut:
    return EvidenceItemOut(id=e.id, summary=e.summary or e.description, source=e.source)


def _cit_out(c) -> CitationItemOut:
    return CitationItemOut(id=c.id, title=c.title or c.source, source=c.source, excerpt=c.excerpt, url=c.url)
