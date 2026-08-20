from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
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
    existing = db.query(Claim).filter(Claim.claim_number == claim.claim_number).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Claim with number '{claim.claim_number}' already exists. Please use a unique claim number (e.g. CLM-2026-002)."
        )
    return crud_claim.create_claim(db, claim)


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
