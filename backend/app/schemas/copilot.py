from typing import Optional
from .common import SchemaBase

class CopilotRequest(SchemaBase):
    investigation_id: Optional[int] = None
    prompt: str
    context: Optional[dict] = None

class CopilotResponse(SchemaBase):
    answer: str
    citations: list[dict] = []
    suggested_actions: list[str] = []
    confidence: Optional[float] = None
