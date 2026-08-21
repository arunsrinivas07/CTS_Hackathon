"""
hybrid_retriever.py
===================

Hybrid Retrieval Engine combining:
1. Vector Semantic Retrieval (ChromaDB)
2. Keyword / BM25-style Retrieval (RankBM25)
3. Metadata Filtering (procedure, document_type, policy_type, jurisdiction)
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from rank_bm25 import BM25Okapi

from utils.tool_helpers import logger


def tokenize(text: str) -> List[str]:
    """Simple alphanumeric tokenizer for BM25."""
    return re.findall(r"\b\w+\b", text.lower())


class HybridRetriever:
    """
    Combines vector search and BM25 search over the CMS knowledge base.
    """

    def __init__(self, chroma_collection: Any, all_documents: Optional[List[Dict[str, Any]]] = None) -> None:
        self.collection = chroma_collection
        self.documents: List[Dict[str, Any]] = all_documents or []
        self._corpus_tokens: List[List[str]] = []
        self._bm25: Optional[BM25Okapi] = None
        if self.documents:
            self._build_bm25_index()

    def update_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Update internal corpus and rebuild BM25 index."""
        self.documents = documents
        self._build_bm25_index()

    def _build_bm25_index(self) -> None:
        """Construct the BM25 index over all document texts."""
        self._corpus_tokens = [tokenize(doc.get("text", "")) for doc in self.documents]
        if self._corpus_tokens and any(len(t) > 0 for t in self._corpus_tokens):
            self._bm25 = BM25Okapi(self._corpus_tokens)
        else:
            self._bm25 = None

    def search(
        self,
        queries: List[str],
        top_k: int = 10,
        metadata_filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid vector + BM25 retrieval across multiple generated queries.
        """
        candidates_by_id: Dict[str, Dict[str, Any]] = {}

        # 1. Vector Search via ChromaDB
        for query in queries:
            try:
                where_clause = None
                if metadata_filters:
                    # Clean empty filters
                    active_filters = {k: v for k, v in metadata_filters.items() if v}
                    if len(active_filters) == 1:
                        k, v = next(iter(active_filters.items()))
                        where_clause = {k: {"$eq": v}}
                    elif len(active_filters) > 1:
                        where_clause = {"$and": [{k: {"$eq": v}} for k, v in active_filters.items()]}

                vector_results = self.collection.query(
                    query_texts=[query],
                    n_results=min(top_k, max(1, self.collection.count())),
                    where=where_clause,
                    include=["documents", "metadatas", "distances"],
                )

                if vector_results and "ids" in vector_results and vector_results["ids"]:
                    ids = vector_results["ids"][0]
                    docs = vector_results["documents"][0] if "documents" in vector_results else []
                    metas = vector_results["metadatas"][0] if "metadatas" in vector_results else []
                    distances = vector_results["distances"][0] if "distances" in vector_results else []

                    for doc_id, text, meta, dist in zip(ids, docs, metas, distances):
                        # Convert Chroma distance to similarity score in [0, 1]
                        sim_score = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
                        if doc_id not in candidates_by_id:
                            candidates_by_id[doc_id] = {
                                "id": doc_id,
                                "text": text,
                                "metadata": meta or {},
                                "vector_score": sim_score,
                                "bm25_score": 0.0,
                            }
                        else:
                            candidates_by_id[doc_id]["vector_score"] = max(
                                candidates_by_id[doc_id]["vector_score"], sim_score
                            )
            except Exception as e:
                logger.warning("Vector search query '%s' encountered error: %s", query, e)

        # 2. BM25 Keyword Search
        if self._bm25 and self.documents:
            for query in queries:
                q_tokens = tokenize(query)
                if not q_tokens:
                    continue
                bm25_scores = self._bm25.get_scores(q_tokens)
                max_bm25 = max(bm25_scores) if len(bm25_scores) > 0 and max(bm25_scores) > 0 else 1.0

                for idx, score in enumerate(bm25_scores):
                    if score <= 0:
                        continue
                    doc = self.documents[idx]
                    doc_id = doc.get("id", str(idx))
                    meta = doc.get("metadata", {})

                    # Apply metadata filtering if specified
                    if metadata_filters:
                        match = True
                        for fk, fv in metadata_filters.items():
                            if fv and meta.get(fk) != fv:
                                match = False
                                break
                        if not match:
                            continue

                    norm_bm25 = min(1.0, score / max_bm25)
                    if doc_id not in candidates_by_id:
                        candidates_by_id[doc_id] = {
                            "id": doc_id,
                            "text": doc.get("text", ""),
                            "metadata": meta,
                            "vector_score": 0.0,
                            "bm25_score": norm_bm25,
                        }
                    else:
                        candidates_by_id[doc_id]["bm25_score"] = max(
                            candidates_by_id[doc_id]["bm25_score"], norm_bm25
                        )

        # 3. Score Combination & Ranking
        results: List[Dict[str, Any]] = []
        for doc_id, item in candidates_by_id.items():
            vec_s = item["vector_score"]
            bm25_s = item["bm25_score"]
            # Weighted hybrid score
            if vec_s > 0 and bm25_s > 0:
                combined_score = 0.60 * vec_s + 0.40 * bm25_s
            elif vec_s > 0:
                combined_score = vec_s * 0.85
            else:
                combined_score = bm25_s * 0.75

            item["retrieval_score"] = round(combined_score, 4)
            results.append(item)

        # Sort descending by retrieval score
        results.sort(key=lambda x: x["retrieval_score"], reverse=True)
        return results[:top_k]
