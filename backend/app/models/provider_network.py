from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from app.database import Base


class ProviderNetwork(Base):
    __tablename__ = "provider_networks"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    network_name = Column(String(255), nullable=False)
    plan_type = Column(String(100), nullable=True)
    is_in_network = Column(Boolean, default=True, nullable=False)
