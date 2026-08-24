from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    claim_number = Column(String(100), unique=True, nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    claim_type = Column(String(50), nullable=True)
    service_date = Column(Date, nullable=False)
    submission_date = Column(Date, nullable=True)
    total_billed_amount = Column(Numeric(12, 2), nullable=False)
    total_paid_amount = Column(Numeric(12, 2), nullable=True)
    status = Column(String(30), default="submitted", nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    diag_count = Column(Integer, default=1, nullable=True)
    proc_count = Column(Integer, default=1, nullable=True)
    line_count = Column(Integer, default=1, nullable=True)
    state = Column(String(10), nullable=True)
    raw_extracted_features = Column(String(2000), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    assigned_investigator = relationship("User", foreign_keys=[assigned_to], lazy="joined")
    risk_scores = relationship("RiskScore", lazy="joined", order_by="desc(RiskScore.id)")
    provider = relationship("Provider", foreign_keys=[provider_id], lazy="joined")
    patient = relationship("Patient", foreign_keys=[patient_id], lazy="joined")
