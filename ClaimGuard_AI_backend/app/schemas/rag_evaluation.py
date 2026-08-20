from datetime import datetime
from typing import Optional
from .common import SchemaBase

class RAGEvaluationCreate(SchemaBase):
    query: str
    expected_answer: Optional[str] = None
    generated_answer: str
    retrieved_documents: list[dict] = []
    retrieval_score: Optional[float] = None
    answer_score: Optional[float] = None

class RAGEvaluationResponse(RAGEvaluationCreate):
    id: int
    created_at: datetime
