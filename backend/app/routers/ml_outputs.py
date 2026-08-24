"""
ML Outputs router - Store and retrieve ML model predictions
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.crud import ml_output as crud_ml_output
from app.schemas.ml_output import MLOutputResponse, MLOutputCreate, MLOutputUpdate
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/ml-outputs", tags=["ml-outputs"])


@router.get("/{output_id}", response_model=MLOutputResponse)
def get_ml_output(
    output_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific ML output by ID"""
    output = crud_ml_output.get(db, id=output_id)
    if not output:
        raise HTTPException(status_code=404, detail="ML output not found")
    return output


@router.get("/", response_model=List[MLOutputResponse])
def list_ml_outputs(
    skip: int = 0,
    limit: int = 100,
    transaction_type: Optional[str] = None,
    provider_id: Optional[str] = None,
    min_risk_score: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all ML outputs with optional filters"""
    outputs = crud_ml_output.get_multi(db, skip=skip, limit=limit)
    
    # Apply filters
    if transaction_type:
        outputs = [o for o in outputs if o.transaction_type == transaction_type]
    if provider_id:
        outputs = [o for o in outputs if o.provider_id == provider_id]
    if min_risk_score is not None:
        outputs = [o for o in outputs if o.final_risk_score >= min_risk_score]
    
    return outputs


@router.post("/", response_model=MLOutputResponse, status_code=201)
def create_ml_output(
    output_in: MLOutputCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new ML output record"""
    output = crud_ml_output.create(db, obj_in=output_in)
    return output


@router.put("/{output_id}", response_model=MLOutputResponse)
def update_ml_output(
    output_id: int,
    output_in: MLOutputUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an ML output record"""
    output = crud_ml_output.get(db, id=output_id)
    if not output:
        raise HTTPException(status_code=404, detail="ML output not found")
    
    output = crud_ml_output.update(db, db_obj=output, obj_in=output_in)
    return output


@router.delete("/{output_id}", status_code=204)
def delete_ml_output(
    output_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an ML output record"""
    output = crud_ml_output.get(db, id=output_id)
    if not output:
        raise HTTPException(status_code=404, detail="ML output not found")
    
    crud_ml_output.remove(db, id=output_id)
    return None
