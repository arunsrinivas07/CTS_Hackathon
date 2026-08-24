from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Resolution(Base):
    __tablename__ = "resolutions"

    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id"), nullable=False)
    resolution_type = Column(String(100), nullable=False)
    summary = Column(String(2000), nullable=True)
    action_taken = Column(String(1000), nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), server_default=func.now())
