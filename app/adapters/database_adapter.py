"""
Provider DB Tool and Claim DB Tool adapters.

INTEGRATION POINT (DB / data-platform team):
Replace `MockProviderDBTool` and `MockClaimDBTool` with clients that call
the real, access-controlled Provider DB / Claim DB read interfaces. The
Copilot depends only on the `ProviderDBTool` / `ClaimDBTool` interfaces.

IMPORTANT: per project rules, the Copilot must never run unrestricted SQL
or access data outside the current investigation's scope. These adapters
intentionally expose only narrow, purpose-built read methods.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from app.data.mock_data import PROVIDER_MRI_HISTORY, RELATED_CLAIMS


class ProviderDBTool(ABC):
    @abstractmethod
    def get_mri_history(self, provider_name: str) -> List[dict]:
        """Return historical monthly procedure volume for a provider."""
        ...


class ClaimDBTool(ABC):
    @abstractmethod
    def get_related_claims(self, claim_id: str) -> List[dict]:
        """Return claims related to the given claim (e.g. same patient)."""
        ...


class MockProviderDBTool(ProviderDBTool):
    """
    MVP mock implementation using in-memory data.

    INTEGRATION POINT: replace with a call into the real, authorized
    Provider DB read API, e.g.
        response = provider_db_client.get_procedure_history(provider_name, months=12)
    """

    def get_mri_history(self, provider_name: str) -> List[dict]:
        return PROVIDER_MRI_HISTORY.get(provider_name, [])


class MockClaimDBTool(ClaimDBTool):
    """
    MVP mock implementation using in-memory data.

    INTEGRATION POINT: replace with a call into the real, authorized
    Claim DB read API, e.g.
        response = claim_db_client.get_related_claims(claim_id)
    """

    def get_related_claims(self, claim_id: str) -> List[dict]:
        return RELATED_CLAIMS.get(claim_id, [])


def get_provider_db_tool() -> ProviderDBTool:
    return MockProviderDBTool()


def get_claim_db_tool() -> ClaimDBTool:
    return MockClaimDBTool()
