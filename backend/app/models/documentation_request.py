from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class DocumentationRequest(Base):
    __tablename__ = "documentation_requests"

    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id"), nullable=False)
    requested_from = Column(String(255), nullable=True)
    document_type = Column(String(100), nullable=False)
    description = Column(String(1000), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    is_fulfilled = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
