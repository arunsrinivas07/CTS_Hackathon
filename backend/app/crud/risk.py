from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.risk import RiskScore
from app.schemas.risk import RiskScoreCreate, RiskScoreUpdate


def get_risk_score(db: Session, risk_id: int) -> Optional[RiskScore]:
    return db.query(RiskScore).filter(RiskScore.id == risk_id).first()


def get_risk_scores(db: Session, skip: int = 0, limit: int = 100) -> List[RiskScore]:
    return db.query(RiskScore).offset(skip).limit(limit).all()


def get_risk_scores_by_claim(db: Session, claim_id: int) -> List[RiskScore]:
    return db.query(RiskScore).filter(RiskScore.claim_id == claim_id).all()


def create_risk_score(db: Session, risk: RiskScoreCreate) -> RiskScore:
    db_risk = RiskScore(**risk.model_dump())
    db.add(db_risk)
    db.commit()
    db.refresh(db_risk)
    return db_risk


def update_risk_score(db: Session, risk_id: int, risk: RiskScoreUpdate) -> Optional[RiskScore]:
    db_risk = get_risk_score(db, risk_id)
    if not db_risk:
        return None
    for field, value in risk.model_dump(exclude_unset=True).items():
        setattr(db_risk, field, value)
    db.commit()
    db.refresh(db_risk)
    return db_risk
