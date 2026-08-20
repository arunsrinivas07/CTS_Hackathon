from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Escalation(Base):
    __tablename__ = "escalations"

    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id"), nullable=False)
    escalated_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    reason = Column(String(1000), nullable=True)
    status = Column(String(30), default="open", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
