from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import engine, Base
import app.models  # Register all models for SQLAlchemy

# Import all routers
from app.routers import (
    auth,
    users,
    roles,
    patients,
    providers,
    claims,
    investigations,
    risk,
    anomalies,
    audit,
    notifications,
    workflow_tasks,
    reports,
    decisions,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database schema is ready
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="ClaimGuard AI - Fraud, Waste, and Abuse (FWA) Healthcare Claims Detection Backend",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?:\/\/.*$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers under /api/v1 prefix
API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(roles.router, prefix=API_PREFIX)
app.include_router(patients.router, prefix=API_PREFIX)
app.include_router(providers.router, prefix=API_PREFIX)
app.include_router(claims.router, prefix=API_PREFIX)
app.include_router(investigations.router, prefix=API_PREFIX)
app.include_router(risk.router, prefix=API_PREFIX)
app.include_router(anomalies.router, prefix=API_PREFIX)
app.include_router(audit.router, prefix=API_PREFIX)
app.include_router(notifications.router, prefix=API_PREFIX)
app.include_router(workflow_tasks.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)
app.include_router(decisions.router, prefix=API_PREFIX)


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/", tags=["Root"])
def root():
    return {
        "message": f"Welcome to {settings.app_name} API",
        "docs": "/docs",
        "health": "/health",
    }
