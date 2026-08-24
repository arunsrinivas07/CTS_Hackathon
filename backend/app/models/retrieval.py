from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Retrieval(Base):
    __tablename__ = "retrievals"

    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id"), nullable=True)
    query = Column(String(2000), nullable=False)
    retrieved_docs = Column(JSON, nullable=True)
    relevance_score = Column(Float, nullable=True)
    retrieval_type = Column(String(100), nullable=True)
    retrieved_at = Column(DateTime(timezone=True), server_default=func.now())
