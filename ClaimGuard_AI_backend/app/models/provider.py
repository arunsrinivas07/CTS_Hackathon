from sqlalchemy import Column, Integer, String, Boolean
from app.database import Base


class Provider(Base):
    __tablename__ = "providers"

    id = Column(Integer, primary_key=True, index=True)
    npi = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    provider_type = Column(String(100), nullable=True)
    specialty = Column(String(150), nullable=True)
    tax_id = Column(String(50), nullable=True)
    address = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
