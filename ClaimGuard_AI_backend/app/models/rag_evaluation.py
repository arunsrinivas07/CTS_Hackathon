from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class RAGEvaluation(Base):
    __tablename__ = "rag_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    retrieval_id = Column(Integer, ForeignKey("retrievals.id"), nullable=True)
    faithfulness_score = Column(Float, nullable=True)
    relevance_score = Column(Float, nullable=True)
    groundedness_score = Column(Float, nullable=True)
    evaluation_notes = Column(String(2000), nullable=True)
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now())
