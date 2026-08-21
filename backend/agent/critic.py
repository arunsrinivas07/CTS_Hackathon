"""
Critic: reviews a drafted report (or draft conclusion) against the actual
evidence in state before it is allowed to become the final report.

Checks (spec section 21): grounding, evidence support, citation
correctness, contradictions, unsupported conclusions, ML interpretation,
missing evidence, risk-vs-fraud distinction, alternative explanations
considered.
"""
from __future__ import annotations

import json
import logging

from llm.client import LLMClient, LLMError
from schemas.investigation import CriticResult, InvestigationState

logger = logging.getLogger("agent.critic")

SYSTEM_PROMPT = """You are the critic for a healthcare claims fraud
investigation report. You did not write the draft; your job is to find
problems with it, not defend it.

Check specifically for:
1. Grounding: every factual claim traces to evidence in the state
2. Evidence support: conclusions are proportionate to evidence strength
3. Citation correctness: cited sources actually say what's claimed
4. Contradictions: conflicting evidence is acknowledged, not hidden
5. Unsupported conclusions: no claim goes beyond what evidence establishes
6. ML interpretation: risk score / SHAP are described as risk indicators,
   NEVER as proof of fraud or causality
7. Missing evidence: gaps are disclosed, not glossed over
8. Risk vs. confirmed fraud: language never asserts fraud was committed;
   only that risk/evidence supports further investigation/escalation
9. Alternative explanations: counter-analysis findings are reflected, not ignored

CRITICAL RULE: if the draft states or implies that fraud was committed,
proven, or confirmed (rather than "risk", "anomalous", "warrants
investigation", "consistent with"), this is an automatic FAIL.

Respond with ONLY a JSON object, no prose, no markdown fences:
{
  "status": "PASS" | "FAIL",
  "issues": ["specific issue 1", "specific issue 2"],
  "confidence": 0.0-1.0
}
"""


def _build_user_prompt(state: InvestigationState, draft_conclusion: str) -> str:
    payload = {
        "draft_conclusion": draft_conclusion,
        "evidence": [e.model_dump() for e in state.evidence],
        "counter_evidence": [e.model_dump() for e in state.counter_evidence],
        "alternative_explanations": state.alternative_explanations,
        "evidence_gaps": [g.model_dump() for g in state.evidence_gaps],
        "citations": state.citations,
        "risk_score": state.risk_score,
        "risk_level": state.risk_level,
    }
    return "Draft and supporting state:\n" + json.dumps(payload, indent=2, default=str)


def run_critic(
    state: InvestigationState, draft_conclusion: str, revision_number: int, llm: LLMClient | None = None
) -> CriticResult:
    llm = llm or LLMClient()
    try:
        raw = llm.complete_json(SYSTEM_PROMPT, _build_user_prompt(state, draft_conclusion))
    except LLMError as exc:
        logger.error("Critic LLM call failed: %s", exc)
        # Fail safe: an unreviewable draft cannot pass.
        result = CriticResult(
            status="FAIL",
            issues=[f"Critic could not run due to an internal error: {exc}"],
            confidence=0.0,
            revision_number=revision_number,
        )
        state.critic_history.append(result)
        state.touch()
        return result

    status = raw.get("status", "FAIL").upper()
    if status not in ("PASS", "FAIL"):
        status = "FAIL"

    result = CriticResult(
        status=status,
        issues=raw.get("issues", []) or [],
        confidence=float(raw.get("confidence", 0.0) or 0.0),
        revision_number=revision_number,
    )
    state.critic_history.append(result)
    state.critic_result = result
    state.touch()
    return result
