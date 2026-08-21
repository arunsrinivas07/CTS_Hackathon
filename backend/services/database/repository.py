"""
repository.py
=============

Database Repository Abstraction Layer.
Decouples database investigation tools and services from the underlying data source
(Mock Repository vs. Real SQL/Postgres Database).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from schemas.tool import (
    ClaimHistoryResponse,
    ProviderHistoryResponse,
    ProviderPeerComparisonResponse,
    ProviderStatisticsResponse,
    RelatedClaimsResponse,
)
from utils.tool_helpers import logger


class BaseDatabaseRepository(ABC):
    """Abstract interface for database investigation tools."""

    @abstractmethod
    def get_provider_statistics(
        self, provider_id: str, procedure: Optional[str] = None
    ) -> Optional[ProviderStatisticsResponse]:
        """Retrieve aggregated statistics for a provider."""
        pass

    @abstractmethod
    def get_provider_history(
        self, provider_id: str
    ) -> Optional[ProviderHistoryResponse]:
        """Retrieve historical claims and billing timeline for a provider."""
        pass

    @abstractmethod
    def get_provider_peer_comparison(
        self, provider_id: str, procedure: Optional[str] = None
    ) -> Optional[ProviderPeerComparisonResponse]:
        """Retrieve peer benchmark comparisons for a provider."""
        pass

    @abstractmethod
    def get_claim_history(self, claim_id: str) -> Optional[ClaimHistoryResponse]:
        """Retrieve timeline and audit history for a specific claim."""
        pass

    @abstractmethod
    def get_related_claims(
        self, claim_id: str
    ) -> Optional[RelatedClaimsResponse]:
        """Retrieve related claims (by patient, episode, or provider)."""
        pass


class MockDatabaseRepository(BaseDatabaseRepository):
    """
    Mock Database Repository with coherent dummy claims and provider records
    for investigation case C10234 / ABC123.
    """

    def __init__(self) -> None:
        self._providers: Dict[str, Dict[str, Any]] = {
            "ABC123": {
                "provider_id": "ABC123",
                "specialty": "Radiology",
                "procedure": "MRI",
                "provider_count": 520,
                "peer_average": 185.0,
                "peer_median": 170.0,
                "peer_95_percentile": 310.0,
                "total_claims_submitted": 1450,
                "total_billed_amount": 2680000.0,
                "denial_rate": 0.28,
                "history": [
                    {"period": "2025-Q3", "mri_claims": 85, "billed": 408000.0, "denial_rate": 0.12},
                    {"period": "2025-Q4", "mri_claims": 110, "billed": 528000.0, "denial_rate": 0.19},
                    {"period": "2026-Q1", "mri_claims": 155, "billed": 744000.0, "denial_rate": 0.26},
                    {"period": "2026-Q2", "mri_claims": 170, "billed": 816000.0, "denial_rate": 0.32},
                ],
                "peer_metrics": {
                    "procedure": "MRI - Lumbar Spine (CPT 72148)",
                    "utilization_rate_per_1000": {"provider": 84.2, "peer_avg": 26.5, "peer_95th": 45.0},
                    "average_charge_per_scan": {"provider": 4800.0, "peer_avg": 1850.0, "peer_95th": 2900.0},
                    "repeat_scan_within_30_days_pct": {"provider": 22.4, "peer_avg": 3.8, "peer_95th": 7.5},
                    "denial_rate_pct": {"provider": 28.0, "peer_avg": 8.5, "peer_95th": 15.0},
                    "conservative_therapy_compliance_pct": {"provider": 14.0, "peer_avg": 78.0, "peer_95th": 92.0},
                },
            }
        }

        self._claims: Dict[str, Dict[str, Any]] = {
            "C10234": {
                "claim_id": "C10234",
                "patient_id": "P8821",
                "provider_id": "ABC123",
                "procedure": "MRI",
                "cpt_code": "72148",
                "diagnosis": "lower_back_pain",
                "icd10": "M54.5",
                "billed_amount": 4800.0,
                "service_date": "2026-06-15",
                "status": "under_review",
                "timeline": [
                    {"event": "Claim Received", "date": "2026-06-16", "details": "Electronic 837P submission"},
                    {"event": "Automated Rule Flag", "date": "2026-06-16", "details": "High procedure frequency for provider ABC123"},
                    {"event": "ML Fraud Score Assigned", "date": "2026-06-17", "details": "Score 0.87 (HIGH)"},
                    {"event": "Routed to SIU", "date": "2026-06-18", "details": "Assigned for manual clinical review"},
                ],
            }
        }

        self._patient_claims: Dict[str, List[Dict[str, Any]]] = {
            "P8821": [
                {
                    "claim_id": "C10190",
                    "service_date": "2026-05-10",
                    "cpt_code": "99213",
                    "description": "Office/outpatient visit, established patient",
                    "provider_id": "ABC123",
                    "billed_amount": 250.0,
                    "status": "paid",
                },
                {
                    "claim_id": "C10212",
                    "service_date": "2026-05-28",
                    "cpt_code": "72040",
                    "description": "Radiologic exam, spine, cervical; 2 or 3 views",
                    "provider_id": "ABC123",
                    "billed_amount": 400.0,
                    "status": "paid",
                },
                {
                    "claim_id": "C10234",
                    "service_date": "2026-06-15",
                    "cpt_code": "72148",
                    "description": "MRI lumbar spine without contrast",
                    "provider_id": "ABC123",
                    "billed_amount": 4800.0,
                    "status": "under_review",
                },
                {
                    "claim_id": "C10260",
                    "service_date": "2026-07-02",
                    "cpt_code": "72149",
                    "description": "MRI lumbar spine with contrast (Repeat within 17 days)",
                    "provider_id": "ABC123",
                    "billed_amount": 5200.0,
                    "status": "flagged",
                },
            ]
        }

    def get_provider_statistics(
        self, provider_id: str, procedure: Optional[str] = None
    ) -> Optional[ProviderStatisticsResponse]:
        provider = self._providers.get(provider_id)
        if not provider:
            return None

        return ProviderStatisticsResponse(
            status="success",
            tool="provider_statistics",
            provider_id=provider_id,
            procedure=procedure or provider.get("procedure", "MRI"),
            provider_count=provider["provider_count"],
            peer_average=provider["peer_average"],
            peer_median=provider["peer_median"],
            peer_95_percentile=provider["peer_95_percentile"],
            specialty=provider["specialty"],
            total_claims_submitted=provider["total_claims_submitted"],
            total_billed_amount=provider["total_billed_amount"],
            denial_rate=provider["denial_rate"],
        )

    def get_provider_history(
        self, provider_id: str
    ) -> Optional[ProviderHistoryResponse]:
        provider = self._providers.get(provider_id)
        if not provider:
            return None

        return ProviderHistoryResponse(
            status="success",
            tool="provider_history",
            provider_id=provider_id,
            history=provider["history"],
        )

    def get_provider_peer_comparison(
        self, provider_id: str, procedure: Optional[str] = None
    ) -> Optional[ProviderPeerComparisonResponse]:
        provider = self._providers.get(provider_id)
        if not provider:
            return None

        return ProviderPeerComparisonResponse(
            status="success",
            tool="provider_peer_comparison",
            provider_id=provider_id,
            procedure=procedure or provider.get("procedure", "MRI"),
            specialty=provider["specialty"],
            metrics=provider["peer_metrics"],
        )

    def get_claim_history(self, claim_id: str) -> Optional[ClaimHistoryResponse]:
        claim = self._claims.get(claim_id)
        if not claim:
            return None

        return ClaimHistoryResponse(
            status="success",
            tool="claim_history",
            claim_id=claim_id,
            patient_id=claim.get("patient_id"),
            provider_id=claim.get("provider_id"),
            claims=claim.get("timeline", []),
        )

    def get_related_claims(
        self, claim_id: str
    ) -> Optional[RelatedClaimsResponse]:
        claim = self._claims.get(claim_id)
        if not claim:
            return None

        patient_id = claim.get("patient_id")
        related = self._patient_claims.get(patient_id, [])

        return RelatedClaimsResponse(
            status="success",
            tool="claim_related_claims",
            claim_id=claim_id,
            patient_id=patient_id,
            related_claims=related,
            evidence=related,
            reason=None if related else "No related claims found for this patient episode.",
        )


class RealDatabaseRepository(BaseDatabaseRepository):
    """
    Real Database Repository connecting to SQL/PostgreSQL database via SQLAlchemy or asyncpg.
    """

    def __init__(self, connection_string: Optional[str] = None) -> None:
        self.connection_string = connection_string
        self.engine = None
        self._initialize_connection()

    def _initialize_connection(self) -> None:
        if not self.connection_string:
            logger.warning("RealDatabaseRepository initialized without connection_string.")
            return
        try:
            # Placeholder for real DB engine init:
            # from sqlalchemy import create_engine
            # self.engine = create_engine(self.connection_string)
            pass
        except Exception as e:
            logger.error("Failed to connect to database: %s", e)

    def get_provider_statistics(
        self, provider_id: str, procedure: Optional[str] = None
    ) -> Optional[ProviderStatisticsResponse]:
        if not self.engine:
            raise RuntimeError("Database connection not established. Set DATA_MODE=mock or provide DATABASE_URL.")
        raise NotImplementedError("Real DB queries not yet connected.")

    def get_provider_history(
        self, provider_id: str
    ) -> Optional[ProviderHistoryResponse]:
        if not self.engine:
            raise RuntimeError("Database connection not established. Set DATA_MODE=mock or provide DATABASE_URL.")
        raise NotImplementedError("Real DB queries not yet connected.")

    def get_provider_peer_comparison(
        self, provider_id: str, procedure: Optional[str] = None
    ) -> Optional[ProviderPeerComparisonResponse]:
        if not self.engine:
            raise RuntimeError("Database connection not established. Set DATA_MODE=mock or provide DATABASE_URL.")
        raise NotImplementedError("Real DB queries not yet connected.")

    def get_claim_history(self, claim_id: str) -> Optional[ClaimHistoryResponse]:
        if not self.engine:
            raise RuntimeError("Database connection not established. Set DATA_MODE=mock or provide DATABASE_URL.")
        raise NotImplementedError("Real DB queries not yet connected.")

    def get_related_claims(
        self, claim_id: str
    ) -> Optional[RelatedClaimsResponse]:
        if not self.engine:
            raise RuntimeError("Database connection not established. Set DATA_MODE=mock or provide DATABASE_URL.")
        raise NotImplementedError("Real DB queries not yet connected.")
