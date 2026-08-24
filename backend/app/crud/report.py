from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.report import Report
from app.schemas.report import ReportCreate, ReportUpdate


def get_report(db: Session, report_id: int) -> Optional[Report]:
    return db.query(Report).filter(Report.id == report_id).first()


def get_reports(db: Session, skip: int = 0, limit: int = 100) -> List[Report]:
    return db.query(Report).offset(skip).limit(limit).all()


def get_reports_by_investigation(db: Session, inv_id: int) -> List[Report]:
    return db.query(Report).filter(Report.investigation_id == inv_id).all()


def create_report(db: Session, report: ReportCreate, generated_by: Optional[int] = None) -> Report:
    data = report.model_dump()
    if generated_by:
        data["generated_by"] = generated_by
    db_report = Report(**data)
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report


def update_report(db: Session, report_id: int, report: ReportUpdate) -> Optional[Report]:
    db_report = get_report(db, report_id)
    if not db_report:
        return None
    for field, value in report.model_dump(exclude_unset=True).items():
        setattr(db_report, field, value)
    db.commit()
    db.refresh(db_report)
    return db_report
