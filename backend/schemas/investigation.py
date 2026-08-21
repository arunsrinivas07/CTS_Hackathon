from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from schemas.evidence import Evidence, EvidenceGap, EvidenceSufficiencyResult, Citation
from schemas.question import InvestigationQuestion, Observation, ToolCallRecord

CounterEvidence = Evidence


class InvestigationStatus(str, Enum):
    INITIALIZED = "INITIALIZED"
    IN_PROGRESS = "IN_PROGRESS"
    COUNTER_ANALYSIS = "COUNTER_ANALYSIS"
    CRITIC_REVIEW = "CRITIC_REVIEW"
    COMPLETED = "COMPLETED"
    REQUIRES_HUMAN_REVIEW = "REQUIRES_HUMAN_REVIEW"
    MAX_ITERATIONS_REACHED = "MAX_ITERATIONS_REACHED"
    FAILED = "FAILED"


class RiskFactor(BaseModel):
    name: str
    description: Optional[str] = None
    shap_value: Optional[float] = None
    magnitude: Optional[str] = None  # e.g. "HIGH" / "MEDIUM" / "LOW"


class DetectedPattern(BaseModel):
    name: str
    description: Optional[str] = None


class InvestigationObjective(BaseModel):
    objective_id: str
    description: str
    related_risk_factors: list[str] = Field(default_factory=list)
    resolved: bool = False


class CriticResult(BaseModel):
    status: str = "PASS"  # "PASS" | "FAIL"
    issues: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    revision_number: int = 0
    # --- Copilot Compatibility Fields ---
    reviewed: bool = True
    notes: Optional[str] = None
    concerns: list[str] = Field(default_factory=list)


class FinalReport(BaseModel):
    investigation_id: str = "UNKNOWN"
    claim_summary: str = ""
    risk_summary: str = ""
    risk_factors: list[RiskFactor] = Field(default_factory=list)
    detected_patterns: list[DetectedPattern] = Field(default_factory=list)
    investigation_objectives: list[InvestigationObjective] = Field(default_factory=list)
    questions_asked: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    evidence_collected: list[Evidence] = Field(default_factory=list)
    citations: list[dict] = Field(default_factory=list)
    counter_evidence: list[Evidence] = Field(default_factory=list)
    alternative_explanations: list[str] = Field(default_factory=list)
    evidence_gaps: list[EvidenceGap] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    critic_result: Optional[CriticResult] = None
    conclusion: str = ""
    generated_at: str = "1970-01-01T00:00:00Z"
    # --- Copilot Compatibility Fields ---
    summary: str = ""
    recommendation: str = ""
    rationale: str = ""


class SHAPFactor(BaseModel):
    feature: str
    shap_value: float
    direction: str  # "increases_risk" | "decreases_risk"
    description: str


class InvestigationTraceStep(BaseModel):
    step_number: int
    action: str
    description: str
    timestamp: Optional[str] = None


class InvestigationState(BaseModel):
    """
    The full memory of a single investigation. This object is the single
    source of truth passed through every step of the agent loop, persisted
    between steps, and exposed via the API to the frontend and the Copilot
    (Member 3). Nothing is ever removed from it -- only appended to or
    marked resolved -- so no previously collected evidence is ever lost.
    """

    investigation_id: str
    claim_id: str

    # --- inputs from the deterministic pipeline (read-only context) ---
    claim_data: dict[str, Any] = Field(default_factory=dict)
    provider_name: str = "UNKNOWN"
    procedure: str = "UNKNOWN"
    claim_amount: float = 0.0
    claim_date: Optional[str] = None
    
    risk_score: float = 0.0
    risk_level: str = "UNKNOWN"
    risk_factors: list[RiskFactor] = Field(default_factory=list)
    shap_factors: list[SHAPFactor] = Field(default_factory=list)
    detected_patterns: list[DetectedPattern] = Field(default_factory=list)

    # --- agent-derived planning state ---
    investigation_objectives: list[InvestigationObjective] = Field(default_factory=list)
    current_hypothesis: Optional[str] = None
    current_reasoning: Optional[str] = None

    # --- loop history (append-only) ---
    questions: list[InvestigationQuestion] = Field(default_factory=list)
    question_history: list[str] = Field(default_factory=list)  # normalized text, for dedup
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    tool_results: list[dict] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list)

    # --- evidence store (append-only) ---
    evidence: list[Evidence] = Field(default_factory=list)
    evidence_scores: dict[str, float] = Field(default_factory=dict)  # evidence_id -> score
    citations: list[Any] = Field(default_factory=list)
    counter_evidence: list[Evidence] = Field(default_factory=list)
    evidence_gaps: list[EvidenceGap] = Field(default_factory=list)
    alternative_explanations: list[str] = Field(default_factory=list)
    investigation_trace: list[InvestigationTraceStep] = Field(default_factory=list)

    # --- evaluation history ---
    sufficiency_history: list[EvidenceSufficiencyResult] = Field(default_factory=list)

    # --- control state ---
    iteration_count: int = 0
    max_iterations: int = 5
    status: InvestigationStatus = InvestigationStatus.INITIALIZED

    # --- critic / revision ---
    critic_result: Optional[CriticResult] = None
    critic_history: list[CriticResult] = Field(default_factory=list)
    revision_count: int = 0
    max_revisions: int = 2

    # --- final output ---
    final_report: Optional[FinalReport] = None

    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()

    model_config = ConfigDict(use_enum_values=False)
