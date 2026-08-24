"""
Simple, maintainable keyword-based question classifier.

For a two-day MVP a rule-based classifier is preferred over a full ML/LLM
classifier: it's deterministic, easy to test, easy to extend, and easy for
teammates to reason about. It can be swapped for an LLM-based classifier
later without changing anything downstream, since it just returns a
QuestionType.
"""

from __future__ import annotations

from app.copilot.schemas.copilot import QuestionType

# Ordered rules: first matching category wins. Order matters — more specific
# categories are checked before more general ones (e.g. "counter evidence"
# before plain "evidence").
_RULES: list[tuple[QuestionType, list[str]]] = [
    (QuestionType.COUNTER_EVIDENCE, [
        "counter-evidence", "counter evidence", "contradict", "reduces the concern",
        "against this finding", "weakens",
    ]),
    (QuestionType.EVIDENCE_GAP, [
        "still missing", "what's missing", "what is missing", "evidence gap",
        "information do we need", "what do we need",
    ]),
    (QuestionType.INVESTIGATION_TRACE, [
        "what did the agent", "what steps", "investigation trace", "what was investigated",
        "what did you investigate",
    ]),
    (QuestionType.INVESTIGATION_SUMMARY, [
        "summarize", "summary", "explain the complete investigation", "give me an overview",
    ]),
    (QuestionType.FINAL_RECOMMENDATION_EXPLANATION, [
        "final recommendation", "recommend escalation", "why does the system recommend",
        "final decision", "recommendation explanation",
    ]),
    (QuestionType.SCENARIO_QUESTION, [
        "what happens if", "what if", "hypothetical", "normalized", "were changed", "simulate",
    ]),
    (QuestionType.ML_EXPLANATION, [
        "ml model", "the model", "shap", "model score", "why did the model", "model give this",
    ]),
    (QuestionType.PROVIDER_HISTORY, [
        "provider's historical", "provider history", "historical pattern", "historical mri",
        "provider's pattern", "past behavior",
    ]),
    (QuestionType.POLICY_QUESTION, [
        "policy", "guideline", "medical necessity", "what policy",
    ]),
    (QuestionType.RISK_EXPLANATION, [
        "high risk", "risk indicators", "why is this claim", "explain the risk", "risk score",
        "strongest risk",
    ]),
    (QuestionType.EVIDENCE_QUESTION, [
        "evidence supports", "what evidence", "supporting evidence", "evidence for",
    ]),
]


def classify_question(question: str) -> QuestionType:
    lowered = question.lower()
    for question_type, keywords in _RULES:
        if any(keyword in lowered for keyword in keywords):
            return question_type
    return QuestionType.UNKNOWN
