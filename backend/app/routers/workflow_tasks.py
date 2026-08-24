from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_active_user
from app.crud import workflow_task as crud_task
from app.schemas.workflow_task import WorkflowTaskCreate, WorkflowTaskUpdate, WorkflowTaskResponse

router = APIRouter(prefix="/tasks", tags=["Workflow Tasks"])


@router.get("/my-tasks", response_model=List[WorkflowTaskResponse])
def get_my_tasks(
    status: str = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Get tasks assigned to current user"""
    return crud_task.get_tasks_by_user(db, current_user.id, status=status)


@router.get("/investigation/{inv_id}", response_model=List[WorkflowTaskResponse])
def get_tasks_for_investigation(
    inv_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    return crud_task.get_tasks_by_investigation(db, inv_id)


@router.post("/", response_model=WorkflowTaskResponse, status_code=201)
def create_task(
    task: WorkflowTaskCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    return crud_task.create_task(db, task)


@router.get("/{task_id}", response_model=WorkflowTaskResponse)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    db_task = crud_task.get_task(db, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task


@router.put("/{task_id}", response_model=WorkflowTaskResponse)
def update_task(
    task_id: int,
    task: WorkflowTaskUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    db_task = crud_task.update_task(db, task_id, task)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task


@router.delete("/{task_id}", status_code=204)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    if not crud_task.delete_task(db, task_id):
        raise HTTPException(status_code=404, detail="Task not found")
