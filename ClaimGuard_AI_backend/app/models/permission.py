from sqlalchemy import Column, Integer, String, Boolean
from app.database import Base


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, nullable=False)
    resource = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)
    is_allowed = Column(Boolean, default=True, nullable=False)
