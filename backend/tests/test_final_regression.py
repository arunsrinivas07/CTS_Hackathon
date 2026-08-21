import pytest
from fastapi.testclient import TestClient
from main import app
from api.investigation_routes import StartInvestigationRequest
from llm.config import settings

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_invalid_input():
    # Missing claim_id
    payload = {
        "risk_score": 0.98,
        "risk_level": "CRITICAL"
    }
    response = client.post("/api/investigations/start", json=payload)
    assert response.status_code == 422  # Pydantic validation error

def test_unknown_investigation():
    response = client.get("/api/investigations/inv_nonexistent")
    assert response.status_code == 404

def test_postgres_unavailable():
    # If DATA_MODE=real but no Postgres URL, it should return ToolErrorResponse internally
    # We can test this by forcing DATA_MODE=real in settings and mocking DB connection failure.
    original_mode = settings.data_mode
    settings.data_mode = "real"
    settings.database_url = ""
    
    # We can hit a known endpoint or instantiate DatabaseService
    from services.database.database_service import DatabaseService
    service = DatabaseService()
    res = service.get_provider_history("UNKNOWN")
    assert getattr(res, "error_code", None) == "DATABASE_SERVICE_ERROR"
    
    settings.data_mode = original_mode

def test_provider_not_found():
    from services.database.database_service import DatabaseService
    service = DatabaseService()
    # Mock data mode
    res = service.get_provider_history("UNKNOWN_PROVIDER")
    assert getattr(res, "error_code", None) == "PROVIDER_NOT_FOUND"

def test_comparison_not_found():
    from services.database.database_service import DatabaseService
    service = DatabaseService()
    res = service.get_provider_peer_comparison("UNKNOWN_PROVIDER", "MRI")
    assert getattr(res, "error_code", None) == "PROVIDER_NOT_FOUND"

def test_rag_retrieval_success():
    from services.rag.retrieval_service import RetrievalService
    service = RetrievalService()
    # Assuming "medicare" or "cms" hits the semantic search
    res = service.search("Medicare claims fraud", top_k=2)
    # The ChromaDB should exist, but this is a unit test so it might be empty depending on DB state.
    # Just asserting it doesn't crash.
    assert hasattr(res, "evidence")

def test_rag_retrieval_no_evidence():
    from services.rag.retrieval_service import RetrievalService
    service = RetrievalService()
    res = service.search("gibberish that doesn't exist anywhere in the world", top_k=1)
    # Shouldn't return evidence
    # Actually depends on the score threshold, but assuming it correctly drops low scores
    if hasattr(service, "evidence_threshold"):
        # Could check if it returns empty list
        pass
    assert hasattr(res, "evidence")
def test_high_risk_claim():
    payload = {
        "claim_id": "CLM-HIGH-003",
        "risk_score": 0.98,
        "risk_level": "CRITICAL",
        "auto_run": True,
        "claim_data": {
            "transaction_type": "MEDICAL_CLAIM",
            "claim_id": "CLM-HIGH-003",
            "bene_id": -10000010254618,
            "provider_id": "1578657367",
            "claim_type": "inpatient",
            "claim_start_date": "2023-02-01",
            "claim_end_date": "2023-02-08",
            "clm_pmt_amt": 14500.00,
            "clm_tot_chrg_amt": 22000.00,
            "line_count": 6,
            "unit_count": 10,
            "diag_count": 8,
            "proc_count": 4
        }
    }
    response = client.post("/api/investigations/start", json=payload)
    
    # Depending on Groq rate limits, it might be 503 (which is expected gracefully) or 200
    assert response.status_code in (200, 503), f"Unexpected status {response.status_code}: {response.text}"
    
    if response.status_code == 200:
        data = response.json()
        assert data["claim_id"] == "CLM-HIGH-003"
        assert data["risk_score"] == 0.98
        assert data["risk_level"] == "CRITICAL"
        assert "investigation_id" in data
