"""
query_generator.py
==================

Generates a targeted, optimized search query for RAG from the Agent's natural language question.
Uses Primary LLM (Groq) -> Deterministic Query Builder.
"""

from __future__ import annotations

import re
from typing import List, Optional
from app.services.agentic.rag.llm_provider import BaseLLMProvider, FallbackLLMProvider
from app.schemas.agentic.tool import ClaimContext
from app.utils.tool_helpers import logger


class QueryGenerator:
    """
    Transforms natural language investigation questions and structured claim context
    into targeted CMS policy search queries.
    """

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None) -> None:
        self.llm = llm_provider or FallbackLLMProvider()

    def generate_queries(
        self, question: str, claim_context: Optional[ClaimContext] = None
    ) -> List[str]:
        """
        Generate a list of retrieval queries tailored to the claim and question.
        """
        queries: List[str] = []

        # Try LLM generation first
        system_prompt = (
            "You are a medical claims retrieval assistant. Given an investigation question "
            "and claim context, output 3 to 4 concise, high-yield search queries to retrieve "
            "relevant CMS Medicare coverage policies, LCDs, NCDs, and medical necessity rules. "
            "Output one query per line without bullet points or numbering."
        )

        prompt = f"Question: {question}\n"
        if claim_context:
            if claim_context.procedure:
                prompt += f"Procedure: {claim_context.procedure}\n"
            if claim_context.diagnosis:
                prompt += f"Diagnosis: {claim_context.diagnosis}\n"
            if claim_context.claim_id:
                prompt += f"Claim ID: {claim_context.claim_id}\n"

        llm_response = self.llm.generate(prompt=prompt, system_prompt=system_prompt)

        if llm_response:
            for line in llm_response.strip().split("\n"):
                clean = re.sub(r"^[\d\.\-\*\s]+", "", line).strip()
                if clean and len(clean) > 5 and clean not in queries:
                    queries.append(clean)

        # If LLM didn't return valid queries, use deterministic fallback
        if not queries:
            queries = self._deterministic_queries(question, claim_context)

        # Ensure base question keywords are represented
        if question not in queries:
            queries.insert(0, question)

        return queries[:5]

    def _deterministic_queries(
        self, question: str, claim_context: Optional[ClaimContext]
    ) -> List[str]:
        """Deterministic query builder based on procedure, diagnosis, and policy keywords."""
        proc = ""
        diag = ""

        if claim_context:
            if claim_context.procedure:
                proc = claim_context.procedure.replace("_", " ").strip()
            if claim_context.diagnosis:
                diag = claim_context.diagnosis.replace("_", " ").strip()

        # Build specific queries
        candidates = []

        if proc and diag:
            candidates.append(f"{proc} medical necessity {diag}")
            if "mri" in proc.lower() or "spine" in diag.lower() or "back" in diag.lower():
                candidates.append(f"lumbar {proc} clinical indications")
            candidates.append(f"CMS {proc} coverage medical necessity {diag}")
            candidates.append(f"{proc} coverage requirements")
            candidates.append(f"Medicare LCD NCD {proc} {diag}")
        elif proc:
            candidates.append(f"CMS {proc} medical necessity guidelines")
            candidates.append(f"{proc} coverage requirements Medicare")
        elif diag:
            candidates.append(f"CMS coverage guidelines for {diag}")
            candidates.append(f"medical necessity criteria for {diag}")
        else:
            candidates.append(question)
            candidates.append("CMS Medicare medical necessity coverage guidelines")

        # Deduplicate while preserving order
        unique_queries = []
        for q in candidates:
            if q not in unique_queries:
                unique_queries.append(q)

        return unique_queries
