"""
retrieval_service.py
====================

SERVICE layer for RAG Retrieval.
Encapsulates isolated Vector Store, query generation, hybrid retrieval,
evidence evaluation, citation generation, and grounded synthesis.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from llm.config import settings
from services.rag.citation_builder import CitationBuilder
from services.rag.embeddings import get_embedding_function
from services.rag.evidence_evaluator import EvidenceEvaluator
from services.rag.hybrid_retriever import HybridRetriever
from services.rag.ingest import ingest_cms_knowledge_base, load_knowledge_base_documents
from services.rag.llm_provider import BaseLLMProvider, FallbackLLMProvider
from services.rag.query_generator import QueryGenerator
from services.rag.vector_store import get_vector_store
from schemas.tool import (
    ClaimContext,
    RAGSearchResponse,
    ToolErrorResponse,
)
from utils.tool_helpers import format_tool_error, logger, timed


class RetrievalService:
    """
    Coordinates the complete RAG pipeline:
    Query Generation -> Hybrid Retrieval -> Evaluation -> Citation -> Synthesis
    """

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        llm_provider: Optional[BaseLLMProvider] = None,
        threshold: Optional[float] = None,
    ) -> None:
        self.persist_directory = persist_directory or settings.chroma_persist_directory
        os.makedirs(self.persist_directory, exist_ok=True)

        self.llm = llm_provider or FallbackLLMProvider()
        self.query_generator = QueryGenerator(llm_provider=self.llm)
        self.evaluator = EvidenceEvaluator(threshold=threshold)

        # Initialize isolated Vector Store
        self._vector_store = get_vector_store(
            collection_name="cms_knowledge_base",
            persist_directory=self.persist_directory,
        )

        # Auto-ingest if collection is empty
        if self._vector_store.count() == 0:
            logger.info("Vector Store is empty. Auto-ingesting CMS knowledge base...")
            ingest_cms_knowledge_base(persist_directory=self.persist_directory)

        # Load indexed corpus for BM25
        self._corpus = self._load_corpus()
        self.hybrid_retriever = HybridRetriever(
            chroma_collection=self._vector_store,
            all_documents=self._corpus,
        )

    def _load_corpus(self) -> List[Dict[str, Any]]:
        """Load corpus from cache or directly from knowledge base files."""
        cache_file = Path(self.persist_directory) / "indexed_corpus.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Could not read corpus cache: %s", e)
        return load_knowledge_base_documents()

    @timed
    def search(
        self,
        question: str,
        claim_context: Optional[ClaimContext] = None,
        top_k: Optional[int] = None,
        metadata_filters: Optional[Dict[str, Any]] = None,
    ) -> RAGSearchResponse:
        """
        Execute the end-to-end RAG pipeline.
        """
        retrieval_k = top_k or settings.rag_top_k
        final_k = settings.rag_final_k

        # 1. Query Generation
        print("\n[RAG]\nSearching CMS knowledge base...")
        generated_queries = self.query_generator.generate_queries(
            question=question, claim_context=claim_context
        )

        # 2. Hybrid Retrieval (Vector + BM25 + Metadata Filters)
        candidates = self.hybrid_retriever.search(
            queries=generated_queries,
            top_k=retrieval_k,
            metadata_filters=metadata_filters,
        )

        # 3. Evidence Evaluation & Filtering
        (
            selected_candidates,
            confidence,
            sufficient,
            has_contradiction,
            contradictions,
            reason,
        ) = self.evaluator.evaluate_and_filter(
            candidates=candidates,
            question=question,
            claim_context=claim_context,
            final_k=final_k,
        )

        # 4. Citation Building
        citations = CitationBuilder.build_citations(selected_candidates)
        print(f"\n[RAG]\nEvidence retrieved: {len(citations)}")

        # 5. Grounded LLM Synthesis (if evidence is sufficient and LLM is available)
        synthesis = None
        if sufficient and citations and not has_contradiction:
            synthesis = self._synthesize_answer(question, citations, claim_context)

        return RAGSearchResponse(
            status="success",
            tool="rag_search",
            question=question,
            generated_queries=generated_queries,
            evidence=citations,
            confidence=confidence,
            sufficient=sufficient,
            has_contradiction=has_contradiction,
            contradictions=contradictions,
            reason=reason,
            synthesis=synthesis,
        )

    def _synthesize_answer(
        self,
        question: str,
        citations: List[Any],
        claim_context: Optional[ClaimContext],
    ) -> Optional[str]:
        """
        Synthesizes a strictly grounded answer based exclusively on retrieved evidence chunks.
        """
        evidence_snippets = "\n\n".join(
            f"[{idx+1}] Source: {c.source} | Document: {c.document} ({c.section})\n{c.text}"
            for idx, c in enumerate(citations[:3])
        )

        system_prompt = (
            "You are a clinical coverage policy expert assisting a fraud investigator. "
            "Synthesize a concise, factual answer to the investigator's question based EXCLUSIVELY "
            "on the provided CMS policy evidence snippets. Do NOT invent policies or assume facts not present. "
            "Cite the source document and section numbers in your explanation."
        )

        prompt = (
            f"Question: {question}\n\n"
            f"Retrieved CMS Evidence:\n{evidence_snippets}\n\n"
            f"Please synthesize the medical necessity coverage decision:"
        )

        return self.llm.generate(prompt=prompt, system_prompt=system_prompt)
