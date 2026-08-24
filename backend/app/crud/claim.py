from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.claim import Claim
from app.schemas.claim import ClaimCreate, ClaimUpdate


def get_claim(db: Session, claim_id: int) -> Optional[Claim]:
    return db.query(Claim).filter(Claim.id == claim_id).first()


def get_claims(db: Session, skip: int = 0, limit: int = 100) -> List[Claim]:
    return db.query(Claim).offset(skip).limit(limit).all()


def get_claims_by_patient(db: Session, patient_id: int) -> List[Claim]:
    return db.query(Claim).filter(Claim.patient_id == patient_id).all()


def get_claims_by_status(db: Session, status: str) -> List[Claim]:
    return db.query(Claim).filter(Claim.status == status).all()


import json

def create_claim(db: Session, claim: ClaimCreate) -> Claim:
    data = claim.model_dump()
    if isinstance(data.get("raw_extracted_features"), dict):
        data["raw_extracted_features"] = json.dumps(data["raw_extracted_features"])
    db_claim = Claim(**data)
    db.add(db_claim)
    db.commit()
    db.refresh(db_claim)
    return db_claim


def update_claim(db: Session, claim_id: int, claim: ClaimUpdate) -> Optional[Claim]:
    db_claim = get_claim(db, claim_id)
    if not db_claim:
        return None
    for field, value in claim.model_dump(exclude_unset=True).items():
        setattr(db_claim, field, value)
    db.commit()
    db.refresh(db_claim)
    return db_claim


def delete_claim(db: Session, claim_id: int) -> bool:
    db_claim = get_claim(db, claim_id)
    if not db_claim:
        return False
    db.delete(db_claim)
    db.commit()
    return True
