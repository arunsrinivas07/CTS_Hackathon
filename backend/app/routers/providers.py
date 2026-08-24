from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_active_user
from app.crud import provider as crud_provider
from app.schemas.provider import ProviderCreate, ProviderUpdate, ProviderResponse

router = APIRouter(prefix="/providers", tags=["Providers"])


@router.get("/", response_model=List[ProviderResponse])
def list_providers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db),
                   _=Depends(get_current_active_user)):
    return crud_provider.get_providers(db, skip=skip, limit=limit)


@router.post("/", response_model=ProviderResponse, status_code=201)
def create_provider(provider: ProviderCreate, db: Session = Depends(get_db),
                    _=Depends(get_current_active_user)):
    from app.models.provider import Provider
    existing = db.query(Provider).filter(Provider.npi == provider.npi).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Provider with NPI '{provider.npi}' already exists. Please use a unique NPI."
        )
    return crud_provider.create_provider(db, provider)


@router.get("/{provider_id}", response_model=ProviderResponse)
def get_provider(provider_id: int, db: Session = Depends(get_db),
                 _=Depends(get_current_active_user)):
    db_prov = crud_provider.get_provider(db, provider_id)
    if not db_prov:
        raise HTTPException(status_code=404, detail="Provider not found")
    return db_prov


@router.put("/{provider_id}", response_model=ProviderResponse)
def update_provider(provider_id: int, provider: ProviderUpdate, db: Session = Depends(get_db),
                    _=Depends(get_current_active_user)):
    db_prov = crud_provider.update_provider(db, provider_id, provider)
    if not db_prov:
        raise HTTPException(status_code=404, detail="Provider not found")
    return db_prov


@router.delete("/{provider_id}", status_code=204)
def delete_provider(provider_id: int, db: Session = Depends(get_db),
                    _=Depends(get_current_active_user)):
    if not crud_provider.delete_provider(db, provider_id):
        raise HTTPException(status_code=404, detail="Provider not found")
