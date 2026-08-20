from datetime import datetime
from typing import Optional
from .common import SchemaBase

class ChatMessageCreate(SchemaBase):
    investigation_id: Optional[int] = None
    session_id: Optional[str] = None
    role: str
    content: str
    metadata: Optional[dict] = None

class ChatMessageResponse(ChatMessageCreate):
    id: int
    created_at: datetime

class ChatHistoryResponse(SchemaBase):
    messages: list[ChatMessageResponse]
