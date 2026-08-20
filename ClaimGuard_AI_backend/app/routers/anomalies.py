from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_active_user
from app.crud import anomaly as crud_anomaly
from app.schemas.anomaly import AnomalyCreate, AnomalyResponse

router = APIRouter(prefix="/anomalies", tags=["Anomalies"])


@router.get("/claim/{claim_id}", response_model=List[AnomalyResponse])
def get_anomalies_for_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    return crud_anomaly.get_anomalies_by_claim(db, claim_id)


@router.post("/", response_model=AnomalyResponse, status_code=201)
def create_anomaly(
    anomaly: AnomalyCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    return crud_anomaly.create_anomaly(db, anomaly)


@router.get("/{anomaly_id}", response_model=AnomalyResponse)
def get_anomaly(
    anomaly_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    db_anomaly = crud_anomaly.get_anomaly(db, anomaly_id)
    if not db_anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")
    return db_anomaly
