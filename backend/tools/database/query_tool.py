"""
query_tool.py
=============

TOOL definition for controlled database investigation operations.
Prevents arbitrary SQL execution; exposes strictly parameterized safe methods.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from tools.database.database_service import DatabaseService
from schemas.tool import (
    ClaimHistoryResponse,
    ProviderHistoryResponse,
    ProviderPeerComparisonResponse,
    ProviderStatisticsResponse,
    RelatedClaimsResponse,
    ToolErrorResponse,
)
from tools.utils.tool_helpers import format_tool_error


class QueryTool:
    """
    Tool-facing wrapper around DatabaseService.
    Exposes safe, structured investigation query methods.
    """

    name: str = "query_tool"
    description: str = "Runs safe, structured queries against provider and claims databases."

    def __init__(self, database_service: Optional[DatabaseService] = None) -> None:
        self._database_service = database_service or DatabaseService()

    def get_provider_statistics(
        self, provider_id: str, procedure: Optional[str] = None
    ) -> ProviderStatisticsResponse | ToolErrorResponse:
        """Fetch provider metrics and peer distribution benchmarks."""
        if not provider_id:
            return format_tool_error(
                error_code="INVALID_INPUT",
                message="provider_id is required.",
            )
        return self._database_service.get_provider_statistics(provider_id, procedure)

    def get_provider_history(
        self, provider_id: str
    ) -> ProviderHistoryResponse | ToolErrorResponse:
        """Fetch provider historical billing trends."""
        if not provider_id:
            return format_tool_error(
                error_code="INVALID_INPUT",
                message="provider_id is required.",
            )
        return self._database_service.get_provider_history(provider_id)

    def get_provider_peer_comparison(
        self, provider_id: str, procedure: Optional[str] = None
    ) -> ProviderPeerComparisonResponse | ToolErrorResponse:
        """Fetch peer group benchmark comparisons for a provider."""
        if not provider_id:
            return format_tool_error(
                error_code="INVALID_INPUT",
                message="provider_id is required.",
            )
        return self._database_service.get_provider_peer_comparison(
            provider_id, procedure
        )

    def get_claim_history(
        self, claim_id: str
    ) -> ClaimHistoryResponse | ToolErrorResponse:
        """Fetch timeline and event trajectory for a specific claim."""
        if not claim_id:
            return format_tool_error(
                error_code="INVALID_INPUT",
                message="claim_id is required.",
            )
        return self._database_service.get_claim_history(claim_id)

    def get_related_claims(
        self, claim_id: str
    ) -> RelatedClaimsResponse | ToolErrorResponse:
        """Fetch related claims associated with the patient, provider, or episode."""
        if not claim_id:
            return format_tool_error(
                error_code="INVALID_INPUT",
                message="claim_id is required.",
            )
        return self._database_service.get_related_claims(claim_id)

    def run(self, payload: Dict[str, Any]) -> Any:
        """
        Generic run entrypoint for tool registry dispatch.
        """
        action = payload.get("action", payload.get("tool"))
        provider_id = payload.get("provider_id")
        claim_id = payload.get("claim_id")
        procedure = payload.get("procedure")

        if action == "provider_statistics":
            return self.get_provider_statistics(provider_id, procedure)
        elif action == "provider_history":
            return self.get_provider_history(provider_id)
        elif action == "provider_peer_comparison":
            return self.get_provider_peer_comparison(provider_id, procedure)
        elif action == "claim_history":
            return self.get_claim_history(claim_id)
        elif action == "claim_related_claims":
            return self.get_related_claims(claim_id)
        else:
            return format_tool_error(
                error_code="UNKNOWN_ACTION",
                message=f"Unknown database action '{action}'.",
                details={"payload": payload},
            )
