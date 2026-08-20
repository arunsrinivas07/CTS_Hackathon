from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class ClaimStatusHistory(Base):
    __tablename__ = "claim_status_history"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    old_status = Column(String(30), nullable=True)
    new_status = Column(String(30), nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reason = Column(String(500), nullable=True)
    changed_at = Column(DateTime(timezone=True), server_default=func.now())
