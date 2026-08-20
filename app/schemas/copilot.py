"""
Request/response schemas for the Investigator Copilot API.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


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


class CopilotQueryRequest(BaseModel):
    investigation_id: str = Field(..., description="ID of the investigation to query")
    question: str = Field(..., description="The investigator's natural language question")


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
    question_type: QuestionType
    answer: str
    evidence: List[EvidenceItemOut] = Field(default_factory=list)
    citations: List[CitationItemOut] = Field(default_factory=list)
    tools_used: List[ToolUsageRecord] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    caveat: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
