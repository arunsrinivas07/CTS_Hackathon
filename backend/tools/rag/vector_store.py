"""
vector_store.py
===============

Isolated Vector Store Abstraction Layer for RAG Retrieval.
Implements the ChromaDB-compatible interface while protecting against platform/C-extension crashes.
Supports semantic similarity search, metadata filtering ($eq, $and), persistence, and chunk retrieval.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

from tools.config import settings
from tools.rag.embeddings import get_embedding_function
from tools.utils.tool_helpers import logger


class VectorStore:
    """
    Isolated Vector Store implementation matching ChromaDB collection semantics.
    Supports cosine similarity vector search, metadata filtering, and disk persistence.
    """

    def __init__(
        self,
        collection_name: str = "cms_knowledge_base",
        persist_directory: Optional[str] = None,
        embedding_function: Any = None,
    ) -> None:
        self.collection_name = collection_name
        self.persist_directory = Path(persist_directory or settings.chroma_persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.embedding_function = embedding_function or get_embedding_function()

        self._store_file = self.persist_directory / f"{collection_name}_store.json"
        self._ids: List[str] = []
        self._documents: List[str] = []
        self._metadatas: List[Dict[str, Any]] = []
        self._embeddings: List[List[float]] = []

        self._load()

    def _load(self) -> None:
        """Load persisted vectors and records from disk."""
        if self._store_file.exists():
            try:
                with open(self._store_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._ids = data.get("ids", [])
                self._documents = data.get("documents", [])
                self._metadatas = data.get("metadatas", [])
                self._embeddings = data.get("embeddings", [])
                logger.debug(
                    "Loaded %d vectors from persistent store %s",
                    len(self._ids),
                    self._store_file,
                )
            except Exception as e:
                logger.warning("Failed to load vector store from %s: %s", self._store_file, e)

    def _save(self) -> None:
        """Persist vectors and records to disk."""
        try:
            # Ensure embeddings are standard python float lists
            clean_embeddings = [
                emb.tolist() if isinstance(emb, np.ndarray) else [float(x) for x in emb]
                for emb in self._embeddings
            ]
            data = {
                "collection_name": self.collection_name,
                "ids": self._ids,
                "documents": self._documents,
                "metadatas": self._metadatas,
                "embeddings": clean_embeddings,
            }
            with open(self._store_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("Failed to persist vector store to %s: %s", self._store_file, e)

    def count(self) -> int:
        """Return total number of indexed vectors."""
        return len(self._ids)

    def upsert(
        self,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        embeddings: Optional[List[List[float]]] = None,
    ) -> None:
        """Upsert documents and embeddings into the collection."""
        if metadatas is None:
            metadatas = [{} for _ in ids]
        if embeddings is None:
            embeddings = self.embedding_function(documents)

        for doc_id, doc, meta, emb in zip(ids, documents, metadatas, embeddings):
            emb_list = emb.tolist() if isinstance(emb, np.ndarray) else [float(x) for x in emb]
            if doc_id in self._ids:
                idx = self._ids.index(doc_id)
                self._documents[idx] = doc
                self._metadatas[idx] = meta
                self._embeddings[idx] = emb_list
            else:
                self._ids.append(doc_id)
                self._documents.append(doc)
                self._metadatas.append(meta)
                self._embeddings.append(emb_list)

        self._save()

    def query(
        self,
        query_texts: Optional[List[str]] = None,
        query_embeddings: Optional[List[List[float]]] = None,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        include: Optional[List[str]] = None,
    ) -> Dict[str, List[List[Any]]]:
        """
        Query collection using cosine similarity and metadata filtering.
        Returns ChromaDB-compatible dictionary structure:
        {"ids": [[...]], "documents": [[...]], "metadatas": [[...]], "distances": [[...]]}
        """
        if not self._ids:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

        if query_embeddings is None and query_texts is not None:
            query_embeddings = self.embedding_function(query_texts)

        if query_embeddings is None or not query_embeddings:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

        q_vec = np.array(query_embeddings[0], dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm > 0:
            q_vec = q_vec / q_norm

        store_matrix = np.array(self._embeddings, dtype=np.float32)

        # Compute cosine similarities
        similarities = np.dot(store_matrix, q_vec)

        # Filter candidates based on where clause
        filtered_indices = []
        for idx in range(len(self._ids)):
            meta = self._metadatas[idx]
            if self._matches_filter(meta, where):
                filtered_indices.append(idx)

        if not filtered_indices:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

        # Sort filtered candidates by similarity descending
        filtered_indices.sort(key=lambda i: similarities[i], reverse=True)
        top_indices = filtered_indices[:n_results]

        res_ids = [self._ids[i] for i in top_indices]
        res_docs = [self._documents[i] for i in top_indices]
        res_metas = [self._metadatas[i] for i in top_indices]
        # Distance = 1.0 - similarity (bounded in [0, 2])
        res_dists = [float(max(0.0, 1.0 - similarities[i])) for i in top_indices]

        return {
            "ids": [res_ids],
            "documents": [res_docs],
            "metadatas": [res_metas],
            "distances": [res_dists],
        }

    def _matches_filter(self, meta: Dict[str, Any], where: Optional[Dict[str, Any]]) -> bool:
        """Check if metadata matches where filter clause."""
        if not where:
            return True

        # Handle $and condition
        if "$and" in where:
            return all(self._matches_filter(meta, clause) for clause in where["$and"])

        # Handle $or condition
        if "$or" in where:
            return any(self._matches_filter(meta, clause) for clause in where["$or"])

        # Handle direct key comparisons
        for key, condition in where.items():
            meta_val = meta.get(key)
            if isinstance(condition, dict):
                if "$eq" in condition and meta_val != condition["$eq"]:
                    return False
                if "$ne" in condition and meta_val == condition["$ne"]:
                    return False
                if "$in" in condition and meta_val not in condition["$in"]:
                    return False
            else:
                if meta_val != condition:
                    return False

        return True


def get_vector_store(
    collection_name: str = "cms_knowledge_base",
    persist_directory: Optional[str] = None,
) -> VectorStore:
    """Factory function returning the isolated VectorStore instance."""
    return VectorStore(
        collection_name=collection_name,
        persist_directory=persist_directory,
    )
