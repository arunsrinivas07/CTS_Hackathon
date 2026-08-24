from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.documentation_request import DocumentationRequest
from app.schemas.documentation_request import DocumentationRequestCreate, DocumentationRequestUpdate


def get_request(db: Session, request_id: int) -> Optional[DocumentationRequest]:
    return db.query(DocumentationRequest).filter(DocumentationRequest.id == request_id).first()


def get_requests(db: Session, skip: int = 0, limit: int = 100) -> List[DocumentationRequest]:
    return db.query(DocumentationRequest).offset(skip).limit(limit).all()


def get_requests_by_investigation(db: Session, inv_id: int) -> List[DocumentationRequest]:
    return db.query(DocumentationRequest).filter(DocumentationRequest.investigation_id == inv_id).all()


def create_request(db: Session, request: DocumentationRequestCreate) -> DocumentationRequest:
    db_request = DocumentationRequest(**request.model_dump())
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    return db_request


def update_request(db: Session, request_id: int, request: DocumentationRequestUpdate) -> Optional[DocumentationRequest]:
    db_request = get_request(db, request_id)
    if not db_request:
        return None
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(db_request, field, value)
    db.commit()
    db.refresh(db_request)
    return db_request


def delete_request(db: Session, request_id: int) -> bool:
    db_request = get_request(db, request_id)
    if not db_request:
        return False
    db.delete(db_request)
    db.commit()
    return True
