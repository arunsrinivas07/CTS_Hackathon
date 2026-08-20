from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_active_user
from app.crud import notification as crud_notif
from app.schemas.notification import NotificationCreate, NotificationResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/my", response_model=List[NotificationResponse])
def get_my_notifications(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return crud_notif.get_notifications_by_user(db, current_user.id)


@router.post("/", response_model=NotificationResponse, status_code=201)
def create_notification(
    notif: NotificationCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    return crud_notif.create_notification(db, notif)


@router.patch("/{notif_id}/read", response_model=NotificationResponse)
def mark_notification_as_read(
    notif_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    db_notif = crud_notif.mark_as_read(db, notif_id)
    if not db_notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return db_notif
