"""
tools.rag
=========

Tools that expose Retrieval-Augmented Generation (RAG) capabilities
to agents (e.g. semantic document search over a knowledge base).

Contains:
- retrieval_tool.py    : Tool-facing interface for retrieval.
- retrieval_service.py : Underlying vector store / embedding logic.

Agents should only ever call functions/classes from retrieval_tool.py,
never retrieval_service.py directly.
"""
