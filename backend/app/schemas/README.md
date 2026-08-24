# ClaimGuard AI - Backend Schemas

This package contains the Pydantic schema layer for the ClaimGuard AI FastAPI backend.

## Structure

All Python schema modules live under `app/schemas/`.

The schemas are intentionally limited to the data-validation/API-contract layer.
They do not create database tables, API routes, or database connections.

## Install

```bash
pip install fastapi pydantic pydantic[email]
```

## Pydantic version

The code targets Pydantic v2 and uses `ConfigDict(from_attributes=True)`.

## Important

These are API/data schemas. Your SQLAlchemy models should live separately, for example:

app/models/

Do not import database sessions into these schema files.
