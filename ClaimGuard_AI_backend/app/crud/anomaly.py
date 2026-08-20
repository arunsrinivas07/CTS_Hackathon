from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.anomaly import Anomaly
from app.schemas.anomaly import AnomalyCreate


def get_anomaly(db: Session, anomaly_id: int) -> Optional[Anomaly]:
    return db.query(Anomaly).filter(Anomaly.id == anomaly_id).first()


def get_anomalies_by_claim(db: Session, claim_id: int) -> List[Anomaly]:
    return db.query(Anomaly).filter(Anomaly.claim_id == claim_id).all()


def create_anomaly(db: Session, anomaly: AnomalyCreate) -> Anomaly:
    db_anomaly = Anomaly(**anomaly.model_dump())
    db.add(db_anomaly)
    db.commit()
    db.refresh(db_anomaly)
    return db_anomaly
