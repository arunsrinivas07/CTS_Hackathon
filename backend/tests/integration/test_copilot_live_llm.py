import os
import sys
import pytest
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "investigator-copilot"))

from fastapi.testclient import TestClient
from app.main import app as copilot_app
from schemas.investigation import InvestigationState
from app.api.copilot import get_copilot_service
from app.services.copilot_service import CopilotService
from app.services.tool_router import ToolRouter


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_LLM_TESTS", "false").lower() != "true",
    reason="RUN_LIVE_LLM_TESTS not set to true"
)


@pytest.fixture
def mock_state():
    return InvestigationState(
        investigation_id="INV-LIVE",
        claim_id="C999",
        provider_name="Dr. Real",
        procedure="MRI",
        claim_amount=5000,
        risk_score=0.92,
        risk_factors=[],
        shap_factors=[],
        evidence=[],
        counter_evidence=[],
        evidence_gaps=[],
        citations=[],
        investigation_trace=[]
    )


@pytest.fixture
def live_client(mock_state):
    class MockStateProvider:
        def get_state(self, inv_id):
            return mock_state if inv_id == "INV-LIVE" else None
        def save_state(self, state):
            pass

    def override_get_copilot_service():
        from app.adapters.database_adapter import get_claim_db_tool, get_provider_db_tool
        from app.adapters.ml_adapter import get_ml_tool
        from app.adapters.rag_adapter import get_rag_tool
        from app.adapters.scenario_adapter import get_scenario_tool

        router = ToolRouter(
            rag_tool=get_rag_tool(),
            ml_tool=get_ml_tool(),
            scenario_tool=get_scenario_tool(),
            provider_db_tool=get_provider_db_tool(),
            claim_db_tool=get_claim_db_tool(),
        )
        return CopilotService(state_provider=MockStateProvider(), tool_router=router)

    copilot_app.dependency_overrides[get_copilot_service] = override_get_copilot_service
    client = TestClient(copilot_app)
    yield client
    copilot_app.dependency_overrides.clear()


def test_live_llm_risk_explanation(live_client):
    resp = live_client.post("/api/copilot/query", json={
        "investigation_id": "INV-LIVE",
        "question": "Why is this claim high risk?"
    })
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["question_type"] == "risk_explanation"
    assert "answer" in data
    assert len(data["answer"]) > 10
