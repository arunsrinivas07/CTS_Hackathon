"""
API Integration Tests using FastAPI TestClient.

Verifies HTTP endpoints for Member 1 investigation lifecycle and trace retrieval.
"""
from __future__ import annotations

from fastapi.testclient import TestClient
from unittest.mock import patch

from main import app
from tests.conftest import ScriptedLLMClient

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_start_investigation_api():
    mock_llm = ScriptedLLMClient([{"objectives": [{"description": "obj", "related_risk_factors": []}]}])
    
    payload = {
        "claim_id": "C10234",
        "claim_data": {"provider_id": "ABC123", "procedure": "MRI"},
        "risk_score": 0.87,
        "risk_level": "HIGH",
        "shap_contributors": [{"feature": "procedure_frequency", "value": 0.34}],
        "detected_patterns": [{"name": "high_procedure_frequency"}],
        "auto_run": False,
    }

    with patch("agent.orchestrator.LLMClient", return_value=mock_llm):
        response = client.post("/api/investigations/start", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["claim_id"] == "C10234"
        assert data["status"] == "IN_PROGRESS"
        inv_id = data["investigation_id"]

        # Get state endpoint
        get_resp = client.get(f"/api/investigations/{inv_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["investigation_id"] == inv_id

        # Get trace endpoint
        trace_resp = client.get(f"/api/investigations/{inv_id}/trace")
        assert trace_resp.status_code == 200
        trace = trace_resp.json()
        assert trace["investigation_id"] == inv_id
        assert trace["claim_id"] == "C10234"
        assert "final_status" in trace
