from sqlalchemy import Column, Integer, String, Date, ForeignKey
from app.database import Base


class ClaimAttachment(Base):
    __tablename__ = "claim_attachments"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    attachment_type = Column(String(100), nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
