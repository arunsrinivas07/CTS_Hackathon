from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class WorkflowTask(Base):
    __tablename__ = "workflow_tasks"

    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id"), nullable=False)
    task_type = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(String(2000), nullable=True)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(30), default="pending", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
