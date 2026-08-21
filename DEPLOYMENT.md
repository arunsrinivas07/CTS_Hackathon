# ClaimGuard Deployment Guide

## Architecture

ClaimGuard operates as a FastAPI REST backend utilizing a purely Agentic architecture, integrated with Groq LLM inference and a ChromaDB-backed RAG (Retrieval-Augmented Generation) pipeline. 

## Prerequisites

- Python 3.11+
- Groq API Key (`GROQ_API_KEY`)
- Docker (optional)

## Environment Variables

Copy `.env.example` to `.env` and set the following:

```ini
APP_ENV=production
DATA_MODE=mock  # Set to 'real' to use PostgreSQL
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile
```

## Running Locally

1. Install dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. Start the Uvicorn server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

## Running via Docker

1. Build the image:
   ```bash
   docker build -t claimguard .
   ```

2. Run the container:
   ```bash
   docker run -p 8000:8000 --env-file .env claimguard
   ```

## Endpoints

- `GET /health` : Health check
- `POST /api/investigations/start` : Start an agentic investigation
- `GET /api/investigations/{investigation_id}` : Get investigation status

## Production Notes

- **Concurrency**: The agentic orchestrator loop is highly compute-intensive. In production, consider deploying on a robust ASGI server (e.g. Gunicorn with Uvicorn workers).
- **RAG Knowledge Base**: The knowledge base is loaded from `knowledge_base/cms`. During the first run, the system will embed and ingest this into `chroma_db`. Ensure the volume is persistent.
- **LLM Provider**: The system is strictly configured for Groq. Ensure rate limits on the Groq tier can handle parallel LLM iterative loops.
