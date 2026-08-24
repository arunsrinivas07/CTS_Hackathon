from sqlalchemy import Column, Integer, String, Boolean, Float
from app.database import Base


class AIModel(Base):
    __tablename__ = "ai_models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False)
    model_type = Column(String(100), nullable=True)
    provider = Column(String(100), nullable=True)
    accuracy = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    description = Column(String(1000), nullable=True)
