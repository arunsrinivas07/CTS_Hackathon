FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend /app/backend
COPY knowledge_base /app/knowledge_base

# Environment variables
ENV PYTHONPATH=/app/backend
ENV APP_ENV=production
ENV HOST=0.0.0.0
ENV PORT=8000

# Expose API port
EXPOSE 8000

# Run Uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
