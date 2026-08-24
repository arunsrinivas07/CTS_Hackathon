from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.claim_payment import ClaimPayment
from app.schemas.claim_payment import ClaimPaymentCreate


def get_payment(db: Session, payment_id: int) -> Optional[ClaimPayment]:
    return db.query(ClaimPayment).filter(ClaimPayment.id == payment_id).first()


def get_payments_by_claim(db: Session, claim_id: int) -> List[ClaimPayment]:
    return db.query(ClaimPayment).filter(ClaimPayment.claim_id == claim_id).all()


def create_payment(db: Session, payment: ClaimPaymentCreate) -> ClaimPayment:
    db_payment = ClaimPayment(**payment.model_dump())
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment
