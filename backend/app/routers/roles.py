from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.crud import role as crud_role
from app.schemas.role import RoleCreate, RoleUpdate, RoleResponse

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("/", response_model=List[RoleResponse])
def list_roles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud_role.get_roles(db, skip=skip, limit=limit)


@router.post("/", response_model=RoleResponse, status_code=201)
def create_role(role: RoleCreate, db: Session = Depends(get_db)):
    return crud_role.create_role(db, role)


@router.get("/{role_id}", response_model=RoleResponse)
def get_role(role_id: int, db: Session = Depends(get_db)):
    db_role = crud_role.get_role(db, role_id)
    if not db_role:
        raise HTTPException(status_code=404, detail="Role not found")
    return db_role


@router.put("/{role_id}", response_model=RoleResponse)
def update_role(role_id: int, role: RoleUpdate, db: Session = Depends(get_db)):
    db_role = crud_role.update_role(db, role_id, role)
    if not db_role:
        raise HTTPException(status_code=404, detail="Role not found")
    return db_role


@router.delete("/{role_id}", status_code=204)
def delete_role(role_id: int, db: Session = Depends(get_db)):
    if not crud_role.delete_role(db, role_id):
        raise HTTPException(status_code=404, detail="Role not found")
