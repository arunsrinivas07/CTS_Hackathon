from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_active_user
from app.crud import user as crud_user
from app.schemas.user import UserCreate, UserUpdate, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
def get_me(current_user=Depends(get_current_active_user)):
    """Get current authenticated user."""
    return current_user


@router.get("/", response_model=List[UserResponse])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db),
               _=Depends(get_current_active_user)):
    return crud_user.get_users(db, skip=skip, limit=limit)


@router.post("/", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing = crud_user.get_user_by_email(db, user.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    from app.crud import role as crud_role
    role_exists = crud_role.get_role(db, user.role_id)
    if not role_exists:
        raise HTTPException(
            status_code=400,
            detail=f"Role ID {user.role_id} does not exist in the database. Please use an existing role ID (like 1) or create role {user.role_id} in /api/v1/roles/ first."
        )
    return crud_user.create_user(db, user)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db),
             _=Depends(get_current_active_user)):
    db_user = crud_user.get_user(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user: UserUpdate, db: Session = Depends(get_db),
                _=Depends(get_current_active_user)):
    db_user = crud_user.update_user(db, user_id, user)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user
