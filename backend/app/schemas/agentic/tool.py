"""
These are the INTERFACE CONTRACTS for tools owned by Member 2.

Member 1 (this codebase) never implements RAG/ML/DB internals. It only
depends on these shapes. When Member 2's real tools are ready, we swap the
mock implementations in tools/*.py for real HTTP/SDK calls -- the
orchestrator, question generator, evidence evaluator etc. never change.
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ToolResultStatus:
    SUCCESS = "SUCCESS"
    NO_EVIDENCE_FOUND = "NO_EVIDENCE_FOUND"
    TOOL_FAILURE = "TOOL_FAILURE"
    INVALID_TOOL = "INVALID_TOOL"

class ToolErrorResponse(BaseModel):
    status: str = "error"
    error_code: str
    message: str
    details: Optional[dict[str, Any]] = None


class CMSEvidenceMetadata(BaseModel):
    official_cms_url: str
    document_id: str
    document_title: str
    section: str
    page: Optional[int] = None
    effective_date: Optional[str] = None
    jurisdiction: Optional[str] = None
    verification_status: str


class LCDEvidenceMetadata(BaseModel):
    lcd_id: str
    mac_contractor: str
    jurisdiction: str
    effective_date: str
    version_status: str


class ContradictionDetail(BaseModel):
    evidence_a: str
    evidence_b: str
    reason: str
    resolution: Optional[str] = None
    preferred_evidence: Optional[str] = None


class ClaimContext(BaseModel):
    claim_id: Optional[str] = None
    procedure: Optional[str] = None
    diagnosis: Optional[str] = None
    provider_id: Optional[str] = None
    claim_amount: Optional[float] = None


class EvidenceScores(BaseModel):
    relevance: float = Field(..., ge=0.0, le=1.0)
    authority: float = Field(..., ge=0.0, le=1.0)
    specificity: float = Field(..., ge=0.0, le=1.0)
    validity: float = Field(..., ge=0.0, le=1.0)
    completeness: float = Field(..., ge=0.0, le=1.0)
    overall_score: float = Field(..., ge=0.0, le=1.0)


class EvidenceItem(BaseModel):
    source: str
    document: str
    section: Optional[str] = "N/A"
    page: Optional[int] = 1
    text: str
    retrieval_score: float = 0.0
    evidence_score: float = 0.0
    scores: Optional[EvidenceScores] = None
    url: Optional[str] = None
    cms_metadata: Optional[CMSEvidenceMetadata] = None
    lcd_metadata: Optional[LCDEvidenceMetadata] = None


class RagToolOutput(BaseModel):
    status: str
    answer_context: Optional[str] = None
    evidence: list[EvidenceItem] = Field(default_factory=list)
    citations: list[dict] = Field(default_factory=list)
    confidence: float = 0.0
    sufficient: bool = False
    has_contradiction: bool = False
    contradictions: list[ContradictionDetail] = Field(default_factory=list)
    reason: Optional[str] = None
    error: Optional[str] = None


class MLRiskRequest(BaseModel):
    claim_id: str


class ShapFeature(BaseModel):
    feature: str
    impact: float
    direction: str = Field(description="'increases_risk' or 'decreases_risk'")
    description: Optional[str] = None


class MLRiskResponse(BaseModel):
    status: str = "success"
    tool: str = "ml_risk"
    claim_id: str
    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_level: str = Field(description="'LOW', 'MEDIUM', or 'HIGH'")
    shap_features: list[ShapFeature] = Field(default_factory=list)
    model_version: Optional[str] = "xgboost_fraud_v1.0"


class MLScenarioRequest(BaseModel):
    claim_id: str
    changes: dict[str, Any]


class ChangedFeatureDetail(BaseModel):
    original: Any
    scenario: Any


class MLScenarioResponse(BaseModel):
    status: str = "success"
    tool: str = "ml_scenario"
    claim_id: str
    original_score: float = Field(..., ge=0.0, le=1.0)
    scenario_score: float = Field(..., ge=0.0, le=1.0)
    difference: float
    changed_features: dict[str, ChangedFeatureDetail]
    is_causal: bool = False
    explanation: Optional[str] = (
        "Scenario simulation demonstrates model sensitivity. SHAP and scenario tests "
        "are statistical explanations and do not prove causality or legal fraud."
    )


class ProviderStatisticsResponse(BaseModel):
    status: str = "success"
    tool: str = "provider_statistics"
    provider_id: str
    procedure: Optional[str] = None
    provider_count: int
    peer_average: float
    peer_median: float
    peer_95_percentile: float
    specialty: str
    total_claims_submitted: Optional[int] = None
    total_billed_amount: Optional[float] = None
    denial_rate: Optional[float] = None


class ProviderHistoryResponse(BaseModel):
    status: str = "success"
    tool: str = "provider_history"
    provider_id: str
    history: list[dict[str, Any]] = Field(default_factory=list)


class ProviderPeerComparisonResponse(BaseModel):
    status: str = "success"
    tool: str = "provider_peer_comparison"
    provider_id: str
    procedure: str
    specialty: str
    metrics: dict[str, Any]


class ClaimHistoryResponse(BaseModel):
    status: str = "success"
    tool: str = "claim_history"
    claim_id: str
    patient_id: Optional[str] = None
    provider_id: Optional[str] = None
    claims: list[dict[str, Any]] = Field(default_factory=list)


class RelatedClaimsResponse(BaseModel):
    status: str = "success"
    tool: str = "claim_related_claims"
    claim_id: str
    patient_id: Optional[str] = None
    related_claims: list[dict[str, Any]] = Field(default_factory=list)
    evidence: Optional[list[dict[str, Any]]] = Field(default_factory=list)
    reason: Optional[str] = None

class RAGSearchRequest(BaseModel):
    question: str
    claim_context: Optional[ClaimContext] = None
    top_k: Optional[int] = None
    metadata_filters: Optional[dict[str, Any]] = None

class RAGSearchResponse(BaseModel):
    status: str = "success"
    tool: str = "rag_search"
    question: str
    generated_queries: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    confidence: float = 0.0
    sufficient: bool = False
    has_contradiction: bool = False
    contradictions: list[ContradictionDetail] = Field(default_factory=list)
    reason: Optional[str] = None
    synthesis: Optional[str] = None

# Generic envelope every tool ultimately returns to the executor, regardless
# of which of the above shapes it started as. Keeping one generic envelope
# keeps tool_executor.py simple and future-proof against new tool types.
class ToolOutput(BaseModel):
    status: str
    data: dict[str, Any] = Field(default_factory=dict)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    citations: list[dict] = Field(default_factory=list)
    confidence: Optional[float] = None
    error: Optional[str] = None
