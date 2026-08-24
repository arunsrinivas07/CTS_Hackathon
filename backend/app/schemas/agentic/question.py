from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Priority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class InvestigationQuestion(BaseModel):
    question_id: str
    question: str
    reason: str
    required_evidence: str
    preferred_tool: str
    priority: Priority
    iteration: int
    answered: bool = False
    answer_summary: Optional[str] = None
    is_counter_question: bool = False


class ToolCallRecord(BaseModel):
    tool_call_id: str
    tool: str
    question_id: Optional[str] = None
    question: Optional[str] = None
    input: dict = Field(default_factory=dict)
    result: Optional[dict] = None
    status: str  # "SUCCESS" | "NO_EVIDENCE_FOUND" | "TOOL_FAILURE" | "INVALID_TOOL"
    error: Optional[str] = None
    timestamp: str
    iteration: int


class Observation(BaseModel):
    observation_id: str
    tool_call_id: str
    question_id: Optional[str] = None
    text: str
    iteration: int
