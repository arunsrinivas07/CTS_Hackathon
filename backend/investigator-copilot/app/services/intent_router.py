from typing import Optional
from app.schemas.copilot import QuestionType
from llm.factory import get_llm_provider
from llm.errors import LLMProviderError, StructuredOutputError
from pydantic import BaseModel
import json

class IntentClassification(BaseModel):
    intent: str
    confidence: float

def classify_intent_semantic(question: str, history_context: str = "", investigation_context: str = "") -> str:
    provider = get_llm_provider()
    system_prompt = """You are a semantic intent classifier for a healthcare fraud investigator copilot.
Your job is to classify the user's question into one of the following intents:
- RISK_ASSESSMENT
- EVIDENCE_QUERY
- EVIDENCE_GAP
- CLAIM_DETAILS
- COMPARISON
- INVESTIGATION_STATUS
- EXPLANATION
- RECOMMENDATION
- FOLLOW_UP
- FOCUS_CHANGE
- UNKNOWN

Respond with exactly one of these intents and a confidence score between 0.0 and 1.0."""

    user_prompt = f"""
History Context: {history_context}
Investigation Context: {investigation_context}
Question: {question}
"""
    try:
        res = provider.structured_generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=IntentClassification,
            max_tokens=50
        )
        return res.intent
    except (LLMProviderError, StructuredOutputError):
        # Fallback to deterministic
        return classify_intent_deterministic(question)

def classify_intent_deterministic(question: str) -> str:
    lowered = question.lower()
    
    rules = [
        ("COMPARISON", ["compare", "which claim", "difference between", "more suspicious", "common risk factors"]),
        ("FOLLOW_UP", ["why?", "why", "what evidence supports that?", "what caused that?", "is that enough"]),
        ("FOCUS_CHANGE", ["focus on", "ignore the", "instead focus on"]),
        ("EVIDENCE_GAP", ["missing", "evidence gap", "what do we need"]),
        ("EVIDENCE_QUERY", ["evidence supports", "what evidence", "show evidence"]),
        ("RECOMMENDATION", ["next action", "what should i do", "investigate next", "escalate"]),
        ("RISK_ASSESSMENT", ["risk level", "how risky", "risk score"]),
        ("EXPLANATION", ["explain", "why is this claim", "why was this flagged", "what made this claim"]),
        ("CLAIM_DETAILS", ["details", "patient", "provider", "amount", "billing"]),
        ("INVESTIGATION_STATUS", ["status", "where are we"]),
    ]
    
    for intent, keywords in rules:
        if any(kw in lowered for kw in keywords):
            return intent
            
    return "UNKNOWN"
