import os
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
    audit,
    notifications,
    workflow_tasks,
    reports,
    decisions,
    ml,
    ml_outputs,
    documentation_requests,
    agentic_investigations,
    copilot,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[STARTUP] Starting application startup...")
    
    # Ensure database schema is ready
    print("[STARTUP] Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("[STARTUP] Database tables created successfully.")
    except Exception as e:
        print(f"[STARTUP ERROR] Failed to create tables: {e}")
    
    # Auto-seed initial data
    print("[STARTUP] Seeding database...")
    try:
        from app.seed import seed_database
        seed_database()
        print("[STARTUP] Database seeded successfully.")
    except Exception as e:
        print(f"[SEED] Warning: {e}")
    
    # Initialize agent knowledge base in background (non-blocking)
    print("[STARTUP] Starting knowledge base ingestion in background...")
    async def ingest_kb_background():
        try:
            import asyncio
            from app.services.agentic.rag.ingest import ingest_cms_knowledge_base
            # Run blocking function in thread pool to avoid blocking event loop
            await asyncio.to_thread(ingest_cms_knowledge_base)
            print("[AGENT KB] Knowledge base ingestion completed successfully.")
        except Exception as e:
            print(f"[AGENT KB] Warning: {e}")
    
    # Start background task but don't wait for it
    import asyncio
    asyncio.create_task(ingest_kb_background())
    print("[STARTUP] Knowledge base ingestion started in background (non-blocking).")
    
    # Initialize agent tools
    print("[STARTUP] Registering agent tools...")
    try:
        import app.tools  # Register tools
        print("[STARTUP] Agent tools registered successfully.")
    except Exception as e:
        print(f"[AGENT TOOLS] Warning: {e}")
    
    print("[STARTUP] Application startup complete!")
    yield
    print("[SHUTDOWN] Application shutdown complete.")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="ClaimGuard AI - Fraud, Waste, and Abuse (FWA) Healthcare Claims Detection Backend",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=r".*",
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
app.include_router(audit.router, prefix=API_PREFIX)
app.include_router(notifications.router, prefix=API_PREFIX)
app.include_router(workflow_tasks.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)
app.include_router(decisions.router, prefix=API_PREFIX)
app.include_router(ml.router, prefix=API_PREFIX)
app.include_router(ml_outputs.router, prefix=API_PREFIX)
app.include_router(documentation_requests.router, prefix=API_PREFIX)
# Agentic routes
app.include_router(agentic_investigations.router, prefix=API_PREFIX)
app.include_router(copilot.router, prefix=API_PREFIX)


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
