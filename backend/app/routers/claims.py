import os
import shutil
from tempfile import NamedTemporaryFile
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_active_user
from app.crud import claim as crud_claim
from app.crud import claim_line_item as crud_line
from app.crud import claim_status as crud_status
from app.crud import claim_payment as crud_payment
from app.schemas.claim import ClaimCreate, ClaimUpdate, ClaimResponse
from app.schemas.claim_line_item import ClaimLineItemCreate, ClaimLineItemResponse
from app.schemas.claim_status import ClaimStatusHistoryCreate, ClaimStatusHistoryResponse
from app.schemas.claim_payment import ClaimPaymentCreate, ClaimPaymentResponse

router = APIRouter(prefix="/claims", tags=["Claims"])


@router.post("/extract_from_document")
def extract_claim_from_document(file: UploadFile = File(...)):
    """
    Extracts structured medical claim features from an uploaded PDF or Image document.
    """
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".png", ".jpg", ".jpeg", ".txt"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Supported formats are PDF, PNG, JPG, JPEG, TXT."
        )

    with NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        from app.services.pdf_claim_extractor import process_document
        result = process_document(tmp_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document feature extraction failed: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


# ─── Claims ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[ClaimResponse])
def list_claims(
    skip: int = 0, limit: int = 100,
    status: Optional[str] = Query(None),
    patient_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    if status:
        return crud_claim.get_claims_by_status(db, status)
    if patient_id:
        return crud_claim.get_claims_by_patient(db, patient_id)
    return crud_claim.get_claims(db, skip=skip, limit=limit)


@router.post("/", response_model=ClaimResponse, status_code=201)
def create_claim(claim: ClaimCreate, db: Session = Depends(get_db),
                 _=Depends(get_current_active_user)):
    from app.models.claim import Claim
    from app.models.patient import Patient
    from app.models.provider import Provider
    import json
    from datetime import datetime

    existing = db.query(Claim).filter(Claim.claim_number == claim.claim_number).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Claim with number '{claim.claim_number}' already exists. Please use a unique claim number (e.g. CLM-2026-002)."
        )

    # Auto-lookup or create Patient in patients table
    raw_feat = claim.raw_extracted_features or {}
    if isinstance(raw_feat, str):
        try:
            raw_feat = json.loads(raw_feat)
        except Exception:
            raw_feat = {}

    bene_id = str(raw_feat.get("bene_id") or "").strip()
    patient_name = str(raw_feat.get("patient_name") or "").strip()
    dob_str = str(raw_feat.get("dob") or "").strip()

    gender_str = str(raw_feat.get("gender") or "").strip().lower()
    if gender_str:
        if gender_str.startswith("m"):
            gender_str = "male"
        elif gender_str.startswith("f"):
            gender_str = "female"
        elif gender_str.startswith("o"):
            gender_str = "other"
        elif gender_str not in ["male", "female", "other", "unknown"]:
            gender_str = "unknown"
    else:
        gender_str = None

    if bene_id or patient_name:
        patient = None
        if bene_id:
            patient = db.query(Patient).filter(
                (Patient.member_id == bene_id) | (Patient.patient_external_id == bene_id) | (Patient.patient_external_id == f"PAT-{bene_id}")
            ).first()
        if not patient and patient_name:
            parts = patient_name.split()
            fn = parts[0]
            ln = " ".join(parts[1:]) if len(parts) > 1 else None
            patient = db.query(Patient).filter(Patient.first_name == fn, Patient.last_name == ln).first()

        if not patient:
            parts = patient_name.split() if patient_name else ["Patient"]
            fn = parts[0] if parts else "Patient"
            ln = " ".join(parts[1:]) if len(parts) > 1 else None

            dob_val = None
            if dob_str:
                try:
                    dob_val = datetime.strptime(dob_str, "%Y-%m-%d").date()
                except Exception:
                    pass

            ext_id = f"PAT-{bene_id}" if bene_id else f"PAT-{int(datetime.now().timestamp())}"
            patient = Patient(
                patient_external_id=ext_id,
                first_name=fn,
                last_name=ln,
                date_of_birth=dob_val,
                gender=gender_str if gender_str else None,
                member_id=bene_id if bene_id else ext_id,
            )
            db.add(patient)
            db.commit()
            db.refresh(patient)
        elif gender_str and not patient.gender:
            patient.gender = gender_str
            db.commit()

        if patient:
            claim.patient_id = patient.id

    # Auto-lookup or create Provider in providers table
    provider_npi = str(raw_feat.get("provider_id") or "").strip()
    if provider_npi:
        provider = db.query(Provider).filter(Provider.npi == provider_npi).first()
        if not provider:
            provider = Provider(
                npi=provider_npi,
                name=f"Medical Center ({provider_npi})",
                provider_type="Facility",
                is_active=True,
            )
            db.add(provider)
            db.commit()
            db.refresh(provider)
        if provider:
            claim.provider_id = provider.id

    created_claim = crud_claim.create_claim(db, claim)
    
    # Automatically trigger live ML Hybrid Scoring
    try:
        from app.routers.ml import score_db_claim
        score_db_claim(claim_id=created_claim.id, db=db, _=None)
    except Exception as e:
        print(f"[ML SCORING] Warning: Auto-scoring for claim {created_claim.id} failed: {e}")
        
    return created_claim


@router.get("/{claim_id}", response_model=ClaimResponse)
def get_claim(claim_id: int, db: Session = Depends(get_db),
              _=Depends(get_current_active_user)):
    db_claim = crud_claim.get_claim(db, claim_id)
    if not db_claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return db_claim


@router.put("/{claim_id}", response_model=ClaimResponse)
def update_claim(claim_id: int, claim: ClaimUpdate, db: Session = Depends(get_db),
                 _=Depends(get_current_active_user)):
    db_claim = crud_claim.update_claim(db, claim_id, claim)
    if not db_claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return db_claim


@router.delete("/{claim_id}", status_code=204)
def delete_claim(claim_id: int, db: Session = Depends(get_db),
                 _=Depends(get_current_active_user)):
    if not crud_claim.delete_claim(db, claim_id):
        raise HTTPException(status_code=404, detail="Claim not found")


# ─── Line Items ──────────────────────────────────────────────────────────────

@router.get("/{claim_id}/line-items", response_model=List[ClaimLineItemResponse])
def get_line_items(claim_id: int, db: Session = Depends(get_db),
                   _=Depends(get_current_active_user)):
    return crud_line.get_line_items_by_claim(db, claim_id)


@router.post("/{claim_id}/line-items", response_model=ClaimLineItemResponse, status_code=201)
def add_line_item(claim_id: int, item: ClaimLineItemCreate, db: Session = Depends(get_db),
                  _=Depends(get_current_active_user)):
    item.claim_id = claim_id
    return crud_line.create_line_item(db, item)


# ─── Status History ───────────────────────────────────────────────────────────

@router.get("/{claim_id}/status-history", response_model=List[ClaimStatusHistoryResponse])
def get_status_history(claim_id: int, db: Session = Depends(get_db),
                       _=Depends(get_current_active_user)):
    return crud_status.get_status_history(db, claim_id)


@router.post("/{claim_id}/status-history", response_model=ClaimStatusHistoryResponse, status_code=201)
def add_status_history(claim_id: int, entry: ClaimStatusHistoryCreate, db: Session = Depends(get_db),
                       _=Depends(get_current_active_user)):
    return crud_status.create_status_history(db, entry)


# ─── Payments ────────────────────────────────────────────────────────────────

@router.get("/{claim_id}/payments", response_model=List[ClaimPaymentResponse])
def get_payments(claim_id: int, db: Session = Depends(get_db),
                 _=Depends(get_current_active_user)):
    return crud_payment.get_payments_by_claim(db, claim_id)


@router.post("/{claim_id}/payments", response_model=ClaimPaymentResponse, status_code=201)
def add_payment(claim_id: int, payment: ClaimPaymentCreate, db: Session = Depends(get_db),
                _=Depends(get_current_active_user)):
    return crud_payment.create_payment(db, payment)
