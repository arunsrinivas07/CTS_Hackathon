"""
FastAPI application entrypoint for the Investigator Copilot (Member 3).

Run with:
    uvicorn app.main:app --reload --port 8000

This service is standalone for now and depends only on mock adapters
(see app/adapters/*). It is designed to later plug into the main claims
investigation project without changes to its internal logic — only the
adapter factory functions need to be repointed at real implementations.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.api.copilot import router as copilot_router

app = FastAPI(
    title="Investigator Copilot API",
    description=(
        "AI assistant for human claims investigators. Answers questions grounded in an "
        "existing InvestigationState, calling approved RAG/ML/DB tools only when necessary."
    ),
    version="0.1.0",
)

app.include_router(copilot_router)


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}
