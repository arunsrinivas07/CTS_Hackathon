from fastapi import APIRouter
from schemas.admin import QueueItem, Investigator, Assignment
from services.admin_service import admin_store, assign_claim, reassign_claim

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/queue", response_model=list[QueueItem])
def get_queue() -> list[QueueItem]:
    return admin_store.get_queue()

@router.post("/queue", response_model=QueueItem)
def add_to_queue(item: QueueItem) -> QueueItem:
    admin_store.add_to_queue(item)
    return item

@router.get("/investigators", response_model=list[Investigator])
def get_investigators() -> list[Investigator]:
    return admin_store.get_investigators()

@router.post("/assign/{claim_id}", response_model=Assignment)
def assign_claim_route(claim_id: str) -> Assignment:
    return assign_claim(claim_id)

@router.get("/assignments/{assignment_id}", response_model=Assignment)
def get_assignment(assignment_id: str) -> Assignment:
    assignment = admin_store.get_assignment(assignment_id)
    if not assignment:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment

@router.post("/reassign/{assignment_id}", response_model=Assignment)
def reassign_claim_route(assignment_id: str) -> Assignment:
    return reassign_claim(assignment_id)
