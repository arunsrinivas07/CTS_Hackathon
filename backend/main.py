import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "investigator-copilot"))
from app.api.copilot import router as copilot_router

import tools  # noqa: F401  -- populates TOOL_REGISTRY on import
from api.investigation_routes import router as investigation_router
from services.rag.ingest import ingest_cms_knowledge_base

logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Initializing Healthcare Claims Fraud Investigation Backend...")
    try:
        ingest_cms_knowledge_base()
    except Exception as exc:
        logging.warning(f"Knowledge base initialization warning: {exc}")
    yield
    logging.info("Shutting down Backend.")

app = FastAPI(title="Healthcare Claims Fraud Investigation System", lifespan=lifespan)
app.include_router(investigation_router)
app.include_router(copilot_router)

@app.get("/health")
def health():
    from llm.config import settings
    return {
        "status": "ok",
        "app_env": settings.app_env,
        "data_mode": settings.data_mode
    }
