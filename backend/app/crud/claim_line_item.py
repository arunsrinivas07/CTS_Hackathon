from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.claim_line_item import ClaimLineItem
from app.schemas.claim_line_item import ClaimLineItemCreate


def get_line_item(db: Session, item_id: int) -> Optional[ClaimLineItem]:
    return db.query(ClaimLineItem).filter(ClaimLineItem.id == item_id).first()


def get_line_items_by_claim(db: Session, claim_id: int) -> List[ClaimLineItem]:
    return db.query(ClaimLineItem).filter(ClaimLineItem.claim_id == claim_id).all()


def create_line_item(db: Session, item: ClaimLineItemCreate) -> ClaimLineItem:
    db_item = ClaimLineItem(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def delete_line_item(db: Session, item_id: int) -> bool:
    db_item = get_line_item(db, item_id)
    if not db_item:
        return False
    db.delete(db_item)
    db.commit()
    return True
