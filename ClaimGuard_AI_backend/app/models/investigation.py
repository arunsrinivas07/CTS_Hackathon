from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Investigation(Base):
    __tablename__ = "investigations"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    priority = Column(String(20), default="medium", nullable=False)
    reason = Column(String(1000), nullable=True)
    status = Column(String(30), default="open", nullable=False)
    notes = Column(String(2000), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
