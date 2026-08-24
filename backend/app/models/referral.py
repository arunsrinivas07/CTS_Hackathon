from sqlalchemy import Column, Integer, String, Date, ForeignKey
from app.database import Base


class Referral(Base):
    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    referring_provider_id = Column(Integer, ForeignKey("providers.id"), nullable=True)
    referred_to_provider_id = Column(Integer, ForeignKey("providers.id"), nullable=True)
    referral_date = Column(Date, nullable=True)
    reason = Column(String(1000), nullable=True)
    status = Column(String(30), default="pending", nullable=False)
