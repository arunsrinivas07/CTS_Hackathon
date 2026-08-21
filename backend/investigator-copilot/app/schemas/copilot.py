"""
Request/response schemas for the Investigator Copilot API.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field
from datetime import datetime


class QuestionType(str, Enum):
    INVESTIGATION_SUMMARY = "investigation_summary"
    RISK_EXPLANATION = "risk_explanation"
    EVIDENCE_QUESTION = "evidence_question"
    COUNTER_EVIDENCE = "counter_evidence"
    POLICY_QUESTION = "policy_question"
    PROVIDER_HISTORY = "provider_history"
    ML_EXPLANATION = "ml_explanation"
    SCENARIO_QUESTION = "scenario_question"
    EVIDENCE_GAP = "evidence_gap"
    INVESTIGATION_TRACE = "investigation_trace"
    FINAL_RECOMMENDATION_EXPLANATION = "final_recommendation_explanation"
    UNKNOWN = "unknown"

class ConversationMessage(BaseModel):
    message_id: str
    role: str
    content: str
    timestamp: datetime
    metadata: Optional[dict] = None

class Conversation(BaseModel):
    conversation_id: str
    investigation_id: str
    created_at: datetime
    status: str = "active"
    messages: List[ConversationMessage] = Field(default_factory=list)


class CopilotQueryRequest(BaseModel):
    investigation_id: str = Field(..., description="ID of the investigation to query")
    question: str = Field(..., description="The investigator's natural language question")
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID to continue an existing session")


class ToolUsageRecord(BaseModel):
    tool: str
    purpose: str


class EvidenceItemOut(BaseModel):
    id: str
    summary: str
    source: str


class CitationItemOut(BaseModel):
    id: str
    title: str
    source: str
    excerpt: str
    url: Optional[str] = None


class CopilotQueryResponse(BaseModel):
    investigation_id: str
    conversation_id: str
    question_type: str
    answer: str
    evidence: List[EvidenceItemOut] = Field(default_factory=list)
    citations: List[CitationItemOut] = Field(default_factory=list)
    tools_used: List[ToolUsageRecord] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    explanation: Optional[str] = None
    caveat: Optional[str] = None
    runtime_trace: Optional[dict] = None


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
