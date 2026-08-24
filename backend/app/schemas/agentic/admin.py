from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime, timezone
import uuid

class QueueItem(BaseModel):
    claim_id: str
    priority_score: float
    queued_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    # Optional metadata to pass to investigation start if needed
    claim_data: dict[str, Any] = Field(default_factory=dict)
    risk_score: float = 0.0
    risk_level: str = "UNKNOWN"
    shap_contributors: list[dict] = Field(default_factory=list)
    detected_patterns: list[dict] = Field(default_factory=list)

class Investigator(BaseModel):
    investigator_id: str
    name: str
    active: bool = True
    workload: int = 0
    last_assigned_at: str = "1970-01-01T00:00:00Z"

class Assignment(BaseModel):
    assignment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    claim_id: str
    investigator_id: str
    investigation_id: str
    assigned_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "assigned"  # "assigned", "completed", "reassigned"
