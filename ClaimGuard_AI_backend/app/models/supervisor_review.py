from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class SupervisorReview(Base):
    __tablename__ = "supervisor_reviews"

    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_notes = Column(Text, nullable=True)
    outcome = Column(String(50), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), server_default=func.now())
