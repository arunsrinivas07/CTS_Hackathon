from datetime import datetime
from typing import Optional
from .common import SchemaBase

class NotificationCreate(SchemaBase):
    user_id: int
    title: str
    message: str
    notification_type: str = "general"

class NotificationResponse(NotificationCreate):
    id: int
    is_read: bool = False
    created_at: datetime
