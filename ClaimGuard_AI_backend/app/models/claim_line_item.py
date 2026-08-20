from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
from app.database import Base


class ClaimLineItem(Base):
    __tablename__ = "claim_line_items"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    line_number = Column(Integer, nullable=False)
    procedure_code = Column(String(20), nullable=True)
    revenue_code = Column(String(20), nullable=True)
    units = Column(Numeric(8, 2), default=1, nullable=False)
    billed_amount = Column(Numeric(12, 2), nullable=False)
    paid_amount = Column(Numeric(12, 2), nullable=True)
    modifier = Column(String(20), nullable=True)
