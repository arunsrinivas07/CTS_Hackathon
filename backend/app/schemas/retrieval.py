from typing import Optional
from .common import SchemaBase

class RetrievalRequest(SchemaBase):
    query: str
    top_k: int = 5
    filters: Optional[dict] = None

class RetrievalResult(SchemaBase):
    document_id: int
    chunk_id: Optional[str] = None
    content: str
    score: float
    metadata: Optional[dict] = None

class RetrievalResponse(SchemaBase):
    query: str
    results: list[RetrievalResult]
