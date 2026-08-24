from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id"), nullable=False)
    report_type = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)
    generated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
