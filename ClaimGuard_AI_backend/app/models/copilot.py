from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class CopilotAction(Base):
    __tablename__ = "copilot_actions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    investigation_id = Column(Integer, ForeignKey("investigations.id"), nullable=True)
    action_type = Column(String(100), nullable=False)
    prompt = Column(String(3000), nullable=True)
    response = Column(String(5000), nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
