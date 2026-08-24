from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.ml_output import MLOutput
from app.schemas.ml_output import MLOutputCreate, MLOutputUpdate


def get(db: Session, id: int) -> Optional[MLOutput]:
    return db.query(MLOutput).filter(MLOutput.id == id).first()


def get_multi(db: Session, skip: int = 0, limit: int = 100) -> List[MLOutput]:
    return db.query(MLOutput).offset(skip).limit(limit).all()


def create(db: Session, obj_in: MLOutputCreate) -> MLOutput:
    db_obj = MLOutput(**obj_in.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update(db: Session, db_obj: MLOutput, obj_in: MLOutputUpdate) -> MLOutput:
    update_data = obj_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def remove(db: Session, id: int) -> MLOutput:
    obj = db.query(MLOutput).get(id)
    db.delete(obj)
    db.commit()
    return obj

