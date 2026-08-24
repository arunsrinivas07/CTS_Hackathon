from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_active_user
from app.crud import investigation as crud_inv
from app.crud import finding as crud_finding
from app.crud import evidence as crud_evidence
from app.crud import decision as crud_decision
from app.schemas.investigation import InvestigationCreate, InvestigationUpdate, InvestigationResponse
from app.schemas.finding import FindingCreate, FindingUpdate, FindingResponse
from app.schemas.evidence import EvidenceCreate, EvidenceResponse
from app.schemas.decision import DecisionCreate, DecisionResponse

router = APIRouter(prefix="/investigations", tags=["Investigations"])


# ─── Investigations ──────────────────────────────────────────────────────────

@router.get("/", response_model=List[InvestigationResponse])
def list_investigations(
    skip: int = 0,
    limit: int = 100,
    claim_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    if claim_id:
        return crud_inv.get_investigations_by_claim(db, claim_id)
    return crud_inv.get_investigations(db, skip=skip, limit=limit)


@router.post("/", response_model=InvestigationResponse, status_code=201)
def create_investigation(
    inv: InvestigationCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    return crud_inv.create_investigation(db, inv)


@router.get("/{inv_id}", response_model=InvestigationResponse)
def get_investigation(
    inv_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    db_inv = crud_inv.get_investigation(db, inv_id)
    if not db_inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return db_inv


@router.put("/{inv_id}", response_model=InvestigationResponse)
def update_investigation(
    inv_id: int,
    inv: InvestigationUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    db_inv = crud_inv.update_investigation(db, inv_id, inv)
    if not db_inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return db_inv


# ─── Findings Sub-resource ───────────────────────────────────────────────────

@router.get("/{inv_id}/findings", response_model=List[FindingResponse])
def list_findings(
    inv_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    return crud_finding.get_findings_by_investigation(db, inv_id)


@router.post("/{inv_id}/findings", response_model=FindingResponse, status_code=201)
def create_finding(
    inv_id: int,
    finding: FindingCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    finding.investigation_id = inv_id
    return crud_finding.create_finding(db, finding)


# ─── Evidence Sub-resource ───────────────────────────────────────────────────

@router.get("/{inv_id}/evidence", response_model=List[EvidenceResponse])
def list_evidence(
    inv_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    return crud_evidence.get_evidence_by_investigation(db, inv_id)


@router.post("/{inv_id}/evidence", response_model=EvidenceResponse, status_code=201)
def create_evidence(
    inv_id: int,
    evidence: EvidenceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    evidence.investigation_id = inv_id
    return crud_evidence.create_evidence(db, evidence, collected_by=current_user.id)


# ─── Decisions Sub-resource ──────────────────────────────────────────────────

@router.get("/{inv_id}/decisions", response_model=List[DecisionResponse])
def list_decisions(
    inv_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    return crud_decision.get_decisions_by_investigation(db, inv_id)


@router.post("/{inv_id}/decisions", response_model=DecisionResponse, status_code=201)
def create_decision(
    inv_id: int,
    decision: DecisionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    decision.investigation_id = inv_id
    return crud_decision.create_decision(db, decision, decided_by=current_user.id)
