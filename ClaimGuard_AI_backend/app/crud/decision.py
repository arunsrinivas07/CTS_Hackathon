from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.decision import Decision
from app.schemas.decision import DecisionCreate


def get_decision(db: Session, decision_id: int) -> Optional[Decision]:
    return db.query(Decision).filter(Decision.id == decision_id).first()


def get_decisions_by_investigation(db: Session, inv_id: int) -> List[Decision]:
    return db.query(Decision).filter(Decision.investigation_id == inv_id).all()


def create_decision(db: Session, decision: DecisionCreate, decided_by: Optional[int] = None) -> Decision:
    data = decision.model_dump()
    if decided_by:
        data["decided_by"] = decided_by
    db_decision = Decision(**data)
    db.add(db_decision)
    db.commit()
    db.refresh(db_decision)
    return db_decision
