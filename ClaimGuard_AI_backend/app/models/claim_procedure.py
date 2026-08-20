from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
from app.database import Base


class ClaimProcedure(Base):
    __tablename__ = "claim_procedures"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    procedure_code = Column(String(20), nullable=False)
    procedure_type = Column(String(50), nullable=True)
    description = Column(String(500), nullable=True)
    billed_amount = Column(Numeric(12, 2), nullable=True)
