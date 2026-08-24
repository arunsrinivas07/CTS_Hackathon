from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_active_user
from app.crud import documentation_request as crud_doc_request
from app.schemas.documentation_request import (
    DocumentationRequestCreate,
    DocumentationRequestUpdate,
    DocumentationRequestResponse
)

router = APIRouter(prefix="/documentation-requests", tags=["Documentation Requests"])


@router.get("/", response_model=List[DocumentationRequestResponse])
def list_documentation_requests(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    """Get all documentation requests"""
    return crud_doc_request.get_requests(db, skip=skip, limit=limit)


@router.get("/investigation/{inv_id}", response_model=List[DocumentationRequestResponse])
def get_requests_for_investigation(
    inv_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    """Get documentation requests for a specific investigation"""
    return crud_doc_request.get_requests_by_investigation(db, inv_id)


@router.post("/", response_model=DocumentationRequestResponse, status_code=201)
def create_documentation_request(
    request: DocumentationRequestCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    """Create a new documentation request"""
    return crud_doc_request.create_request(db, request)


@router.get("/{request_id}", response_model=DocumentationRequestResponse)
def get_documentation_request(
    request_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    """Get a specific documentation request"""
    db_request = crud_doc_request.get_request(db, request_id)
    if not db_request:
        raise HTTPException(status_code=404, detail="Documentation request not found")
    return db_request


@router.put("/{request_id}", response_model=DocumentationRequestResponse)
def update_documentation_request(
    request_id: int,
    request: DocumentationRequestUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    """Update a documentation request"""
    db_request = crud_doc_request.update_request(db, request_id, request)
    if not db_request:
        raise HTTPException(status_code=404, detail="Documentation request not found")
    return db_request


@router.delete("/{request_id}", status_code=204)
def delete_documentation_request(
    request_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    """Delete a documentation request"""
    if not crud_doc_request.delete_request(db, request_id):
        raise HTTPException(status_code=404, detail="Documentation request not found")
