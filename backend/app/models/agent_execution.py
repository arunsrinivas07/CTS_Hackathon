from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id"), nullable=True)
    agent_name = Column(String(100), nullable=False)
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    status = Column(String(30), default="pending", nullable=False)
    duration_ms = Column(Float, nullable=True)
    error_message = Column(String(2000), nullable=True)
    executed_at = Column(DateTime(timezone=True), server_default=func.now())
