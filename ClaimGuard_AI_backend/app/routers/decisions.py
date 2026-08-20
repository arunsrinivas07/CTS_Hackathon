from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_active_user
from app.crud import decision as crud_decision
from app.schemas.decision import DecisionCreate, DecisionResponse

router = APIRouter(prefix="/decisions", tags=["Decisions"])


@router.get("/investigation/{inv_id}", response_model=List[DecisionResponse])
def get_decisions_for_investigation(
    inv_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    return crud_decision.get_decisions_by_investigation(db, inv_id)


@router.post("/", response_model=DecisionResponse, status_code=201)
def create_decision(
    decision: DecisionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return crud_decision.create_decision(db, decision, decided_by=current_user.id)


@router.get("/{decision_id}", response_model=DecisionResponse)
def get_decision(
    decision_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    db_dec = crud_decision.get_decision(db, decision_id)
    if not db_dec:
        raise HTTPException(status_code=404, detail="Decision not found")
    return db_dec
