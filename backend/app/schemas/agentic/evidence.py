"""
Evidence-related schemas.

Evidence is the atomic unit of "things we've learned" during an investigation.
Every tool result that contributes to the case must eventually be distilled
into one or more Evidence objects so that:
  - the final report can cite concrete, structured facts
  - Member 3 (Copilot) can answer investigator questions against real evidence
  - the critic can check that conclusions are actually grounded in evidence
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    PROVIDER_STATISTIC = "provider_statistic"
    PROVIDER_HISTORY = "provider_history"
    PEER_COMPARISON = "peer_comparison"
    CLAIM_HISTORY = "claim_history"
    POLICY = "policy"
    CLINICAL = "clinical"
    ML_SCORE = "ml_score"
    ML_SCENARIO = "ml_scenario"
    PATTERN = "pattern"
    OTHER = "other"


class Citation(BaseModel):
    """A pointer back to the source document/record that backs a claim."""
    citation_id: str
    source: str
    source_type: str  # e.g. "policy_document", "database", "model_output"
    reference: Optional[str] = None  # e.g. section/page/record id
    excerpt: Optional[str] = None
    # --- Copilot Compatibility Fields ---
    title: Optional[str] = None
    url: Optional[str] = None

    @property
    def id(self) -> str:
        return self.citation_id


class Evidence(BaseModel):
    evidence_id: str
    type: EvidenceType
    description: str
    source: str
    source_type: str
    supporting_data: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0)
    relevance: float = Field(default=1.0, ge=0.0, le=1.0)
    citation: Optional[Citation] = None
    related_question: Optional[str] = None
    tool_used: Optional[str] = None
    is_counter_evidence: bool = False
    created_at_iteration: int = 0
    # --- Copilot Compatibility Fields ---
    summary: Optional[str] = None
    detail: Optional[str] = None
    supports: Optional[str] = None
    timestamp: Optional[str] = None
    added_by: str = "investigation_agent"

    @property
    def id(self) -> str:
        return self.evidence_id


class EvidenceGap(BaseModel):
    """A specific piece of missing evidence identified during evaluation."""
    description: str
    related_risk_factor: Optional[str] = None
    suggested_tool: Optional[str] = None
    resolved: bool = False
    # --- Copilot Compatibility Fields ---
    gap_id: Optional[str] = None
    why_it_matters: Optional[str] = None

    @property
    def id(self) -> str:
        return self.gap_id or "gap_unknown"


class EvidenceSufficiencyResult(BaseModel):
    sufficient: bool
    reason: str
    missing_evidence: list[str] = Field(default_factory=list)
    next_action: str  # "generate_question" | "counter_analysis" | "escalate"
    criteria_met: dict[str, bool] = Field(default_factory=dict)
