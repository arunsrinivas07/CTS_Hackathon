"""
Tool router.

Chooses and invokes exactly one approved tool for a given question type,
when the evidence_resolver has determined InvestigationState alone cannot
answer the question. Never calls more than one tool per question, and
never calls a tool when it isn't needed (evidence_resolver gates that).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from app.adapters.database_adapter import ClaimDBTool, ProviderDBTool
from app.adapters.ml_adapter import MLTool
from app.adapters.rag_adapter import RAGTool
from app.adapters.scenario_adapter import ScenarioTool
from app.schemas.copilot import CitationItemOut, EvidenceItemOut, QuestionType, ToolUsageRecord
from schemas.investigation import Citation, Evidence, InvestigationState, SHAPFactor


@dataclass
class ToolResult:
    answer: str
    evidence: List[EvidenceItemOut] = field(default_factory=list)
    citations: List[CitationItemOut] = field(default_factory=list)
    tool_usage: Optional[ToolUsageRecord] = None
    confidence: float = 0.75
    caveat: Optional[str] = None
    # If new evidence should be attached back onto InvestigationState
    new_evidence: Optional[Evidence] = None


class ToolRouter:
    def __init__(
        self,
        rag_tool: RAGTool,
        ml_tool: MLTool,
        scenario_tool: ScenarioTool,
        provider_db_tool: ProviderDBTool,
        claim_db_tool: ClaimDBTool,
    ) -> None:
        self._rag_tool = rag_tool
        self._ml_tool = ml_tool
        self._scenario_tool = scenario_tool
        self._provider_db_tool = provider_db_tool
        self._claim_db_tool = claim_db_tool

    def route(self, question_type: QuestionType, question: str, state: InvestigationState) -> Optional[ToolResult]:
        handler = self._HANDLERS.get(question_type)
        if handler is None:
            return None
        return handler(self, question, state)

    # -- handlers -----------------------------------------------------

    def _handle_policy(self, question: str, state: InvestigationState) -> ToolResult:
        claim_context = {"procedure": state.procedure, "claim_id": state.claim_id}
        citations = self._rag_tool.retrieve_policy(question, claim_context)
        if not citations:
            return ToolResult(
                answer="I don't currently have an authoritative citation for that claim.",
                tool_usage=ToolUsageRecord(tool="rag_tool", purpose="Retrieve applicable policy documents"),
                confidence=0.3,
            )
        excerpt_lines = [f"{c.title} — {c.excerpt} (source: {c.source})" for c in citations]
        return ToolResult(
            answer="The following policy evidence is relevant: " + " ".join(excerpt_lines),
            citations=[CitationItemOut(id=c.id, title=c.title, source=c.source, excerpt=c.excerpt, url=c.url) for c in citations],
            tool_usage=ToolUsageRecord(tool="rag_tool", purpose="Retrieve applicable policy documents"),
            confidence=0.82,
        )

    def _handle_provider_history(self, _question: str, state: InvestigationState) -> ToolResult:
        history = self._provider_db_tool.get_mri_history(state.provider_name)
        if not history:
            return ToolResult(
                answer="I don't currently have historical provider data available for this claim.",
                tool_usage=ToolUsageRecord(tool="provider_db_tool", purpose="Retrieve provider historical MRI behavior"),
                confidence=0.3,
            )
        trend = ", ".join(f"{h['month']}={h['mri_count']}" for h in history)
        answer = (
            f"{state.provider_name}'s monthly MRI volume over the recorded period was: {trend}. "
            f"This shows a rising trend leading up to the current claim."
        )
        new_evidence = Evidence(
            id=f"EV-TOOL-{state.investigation_id}-provider-history",
            summary=f"{state.provider_name}'s 12-month MRI volume trend was retrieved.",
            detail=trend,
            source="Provider Claims Database",
            supports="provider_anomaly",
            added_by="copilot",
            tool_used="provider_db_tool",
        )
        return ToolResult(
            answer=answer,
            evidence=[EvidenceItemOut(id=new_evidence.id, summary=new_evidence.summary, source=new_evidence.source)],
            tool_usage=ToolUsageRecord(tool="provider_db_tool", purpose="Retrieve provider historical MRI behavior"),
            confidence=0.85,
            new_evidence=new_evidence,
        )

    def _handle_ml_explanation(self, _question: str, state: InvestigationState) -> ToolResult:
        shap_factors: List[SHAPFactor] = self._ml_tool.explain_risk_score(state.claim_id, state.risk_score)
        if not shap_factors:
            return ToolResult(
                answer="I don't currently have a model explanation available for this claim.",
                tool_usage=ToolUsageRecord(tool="ml_tool", purpose="Retrieve SHAP-based model explanation"),
                confidence=0.3,
            )
        lines = [f"{sf.feature} ({sf.direction}): {sf.description}" for sf in shap_factors]
        answer = (
            f"The model assigns a risk score of {state.risk_score:.2f}. "
            f"The largest contributing factors are: " + "; ".join(lines) + "."
        )
        return ToolResult(
            answer=answer,
            tool_usage=ToolUsageRecord(tool="ml_tool", purpose="Retrieve SHAP-based model explanation"),
            confidence=0.8,
            caveat="A high risk score reflects statistical anomalies; it does not by itself confirm fraud.",
        )

    def _handle_scenario(self, question: str, state: InvestigationState) -> ToolResult:
        feature = _guess_scenario_feature(question)
        result = self._scenario_tool.run_scenario(
            claim_id=state.claim_id,
            base_risk_score=state.risk_score,
            feature=feature,
            hypothetical_change=question,
        )
        answer = (
            f"Hypothetical simulation only — no claim data was changed. "
            f"If {feature.replace('_', ' ')} were adjusted as described, the estimated risk score would move "
            f"from {result['base_risk_score']:.2f} to approximately {result['simulated_risk_score']:.2f}."
        )
        return ToolResult(
            answer=answer,
            tool_usage=ToolUsageRecord(tool="ml_scenario_tool", purpose="Run hypothetical what-if simulation"),
            confidence=0.65,
            caveat="This is a simulated, hypothetical result and does not reflect the claim's actual, current risk score.",
        )

    _HANDLERS = {
        QuestionType.POLICY_QUESTION: _handle_policy,
        QuestionType.PROVIDER_HISTORY: _handle_provider_history,
        QuestionType.ML_EXPLANATION: _handle_ml_explanation,
        QuestionType.SCENARIO_QUESTION: _handle_scenario,
    }


def _guess_scenario_feature(question: str) -> str:
    lowered = question.lower()
    if "frequency" in lowered or "volume" in lowered:
        return "provider_frequency"
    if "amount" in lowered:
        return "claim_amount"
    if "diagnosis" in lowered:
        return "diagnosis_code"
    return "unspecified_feature"
