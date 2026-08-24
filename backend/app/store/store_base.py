"""
Abstract StateStore Interface for Investigation Persistence.

Decouples API routes and orchestrator from the underlying persistence engine.
Allows InMemoryStateStore to be swapped for DatabaseStateStore (Member 2 DB integration)
without changing business logic.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.schemas.agentic.investigation import InvestigationState


class StateStore(ABC):
    @abstractmethod
    def save(self, state: InvestigationState) -> None:
        """Persist or update investigation state."""
        pass

    @abstractmethod
    def get(self, investigation_id: str) -> Optional[InvestigationState]:
        """Retrieve investigation state by investigation_id."""
        pass

    @abstractmethod
    def all_investigations(self) -> list[InvestigationState]:
        """Retrieve all stored investigation states."""
        pass
