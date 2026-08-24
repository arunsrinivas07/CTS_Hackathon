"""
Copilot Router - Integrated into main backend.

This router provides AI copilot functionality for investigations.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_active_user
from app.copilot.adapters.database_adapter import get_claim_db_tool, get_provider_db_tool
from app.copilot.adapters.investigation_state_adapter import (
    InvestigationStateProvider,
    get_investigation_state_provider,
)
from app.copilot.adapters.ml_adapter import get_ml_tool
from app.copilot.adapters.rag_adapter import get_rag_tool
from app.copilot.adapters.scenario_adapter import get_scenario_tool
from app.copilot.schemas.copilot import CopilotQueryRequest, CopilotQueryResponse
from app.copilot.services.copilot_service import CopilotService
from app.copilot.services.tool_router import ToolRouter

router = APIRouter(prefix="/agentic/copilot", tags=["Copilot"])


def get_copilot_service(
    state_provider: InvestigationStateProvider = Depends(get_investigation_state_provider),
) -> CopilotService:
    """
    Dependency wiring for the Copilot service.
    Assembles all tool adapters and creates the copilot service.
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
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user),
) -> CopilotQueryResponse:
    """
    Ask the AI Copilot a question about an investigation.
    
    The copilot uses existing investigation state and can access:
    - RAG tool for policy/guideline questions
    - ML tool for risk predictions
    - Database tools for provider/claim history
    - Scenario tools for comparative analysis
    """
    return copilot_service.answer_question(request)
