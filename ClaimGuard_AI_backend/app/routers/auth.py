from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import create_access_token
from app.crud import user as crud_user
from app.schemas.auth import TokenResponse, LoginRequest

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login with email and password — returns JWT access token."""
    user = crud_user.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(access_token=access_token)


@router.post("/login/json", response_model=TokenResponse)
def login_json(request: LoginRequest, db: Session = Depends(get_db)):
    """Login with JSON body."""
    user = crud_user.authenticate_user(db, request.email, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    access_token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(access_token=access_token)
