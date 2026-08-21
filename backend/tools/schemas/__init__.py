"""
tools.schemas
=============

Structured input/output definitions (schemas) shared across all tools.

Contains:
- tool_schemas.py : Pydantic/dataclass-style models describing the
  request and response shapes for each tool category (ML, RAG,
  database, external API).

Schemas are the contract between agents and tools: agents build
requests matching these schemas, and tools return responses matching
these schemas. Keeping schemas centralized here (rather than scattered
per-tool) makes it easy for a team to see the full I/O surface at a
glance.
"""
