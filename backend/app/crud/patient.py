from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate


def get_patient(db: Session, patient_id: int) -> Optional[Patient]:
    return db.query(Patient).filter(Patient.id == patient_id).first()


def get_patients(db: Session, skip: int = 0, limit: int = 100) -> List[Patient]:
    return db.query(Patient).offset(skip).limit(limit).all()


def create_patient(db: Session, patient: PatientCreate) -> Patient:
    db_patient = Patient(**patient.model_dump())
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient


def update_patient(db: Session, patient_id: int, patient: PatientUpdate) -> Optional[Patient]:
    db_patient = get_patient(db, patient_id)
    if not db_patient:
        return None
    for field, value in patient.model_dump(exclude_unset=True).items():
        setattr(db_patient, field, value)
    db.commit()
    db.refresh(db_patient)
    return db_patient


def delete_patient(db: Session, patient_id: int) -> bool:
    db_patient = get_patient(db, patient_id)
    if not db_patient:
        return False
    db.delete(db_patient)
    db.commit()
    return True
