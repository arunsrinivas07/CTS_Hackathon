from datetime import datetime
from typing import Optional
from .common import SchemaBase

class WorkflowTaskCreate(SchemaBase):
    investigation_id: int
    task_type: str
    title: str
    description: Optional[str] = None
    assigned_to: Optional[int] = None
    due_at: Optional[datetime] = None

class WorkflowTaskUpdate(SchemaBase):
    title: Optional[str] = None
    description: Optional[str] = None
    assigned_to: Optional[int] = None
    due_at: Optional[datetime] = None
    status: Optional[str] = None

class WorkflowTaskResponse(WorkflowTaskCreate):
    id: int
    status: str = "pending"
    created_at: datetime
