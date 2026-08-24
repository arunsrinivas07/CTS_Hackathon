from sqlalchemy import Column, Integer, String, ForeignKey
from app.database import Base


class RelatedClaim(Base):
    __tablename__ = "related_claims"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    related_claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    relationship_type = Column(String(100), nullable=True)
