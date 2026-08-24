from sqlalchemy import Column, Integer, String, ForeignKey
from app.database import Base


class ClaimDiagnosis(Base):
    __tablename__ = "claim_diagnoses"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    diagnosis_code = Column(String(20), nullable=False)
    diagnosis_type = Column(String(50), nullable=True)
    description = Column(String(500), nullable=True)
