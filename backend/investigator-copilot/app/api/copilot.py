"""
FastAPI endpoint(s) for the Investigator Copilot.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.adapters.database_adapter import get_claim_db_tool, get_provider_db_tool
from app.adapters.investigation_state_adapter import (
    InvestigationStateProvider,
    get_investigation_state_provider,
)
from app.adapters.ml_adapter import get_ml_tool
from app.adapters.rag_adapter import get_rag_tool
from app.adapters.scenario_adapter import get_scenario_tool
from app.schemas.copilot import CopilotQueryRequest, CopilotQueryResponse
from app.services.copilot_service import CopilotService
from app.services.tool_router import ToolRouter

router = APIRouter(prefix="/api/copilot", tags=["copilot"])


def get_copilot_service(
    state_provider: InvestigationStateProvider = Depends(get_investigation_state_provider),
) -> CopilotService:
    """
    Dependency wiring for the Copilot service.

    INTEGRATION POINT: this is the single place where adapter
    implementations are assembled. When real RAG/ML/DB/Orchestrator
    implementations exist, update the corresponding `get_*` factory
    functions in app/adapters/*.py — nothing here or in copilot_service.py
    needs to change.
    """
    tool_router = ToolRouter(
        rag_tool=get_rag_tool(),
        ml_tool=get_ml_tool(),
        scenario_tool=get_scenario_tool(),
        provider_db_tool=get_provider_db_tool(),
        claim_db_tool=get_claim_db_tool(),
    )
    return CopilotService(state_provider=state_provider, tool_router=tool_router)


@router.post("/query", response_model=CopilotQueryResponse)
def query_copilot(
    request: CopilotQueryRequest,
    copilot_service: CopilotService = Depends(get_copilot_service),
) -> CopilotQueryResponse:
    """
    Ask the Investigator Copilot a question about an existing investigation.

    The Copilot answers using the existing InvestigationState wherever
    possible, and only calls an approved RAG / ML / Provider-DB / Claim-DB /
    Scenario tool when the required information is not already present.
    """
    return copilot_service.answer_question(request)
