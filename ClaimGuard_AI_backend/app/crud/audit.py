from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.audit import AuditLog
from app.schemas.audit import AuditLogCreate


def create_audit_log(db: Session, log: AuditLogCreate) -> AuditLog:
    db_log = AuditLog(**log.model_dump())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log


def get_audit_logs(db: Session, skip: int = 0, limit: int = 100) -> List[AuditLog]:
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()


def get_audit_logs_by_user(db: Session, user_id: int) -> List[AuditLog]:
    return db.query(AuditLog).filter(AuditLog.user_id == user_id).all()
