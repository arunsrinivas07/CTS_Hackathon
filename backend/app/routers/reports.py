from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_active_user
from app.crud import report as crud_report
from app.schemas.report import ReportCreate, ReportUpdate, ReportResponse

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/", response_model=List[ReportResponse])
def list_all_reports(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    """Get all reports"""
    return crud_report.get_reports(db, skip=skip, limit=limit)


@router.get("/investigation/{inv_id}", response_model=List[ReportResponse])
def get_reports_for_investigation(
    inv_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    return crud_report.get_reports_by_investigation(db, inv_id)


@router.post("/", response_model=ReportResponse, status_code=201)
def create_report(
    report: ReportCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return crud_report.create_report(db, report, generated_by=current_user.id)


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    db_report = crud_report.get_report(db, report_id)
    if not db_report:
        raise HTTPException(status_code=404, detail="Report not found")
    return db_report


@router.put("/{report_id}", response_model=ReportResponse)
def update_report(
    report_id: int,
    report: ReportUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    db_report = crud_report.update_report(db, report_id, report)
    if not db_report:
        raise HTTPException(status_code=404, detail="Report not found")
    return db_report
