from sqlalchemy import Column, Integer, Float, String, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Anomaly(Base):
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    anomaly_type = Column(String(100), nullable=False)
    description = Column(String(2000), nullable=False)
    score = Column(Float, nullable=False)
    evidence = Column(JSON, nullable=True)
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
