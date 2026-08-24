from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.evidence import Evidence
from app.schemas.evidence import EvidenceCreate


def get_evidence(db: Session, evidence_id: int) -> Optional[Evidence]:
    return db.query(Evidence).filter(Evidence.id == evidence_id).first()


def get_evidence_by_investigation(db: Session, inv_id: int) -> List[Evidence]:
    return db.query(Evidence).filter(Evidence.investigation_id == inv_id).all()


def create_evidence(db: Session, evidence: EvidenceCreate, collected_by: Optional[int] = None) -> Evidence:
    data = evidence.model_dump()
    if collected_by:
        data["collected_by"] = collected_by
    db_evidence = Evidence(**data)
    db.add(db_evidence)
    db.commit()
    db.refresh(db_evidence)
    return db_evidence


def delete_evidence(db: Session, evidence_id: int) -> bool:
    db_evidence = get_evidence(db, evidence_id)
    if not db_evidence:
        return False
    db.delete(db_evidence)
    db.commit()
    return True
