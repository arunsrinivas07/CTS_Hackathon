from sqlalchemy import Column, Integer, String, Float, ForeignKey
from app.database import Base


class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id"), nullable=False)
    finding_type = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(String(2000), nullable=False)
    severity = Column(String(20), nullable=False)
    confidence = Column(Float, nullable=True)
    source = Column(String(255), nullable=True)
