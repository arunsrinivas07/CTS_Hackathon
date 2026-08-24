"""
In-Memory implementation of StateStore.

Serves as the default storage mechanism for Member 1. Can be replaced with
a DB-backed store implementation via dependency injection or configuration.
"""
from __future__ import annotations

from typing import Optional

from .store_base import StateStore
from .database_store import DatabaseStateStore
from app.schemas.agentic.investigation import InvestigationState
import os


class InMemoryStateStore(StateStore):
    def __init__(self):
        self._store = {}

    def save(self, state: InvestigationState) -> None:
        self._store[state.investigation_id] = state

    def get(self, investigation_id: str) -> Optional[InvestigationState]:
        return self._store.get(investigation_id)

    def all_investigations(self) -> list[InvestigationState]:
        return list(self._store.values())

# Global default instance
if os.environ.get("DATA_MODE") == "mock":
    _DEFAULT_STORE = InMemoryStateStore()
else:
    _DEFAULT_STORE = DatabaseStateStore()

def get_store() -> StateStore:
    return _DEFAULT_STORE


def save(state: InvestigationState) -> None:
    get_store().save(state)


def get(investigation_id: str) -> Optional[InvestigationState]:
    return get_store().get(investigation_id)


def all_investigations() -> list[InvestigationState]:
    return get_store().all_investigations()

