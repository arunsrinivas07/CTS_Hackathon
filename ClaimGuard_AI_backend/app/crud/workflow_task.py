from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.workflow_task import WorkflowTask
from app.schemas.workflow_task import WorkflowTaskCreate, WorkflowTaskUpdate


def get_task(db: Session, task_id: int) -> Optional[WorkflowTask]:
    return db.query(WorkflowTask).filter(WorkflowTask.id == task_id).first()


def get_tasks_by_investigation(db: Session, inv_id: int) -> List[WorkflowTask]:
    return db.query(WorkflowTask).filter(WorkflowTask.investigation_id == inv_id).all()


def create_task(db: Session, task: WorkflowTaskCreate) -> WorkflowTask:
    db_task = WorkflowTask(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def update_task(db: Session, task_id: int, task: WorkflowTaskUpdate) -> Optional[WorkflowTask]:
    db_task = get_task(db, task_id)
    if not db_task:
        return None
    for field, value in task.model_dump(exclude_unset=True).items():
        setattr(db_task, field, value)
    db.commit()
    db.refresh(db_task)
    return db_task


def delete_task(db: Session, task_id: int) -> bool:
    db_task = get_task(db, task_id)
    if not db_task:
        return False
    db.delete(db_task)
    db.commit()
    return True
