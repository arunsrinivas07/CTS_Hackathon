from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base


class FraudPattern(Base):
    __tablename__ = "fraud_patterns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    pattern_type = Column(String(100), nullable=True)
    rules = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
