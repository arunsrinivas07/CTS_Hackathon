"""
InvestigationState schema.

This is the shared state object produced by the (future) Investigation
Orchestrator built by another team member. The Copilot is a CONSUMER of
this state, never a producer of the primary investigation.

INTEGRATION POINT:
When the real Investigation Orchestrator is available, this model should be
aligned with (or imported from) that team's actual InvestigationState
definition. For this MVP we define a compatible shape here so the Copilot
can be built and tested independently.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class RiskFactor(BaseModel):
    """A single contributing factor to the risk score (rule/pattern based)."""

    name: str
    description: str
    weight: Optional[float] = None


class SHAPFactor(BaseModel):
    """A single SHAP-derived feature contribution to the ML risk score."""

    feature: str
    shap_value: float
    direction: str  # "increases_risk" | "decreases_risk"
    description: str


class Evidence(BaseModel):
    """A single piece of evidence gathered during the investigation."""

    id: str
    summary: str
    detail: str
    source: str
    supports: str  # what claim/finding this evidence supports
    timestamp: Optional[str] = None
    # provenance for evidence added later by the Copilot via a tool call
    added_by: str = "investigation_agent"  # "investigation_agent" | "copilot"
    tool_used: Optional[str] = None


class Citation(BaseModel):
    """A citation to an authoritative source (policy, guideline, etc.)."""

    id: str
    title: str
    source: str
    excerpt: str
    url: Optional[str] = None


class CounterEvidence(BaseModel):
    """Evidence that weakens or contradicts a finding."""

    id: str
    summary: str
    detail: str
    source: str


class EvidenceGap(BaseModel):
    """Information that is still missing from the investigation."""

    id: str
    description: str
    why_it_matters: str


class InvestigationTraceStep(BaseModel):
    """A single step actually performed by the investigation agent."""

    step_number: int
    action: str
    description: str
    timestamp: Optional[str] = None


class CriticResult(BaseModel):
    """Result of the (future) critic/review stage of the orchestrator."""

    reviewed: bool
    notes: Optional[str] = None
    concerns: List[str] = Field(default_factory=list)


class FinalReport(BaseModel):
    """The orchestrator's draft final report / recommendation."""

    summary: str
    recommendation: str  # e.g. "escalate_for_review" (never "reject"/"approve")
    rationale: str


class InvestigationState(BaseModel):
    """
    Full investigation state for a single claim investigation.

    This mirrors the fields described in the project spec:
    claim information, risk score, risk factors, questions, tool calls,
    observations, evidence, citations, counter-evidence, evidence gaps,
    critic result, final report, investigation trace.
    """

    investigation_id: str
    claim_id: str

    # --- Claim information ---
    provider_name: str
    procedure: str
    claim_amount: float
    claim_date: Optional[str] = None

    # --- Risk scoring ---
    risk_score: float
    risk_factors: List[RiskFactor] = Field(default_factory=list)
    shap_factors: List[SHAPFactor] = Field(default_factory=list)
    detected_patterns: List[str] = Field(default_factory=list)

    # --- Evidence & citations ---
    evidence: List[Evidence] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    counter_evidence: List[CounterEvidence] = Field(default_factory=list)
    evidence_gaps: List[EvidenceGap] = Field(default_factory=list)

    # --- Process record ---
    investigation_trace: List[InvestigationTraceStep] = Field(default_factory=list)
    critic_result: Optional[CriticResult] = None
    final_report: Optional[FinalReport] = None

    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def touch(self) -> None:
        self.updated_at = datetime.utcnow().isoformat()
