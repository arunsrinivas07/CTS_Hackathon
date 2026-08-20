from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class ClaimEdit(Base):
    __tablename__ = "claim_edits"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    edit_type = Column(String(100), nullable=False)
    field_changed = Column(String(100), nullable=True)
    old_value = Column(String(500), nullable=True)
    new_value = Column(String(500), nullable=True)
    edited_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    edited_at = Column(DateTime(timezone=True), server_default=func.now())
