from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.provider import Provider
from app.schemas.provider import ProviderCreate, ProviderUpdate


def get_provider(db: Session, provider_id: int) -> Optional[Provider]:
    return db.query(Provider).filter(Provider.id == provider_id).first()


def get_providers(db: Session, skip: int = 0, limit: int = 100) -> List[Provider]:
    return db.query(Provider).offset(skip).limit(limit).all()


def create_provider(db: Session, provider: ProviderCreate) -> Provider:
    db_provider = Provider(**provider.model_dump())
    db.add(db_provider)
    db.commit()
    db.refresh(db_provider)
    return db_provider


def update_provider(db: Session, provider_id: int, provider: ProviderUpdate) -> Optional[Provider]:
    db_provider = get_provider(db, provider_id)
    if not db_provider:
        return None
    for field, value in provider.model_dump(exclude_unset=True).items():
        setattr(db_provider, field, value)
    db.commit()
    db.refresh(db_provider)
    return db_provider


def delete_provider(db: Session, provider_id: int) -> bool:
    db_provider = get_provider(db, provider_id)
    if not db_provider:
        return False
    db.delete(db_provider)
    db.commit()
    return True
