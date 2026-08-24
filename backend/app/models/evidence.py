from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id"), nullable=False)
    evidence_type = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(String(2000), nullable=True)
    source_reference = Column(String(500), nullable=True)
    file_path = Column(String(500), nullable=True)
    hash_value = Column(String(255), nullable=True)
    collected_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    collected_at = Column(DateTime(timezone=True), server_default=func.now())
