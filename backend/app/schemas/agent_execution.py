from datetime import datetime
from typing import Optional
from .common import SchemaBase

class AgentExecutionCreate(SchemaBase):
    investigation_run_id: int
    agent_name: str
    task: str
    input_data: Optional[dict] = None

class AgentExecutionResponse(AgentExecutionCreate):
    id: int
    status: str
    output_data: Optional[dict] = None
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
