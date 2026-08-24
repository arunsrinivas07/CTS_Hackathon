from datetime import datetime
from typing import Optional, Literal
from .common import SchemaBase

class SupervisorReviewCreate(SchemaBase):
    investigation_id: int
    reviewer_id: int
    decision: Literal["approved","rejected","needs_more_information"]
    comments: Optional[str] = None

class SupervisorReviewResponse(SupervisorReviewCreate):
    id: int
    created_at: datetime
