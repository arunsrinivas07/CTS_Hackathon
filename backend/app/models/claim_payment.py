from sqlalchemy import Column, Integer, Date, Numeric, String, ForeignKey
from app.database import Base


class ClaimPayment(Base):
    __tablename__ = "claim_payments"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    payment_date = Column(Date, nullable=False)
    paid_amount = Column(Numeric(12, 2), nullable=False)
    adjustment_amount = Column(Numeric(12, 2), nullable=True)
    denial_amount = Column(Numeric(12, 2), nullable=True)
    payment_reference = Column(String(100), nullable=True)
