from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_active_user
from app.crud import patient as crud_patient
from app.schemas.patient import PatientCreate, PatientUpdate, PatientResponse

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.get("/", response_model=List[PatientResponse])
def list_patients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db),
                  _=Depends(get_current_active_user)):
    return crud_patient.get_patients(db, skip=skip, limit=limit)


@router.post("/", response_model=PatientResponse, status_code=201)
def create_patient(patient: PatientCreate, db: Session = Depends(get_db),
                   _=Depends(get_current_active_user)):
    from app.models.patient import Patient
    existing = db.query(Patient).filter(Patient.patient_external_id == patient.patient_external_id).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Patient with external ID '{patient.patient_external_id}' already exists. Please use a unique external ID (e.g. PAT-1002)."
        )
    return crud_patient.create_patient(db, patient)


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(patient_id: int, db: Session = Depends(get_db),
                _=Depends(get_current_active_user)):
    db_patient = crud_patient.get_patient(db, patient_id)
    if not db_patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return db_patient


@router.put("/{patient_id}", response_model=PatientResponse)
def update_patient(patient_id: int, patient: PatientUpdate, db: Session = Depends(get_db),
                   _=Depends(get_current_active_user)):
    db_patient = crud_patient.update_patient(db, patient_id, patient)
    if not db_patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return db_patient


@router.delete("/{patient_id}", status_code=204)
def delete_patient(patient_id: int, db: Session = Depends(get_db),
                   _=Depends(get_current_active_user)):
    if not crud_patient.delete_patient(db, patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
