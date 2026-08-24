"""
database_service.py
===================

SERVICE layer for database investigation operations.
Interacts with the underlying repository without exposing SQL to agents or orchestrator.
"""

from __future__ import annotations

from typing import Optional
from app.llm.config import settings
from app.services.agentic.database.repository import (
    BaseDatabaseRepository,
    MockDatabaseRepository,
    RealDatabaseRepository,
)
from app.schemas.agentic.tool import (
    ClaimHistoryResponse,
    ProviderHistoryResponse,
    ProviderPeerComparisonResponse,
    ProviderStatisticsResponse,
    RelatedClaimsResponse,
    ToolErrorResponse,
)
from app.utils.tool_helpers import format_tool_error, logger, timed


class DatabaseService:
    """
    Service coordinating database lookups for providers, claims, and peer benchmarks.
    """

    def __init__(self, repository: Optional[BaseDatabaseRepository] = None) -> None:
        if repository is not None:
            self._repo = repository
        elif settings.data_mode == "real":
            self._repo = RealDatabaseRepository(settings.database_url)
        else:
            self._repo = MockDatabaseRepository()

    @timed
    def get_provider_statistics(
        self, provider_id: str, procedure: Optional[str] = None
    ) -> ProviderStatisticsResponse | ToolErrorResponse:
        """Fetch provider summary statistics and peer distribution benchmarks."""
        try:
            stats = self._repo.get_provider_statistics(provider_id, procedure)
            if stats is None:
                return format_tool_error(
                    error_code="PROVIDER_NOT_FOUND",
                    message=f"Provider '{provider_id}' was not found in the database.",
                    details={"provider_id": provider_id},
                )
            return stats
        except Exception as exc:
            logger.error("Database error fetching statistics for provider %s: %s", provider_id, exc)
            return format_tool_error(
                error_code="DATABASE_SERVICE_ERROR",
                message=f"Database error fetching provider statistics: {str(exc)}",
                details={"provider_id": provider_id},
            )

    @timed
    def get_provider_history(
        self, provider_id: str
    ) -> ProviderHistoryResponse | ToolErrorResponse:
        """Fetch provider historical billing quarterly / monthly trend."""
        try:
            history = self._repo.get_provider_history(provider_id)
            if history is None:
                return format_tool_error(
                    error_code="PROVIDER_NOT_FOUND",
                    message=f"Provider '{provider_id}' was not found in the database.",
                    details={"provider_id": provider_id},
                )
            return history
        except Exception as exc:
            logger.error("Database error fetching history for provider %s: %s", provider_id, exc)
            return format_tool_error(
                error_code="DATABASE_SERVICE_ERROR",
                message=f"Database error fetching provider history: {str(exc)}",
                details={"provider_id": provider_id},
            )

    @timed
    def get_provider_peer_comparison(
        self, provider_id: str, procedure: Optional[str] = None
    ) -> ProviderPeerComparisonResponse | ToolErrorResponse:
        """Fetch provider peer benchmark comparisons."""
        try:
            peers = self._repo.get_provider_peer_comparison(provider_id, procedure)
            if peers is None:
                return format_tool_error(
                    error_code="PROVIDER_NOT_FOUND",
                    message=f"Provider '{provider_id}' was not found in the database.",
                    details={"provider_id": provider_id},
                )
            return peers
        except Exception as exc:
            logger.error("Database error fetching peer comparison for %s: %s", provider_id, exc)
            return format_tool_error(
                error_code="DATABASE_SERVICE_ERROR",
                message=f"Database error fetching peer comparison: {str(exc)}",
                details={"provider_id": provider_id},
            )

    @timed
    def get_claim_history(
        self, claim_id: str
    ) -> ClaimHistoryResponse | ToolErrorResponse:
        """Fetch timeline and event trajectory for a specific claim."""
        try:
            history = self._repo.get_claim_history(claim_id)
            if history is None:
                return format_tool_error(
                    error_code="CLAIM_NOT_FOUND",
                    message=f"Claim '{claim_id}' was not found in the claims database.",
                    details={"claim_id": claim_id},
                )
            return history
        except Exception as exc:
            logger.error("Database error fetching claim history for %s: %s", claim_id, exc)
            return format_tool_error(
                error_code="DATABASE_SERVICE_ERROR",
                message=f"Database error fetching claim history: {str(exc)}",
                details={"claim_id": claim_id},
            )

    @timed
    def get_related_claims(
        self, claim_id: str
    ) -> RelatedClaimsResponse | ToolErrorResponse:
        """Fetch related claims associated with the patient, provider, or episode."""
        try:
            related = self._repo.get_related_claims(claim_id)
            if related is None:
                return format_tool_error(
                    error_code="CLAIM_NOT_FOUND",
                    message=f"Claim '{claim_id}' was not found in the claims database.",
                    details={"claim_id": claim_id},
                )
            return related
        except Exception as exc:
            logger.error("Database error fetching related claims for %s: %s", claim_id, exc)
            return format_tool_error(
                error_code="DATABASE_SERVICE_ERROR",
                message=f"Database error fetching related claims: {str(exc)}",
                details={"claim_id": claim_id},
            )
