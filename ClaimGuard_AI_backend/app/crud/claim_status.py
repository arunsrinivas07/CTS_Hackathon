from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.claim_status import ClaimStatusHistory
from app.schemas.claim_status import ClaimStatusHistoryCreate


def get_status_history(db: Session, claim_id: int) -> List[ClaimStatusHistory]:
    return db.query(ClaimStatusHistory).filter(ClaimStatusHistory.claim_id == claim_id).all()


def create_status_history(db: Session, entry: ClaimStatusHistoryCreate) -> ClaimStatusHistory:
    db_entry = ClaimStatusHistory(**entry.model_dump())
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry
