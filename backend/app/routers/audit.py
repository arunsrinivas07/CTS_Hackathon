from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_active_user
from app.crud import audit as crud_audit
from app.schemas.audit import AuditLogCreate, AuditLogResponse

router = APIRouter(prefix="/audit", tags=["Audit Logs"])


@router.get("/", response_model=List[AuditLogResponse])
def list_audit_logs(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    if user_id:
        return crud_audit.get_audit_logs_by_user(db, user_id)
    return crud_audit.get_audit_logs(db, skip=skip, limit=limit)


@router.post("/", response_model=AuditLogResponse, status_code=201)
def create_audit_log(
    log: AuditLogCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    if not log.user_id:
        log.user_id = current_user.id
    return crud_audit.create_audit_log(db, log)
