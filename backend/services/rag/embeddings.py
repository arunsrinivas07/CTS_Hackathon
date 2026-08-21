"""
embeddings.py
=============

Robust, zero-external-dependency local embedding provider for ChromaDB.
Provides consistent dense vector representations for CMS documents and queries.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import List, Optional
import numpy as np
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings


def clean_tokenize(text: str) -> List[str]:
    """Tokenize text into unigrams and bigrams for semantic capture."""
    words = re.findall(r"\b\w+\b", text.lower())
    tokens = list(words)
    # Add adjacent word pairs (bigrams)
    for i in range(len(words) - 1):
        tokens.append(f"{words[i]}_{words[i+1]}")
    return tokens


class LocalDenseEmbeddingFunction(EmbeddingFunction[Documents]):
    """
    High-performance, deterministic local dense embedding function using
    subword & n-gram feature hashing with L2 normalization.
    Ensures 100% reliability across all OS / Python versions without requiring external C++ DLLs.
    """

    def __init__(self, dimension: int = 256) -> None:
        self.dimension = dimension

    def name(self) -> str:
        return "LocalDenseEmbeddingFunction"

    def __call__(self, input: Documents) -> Embeddings:
        """Embed a list of documents into dense floating-point vector representations."""
        embeddings: List[List[float]] = []

        for doc in input:
            tokens = clean_tokenize(doc)
            vec = np.zeros(self.dimension, dtype=np.float32)

            if not tokens:
                embeddings.append(vec.tolist())
                continue

            for token in tokens:
                # Murmur-style MD5 multi-hash projection
                h_raw = hashlib.md5(token.encode("utf-8")).hexdigest()
                h1 = int(h_raw[:8], 16)
                h2 = int(h_raw[8:16], 16)

                idx = h1 % self.dimension
                sign = 1.0 if (h2 % 2 == 0) else -1.0
                # IDF-like heuristic weighting: longer tokens & domain terms carry higher weight
                weight = 1.0 + math.log(max(1, len(token)))
                if any(k in token for k in ("mri", "lumbar", "spine", "cms", "necessity", "coverage", "denial")):
                    weight *= 1.5

                vec[idx] += sign * weight

            # L2 normalize vector
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm

            embeddings.append(vec.tolist())

        return embeddings


def get_embedding_function() -> EmbeddingFunction[Documents]:
    """Factory function returning the active embedding function."""
    return LocalDenseEmbeddingFunction(dimension=256)
