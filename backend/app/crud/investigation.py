from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.investigation import Investigation
from app.schemas.investigation import InvestigationCreate, InvestigationUpdate


def get_investigation(db: Session, inv_id: int) -> Optional[Investigation]:
    return db.query(Investigation).filter(Investigation.id == inv_id).first()


def get_investigations(db: Session, skip: int = 0, limit: int = 100) -> List[Investigation]:
    return db.query(Investigation).offset(skip).limit(limit).all()


def get_investigations_by_claim(db: Session, claim_id: int) -> List[Investigation]:
    return db.query(Investigation).filter(Investigation.claim_id == claim_id).all()


def create_investigation(db: Session, inv: InvestigationCreate) -> Investigation:
    db_inv = Investigation(**inv.model_dump())
    db.add(db_inv)
    db.commit()
    db.refresh(db_inv)
    return db_inv


def update_investigation(db: Session, inv_id: int, inv: InvestigationUpdate) -> Optional[Investigation]:
    db_inv = get_investigation(db, inv_id)
    if not db_inv:
        return None
    for field, value in inv.model_dump(exclude_unset=True).items():
        setattr(db_inv, field, value)
    db.commit()
    db.refresh(db_inv)
    return db_inv
