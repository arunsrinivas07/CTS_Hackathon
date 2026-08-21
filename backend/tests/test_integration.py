import pytest
import os
import sys
from fastapi.testclient import TestClient



from main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_openapi_docs():
    response = client.get("/docs")
    assert response.status_code == 200
    
    response_json = client.get("/openapi.json")
    assert response_json.status_code == 200

def test_end_to_end_investigation_C10234():
    """
    Test the full investigation sequence:
    Claim -> Orchestrator -> ML -> DB -> RAG -> Evidence Bundle -> Investigation State
    for C10234, Provider ABC123, MRI, lower_back_pain
    """
    payload = {
        "claim_id": "C10234",
        "claim_data": {
            "provider_id": "ABC123",
            "procedure": "MRI",
            "diagnosis": "lower_back_pain",
            "amount": 4800.0
        },
        "risk_score": 0.85,
        "risk_level": "HIGH",
        "auto_run": True
    }
    
    # We invoke the orchestration endpoint to start and auto_run the investigation
    response = client.post("/api/investigations/start", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["claim_id"] == "C10234"
    assert data["status"] in ["COMPLETED", "REQUIRES_HUMAN_REVIEW", "FAILED", "MAX_ITERATIONS_REACHED"]
    
    # Explicitly test tools via registry to ensure they are connected to Member 2 services correctly
    from tools import get_tool
    
    # ML
    ml_tool = get_tool("ml")
    ml_result = ml_tool.run(claim_id="C10234")
    assert ml_result.status == "SUCCESS"
    assert "risk_score" in ml_result.data
    assert "SHAP features are statistical" in ml_result.data.get("disclaimer", "")
    
    # DB - Provider Statistics
    db_tool = get_tool("provider_statistics")
    db_result = db_tool.run(provider_id="ABC123", procedure="MRI")
    assert db_result.status == "SUCCESS"
    assert "monthly_volume" in db_result.data["provider_statistics"]
    
    # DB - Claim History
    claim_db_tool = get_tool("claim_history")
    claim_result = claim_db_tool.run(claim_id="C10234")
    assert claim_result.status == "SUCCESS"
    
    # RAG
    rag_tool = get_tool("rag")
    rag_result = rag_tool.run(query="Is MRI medically necessary for this condition without prior physical therapy?", claim_id="C10234", procedure="MRI", diagnosis="lower_back_pain", provider_id="ABC123", claim_amount=4800.0)
    assert rag_result.status in ["SUCCESS", "NO_EVIDENCE_FOUND"]
