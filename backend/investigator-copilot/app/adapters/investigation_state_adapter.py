"""
InvestigationState Provider adapter.

INTEGRATION POINT (Investigation Orchestrator team):
Replace `MockInvestigationStateProvider` with a real implementation of
`InvestigationStateProvider` that talks to the actual Investigation
Orchestrator / its storage layer. The Copilot only ever depends on the
`InvestigationStateProvider` interface below, never on the mock directly
(see app/services/copilot_service.py dependency wiring), so swapping the
implementation requires no changes to Copilot logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.repositories.mock_investigation_repository import (
    MockInvestigationRepository,
    get_mock_repository,
)
from schemas.investigation import InvestigationState
from api.store import get_store


class InvestigationStateProvider(ABC):
    """Interface the Copilot depends on to fetch InvestigationState."""

    @abstractmethod
    def get_state(self, investigation_id: str) -> Optional[InvestigationState]:
        ...

    @abstractmethod
    def save_state(self, state: InvestigationState) -> None:
        ...


class MockInvestigationStateProvider(InvestigationStateProvider):
    """
    MVP implementation backed by the in-memory mock repository.

    INTEGRATION POINT: swap this for a provider that calls into the real
    Investigation Orchestrator (e.g. an internal service client or DB
    query) once that component exists.
    """

    def __init__(self, repository: Optional[MockInvestigationRepository] = None) -> None:
        self._repository = repository or get_mock_repository()

    def get_state(self, investigation_id: str) -> Optional[InvestigationState]:
        return self._repository.get(investigation_id)

    def save_state(self, state: InvestigationState) -> None:
        self._repository.save(state)


class RealInvestigationStateProvider(InvestigationStateProvider):
    def get_state(self, investigation_id: str) -> Optional[InvestigationState]:
        return get_store().get(investigation_id)

    def save_state(self, state: InvestigationState) -> None:
        get_store().save(state)

def get_investigation_state_provider() -> InvestigationStateProvider:
    """FastAPI dependency factory. Swapped to RealInvestigationStateProvider."""
    return RealInvestigationStateProvider()
