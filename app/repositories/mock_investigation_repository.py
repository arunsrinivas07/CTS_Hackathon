"""
Mock in-memory InvestigationState repository.

INTEGRATION POINT:
This is the ONLY implementation of `InvestigationStateProvider`
(see app/adapters/investigation_state_adapter.py) that exists for this MVP.
When the real Investigation Orchestrator is available, replace this class
with one that fetches InvestigationState from wherever the orchestrator
persists it (DB, cache, service call, etc.) — the interface contract stays
the same, so nothing else in the Copilot needs to change.
"""

from __future__ import annotations

from typing import Dict, Optional

from app.data.mock_data import MOCK_INVESTIGATIONS
from app.schemas.investigation import InvestigationState


class MockInvestigationRepository:
    def __init__(self) -> None:
        # In-memory store, seeded with demo data. A real implementation
        # would not hold state in process memory.
        self._store: Dict[str, InvestigationState] = dict(MOCK_INVESTIGATIONS)

    def get(self, investigation_id: str) -> Optional[InvestigationState]:
        return self._store.get(investigation_id)

    def save(self, state: InvestigationState) -> None:
        """Persist an updated InvestigationState (e.g. after the Copilot
        attaches new evidence retrieved from a tool)."""
        state.touch()
        self._store[state.investigation_id] = state


# Module-level singleton so the mock "database" persists across requests
# within a single process run. A real repository would not need this.
_repository_instance = MockInvestigationRepository()


def get_mock_repository() -> MockInvestigationRepository:
    return _repository_instance
