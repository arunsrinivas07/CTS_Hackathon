from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.notification import Notification
from app.schemas.notification import NotificationCreate


def get_notification(db: Session, notif_id: int) -> Optional[Notification]:
    return db.query(Notification).filter(Notification.id == notif_id).first()


def get_notifications_by_user(db: Session, user_id: int) -> List[Notification]:
    return db.query(Notification).filter(Notification.user_id == user_id).all()


def create_notification(db: Session, notif: NotificationCreate) -> Notification:
    db_notif = Notification(**notif.model_dump())
    db.add(db_notif)
    db.commit()
    db.refresh(db_notif)
    return db_notif


def mark_as_read(db: Session, notif_id: int) -> Optional[Notification]:
    db_notif = get_notification(db, notif_id)
    if not db_notif:
        return None
    db_notif.is_read = True
    db.commit()
    db.refresh(db_notif)
    return db_notif
