from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.finding import Finding
from app.schemas.finding import FindingCreate, FindingUpdate


def get_finding(db: Session, finding_id: int) -> Optional[Finding]:
    return db.query(Finding).filter(Finding.id == finding_id).first()


def get_findings_by_investigation(db: Session, inv_id: int) -> List[Finding]:
    return db.query(Finding).filter(Finding.investigation_id == inv_id).all()


def create_finding(db: Session, finding: FindingCreate) -> Finding:
    db_finding = Finding(**finding.model_dump())
    db.add(db_finding)
    db.commit()
    db.refresh(db_finding)
    return db_finding


def update_finding(db: Session, finding_id: int, finding: FindingUpdate) -> Optional[Finding]:
    db_finding = get_finding(db, finding_id)
    if not db_finding:
        return None
    for field, value in finding.model_dump(exclude_unset=True).items():
        setattr(db_finding, field, value)
    db.commit()
    db.refresh(db_finding)
    return db_finding


def delete_finding(db: Session, finding_id: int) -> bool:
    db_finding = get_finding(db, finding_id)
    if not db_finding:
        return False
    db.delete(db_finding)
    db.commit()
    return True
