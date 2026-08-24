"""
tools.database
===============

Tools that expose database read/write capabilities to agents.

Contains:
- query_tool.py       : Tool-facing interface for database queries.
- database_service.py : Underlying database connection/query logic.

Agents should only ever call functions/classes from query_tool.py,
never database_service.py directly.
"""
