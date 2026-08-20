from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_active_user
from app.crud import risk as crud_risk
from app.schemas.risk import RiskScoreCreate, RiskScoreUpdate, RiskScoreResponse

router = APIRouter(prefix="/risk", tags=["Risk Scoring"])


@router.get("/claim/{claim_id}", response_model=List[RiskScoreResponse])
def get_risk_scores_for_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    return crud_risk.get_risk_scores_by_claim(db, claim_id)


@router.post("/", response_model=RiskScoreResponse, status_code=201)
def create_risk_score(
    risk: RiskScoreCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    return crud_risk.create_risk_score(db, risk)


@router.get("/{risk_id}", response_model=RiskScoreResponse)
def get_risk_score(
    risk_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    db_risk = crud_risk.get_risk_score(db, risk_id)
    if not db_risk:
        raise HTTPException(status_code=404, detail="Risk score not found")
    return db_risk


@router.put("/{risk_id}", response_model=RiskScoreResponse)
def update_risk_score(
    risk_id: int,
    risk: RiskScoreUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    db_risk = crud_risk.update_risk_score(db, risk_id, risk)
    if not db_risk:
        raise HTTPException(status_code=404, detail="Risk score not found")
    return db_risk
