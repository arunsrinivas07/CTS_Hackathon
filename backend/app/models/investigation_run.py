from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class InvestigationRun(Base):
    __tablename__ = "investigation_runs"

    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id"), nullable=False)
    run_type = Column(String(100), nullable=False)
    status = Column(String(30), default="pending", nullable=False)
    result = Column(JSON, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
