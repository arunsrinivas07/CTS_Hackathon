from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base


class PolicyRule(Base):
    __tablename__ = "policy_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    rule_code = Column(String(50), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    rule_logic = Column(JSON, nullable=True)
    category = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
