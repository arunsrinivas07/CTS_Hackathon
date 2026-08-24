import threading
from typing import Optional
from datetime import datetime, timezone
from fastapi import HTTPException
from app.schemas.agentic.admin import QueueItem, Investigator, Assignment
from app.agent.orchestrator import start_investigation
from app.store import store

class AdminStateStore:
    def __init__(self):
        self.lock = threading.Lock()
        self.queue: list[QueueItem] = []
        self.investigators: dict[str, Investigator] = {
            "INV-01": Investigator(investigator_id="INV-01", name="Alice", active=True),
            "INV-02": Investigator(investigator_id="INV-02", name="Bob", active=True),
            "INV-03": Investigator(investigator_id="INV-03", name="Charlie", active=True)
        }
        self.assignments: dict[str, Assignment] = {}

    def get_queue(self) -> list[QueueItem]:
        with self.lock:
            # Sort queue by priority_score descending, then queued_at ascending
            return sorted(self.queue, key=lambda q: (-q.priority_score, q.queued_at))

    def add_to_queue(self, item: QueueItem):
        with self.lock:
            if not any(q.claim_id == item.claim_id for q in self.queue):
                self.queue.append(item)

    def pop_from_queue(self, claim_id: str) -> Optional[QueueItem]:
        with self.lock:
            for idx, item in enumerate(self.queue):
                if item.claim_id == claim_id:
                    return self.queue.pop(idx)
            return None

    def get_investigators(self) -> list[Investigator]:
        with self.lock:
            return list(self.investigators.values())

    def get_assignment(self, assignment_id: str) -> Optional[Assignment]:
        with self.lock:
            return self.assignments.get(assignment_id)

admin_store = AdminStateStore()

def determine_best_investigator() -> Optional[Investigator]:
    with admin_store.lock:
        active_invs = [inv for inv in admin_store.investigators.values() if inv.active]
        if not active_invs:
            return None
        
        # Sort by:
        # 1. Workload (ascending)
        # 2. Last assigned at (ascending/oldest first)
        # 3. Investigator ID (ascending tie-breaker)
        active_invs.sort(key=lambda inv: (
            inv.workload,
            inv.last_assigned_at,
            inv.investigator_id
        ))
        return active_invs[0]

def assign_claim(claim_id: str) -> Assignment:
    # 1. Pop from queue
    queue_item = admin_store.pop_from_queue(claim_id)
    if not queue_item:
        raise HTTPException(status_code=404, detail="Claim not found in queue")

    with admin_store.lock:
        # 2. Find best investigator
        investigator = determine_best_investigator()
        if not investigator:
            # Re-queue if no investigator available
            admin_store.queue.append(queue_item)
            raise HTTPException(status_code=503, detail="No active investigators available")
        
        # 3. Update investigator workload
        investigator.workload += 1
        now_str = datetime.now(timezone.utc).isoformat()
        investigator.last_assigned_at = now_str
        
        # 4. Initialize Investigation via Member 1 Orchestrator
        try:
            state = start_investigation(
                claim_id=queue_item.claim_id,
                claim_data=queue_item.claim_data,
                risk_score=queue_item.risk_score,
                risk_level=queue_item.risk_level,
                shap_contributors=queue_item.shap_contributors,
                detected_patterns=queue_item.detected_patterns,
                max_iterations=5,
                max_revisions=2
            )
            store.save(state)
        except Exception as e:
            # Revert assignment workload on failure
            investigator.workload -= 1
            admin_store.queue.append(queue_item)
            raise HTTPException(status_code=500, detail=f"Failed to initialize investigation: {str(e)}")

        # 5. Create Assignment Record
        assignment = Assignment(
            claim_id=queue_item.claim_id,
            investigator_id=investigator.investigator_id,
            investigation_id=state.investigation_id,
            assigned_at=now_str
        )
        admin_store.assignments[assignment.assignment_id] = assignment

    return assignment

def reassign_claim(assignment_id: str) -> Assignment:
    with admin_store.lock:
        old_assignment = admin_store.assignments.get(assignment_id)
        if not old_assignment or old_assignment.status != "assigned":
            raise HTTPException(status_code=404, detail="Active assignment not found")

        # Find new investigator (excluding the current one)
        active_invs = [inv for inv in admin_store.investigators.values() if inv.active and inv.investigator_id != old_assignment.investigator_id]
        if not active_invs:
            raise HTTPException(status_code=503, detail="No other active investigators available")
        
        active_invs.sort(key=lambda inv: (inv.workload, inv.last_assigned_at, inv.investigator_id))
        new_investigator = active_invs[0]

        # Update workloads
        old_inv = admin_store.investigators[old_assignment.investigator_id]
        old_inv.workload = max(0, old_inv.workload - 1)
        old_assignment.status = "reassigned"

        new_investigator.workload += 1
        now_str = datetime.now(timezone.utc).isoformat()
        new_investigator.last_assigned_at = now_str

        new_assignment = Assignment(
            claim_id=old_assignment.claim_id,
            investigator_id=new_investigator.investigator_id,
            investigation_id=old_assignment.investigation_id,
            assigned_at=now_str
        )
        admin_store.assignments[new_assignment.assignment_id] = new_assignment

    return new_assignment
