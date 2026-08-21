"""
Adaptive Copilot service — coordinates the full Investigator Copilot flow with conversation memory, semantic intent routing, and dynamic context.
"""

from __future__ import annotations
import logging
import json
import uuid
import time
from typing import Optional, List, Dict, Any

from pydantic import BaseModel

from app.adapters.investigation_state_adapter import InvestigationStateProvider
from app.adapters.conversation_adapter import get_conversation_repository
from app.schemas.copilot import CopilotQueryRequest, CopilotQueryResponse, QuestionType
from schemas.investigation import InvestigationState
from app.services import guardrails
from app.services.evidence_resolver import resolve_from_state
from app.services.intent_router import classify_intent_semantic
from app.services.comparison_service import ComparisonService
from app.services.tool_router import ToolRouter

from llm.factory import get_llm_provider
from llm.errors import LLMProviderError, StructuredOutputError

logger = logging.getLogger("copilot.service")

class CopilotLLMOutput(BaseModel):
    answer: str
    explanation: Optional[str] = None
    caveat: Optional[str] = None
    focus: Optional[str] = None

class CopilotService:
    def __init__(self, state_provider: InvestigationStateProvider, tool_router: ToolRouter) -> None:
        self._state_provider = state_provider
        self._tool_router = tool_router
        self._conversation_repo = get_conversation_repository()
        self._comparison_service = ComparisonService(state_provider)

    def _build_context(self, state: InvestigationState, history: List[Dict], extra_ctx: dict) -> dict:
        """Constructs a rich CopilotContext."""
        ctx = {
            "investigation": {
                "investigation_id": state.investigation_id,
                "claim_id": state.claim_id,
                "status": state.status.value if state.status else "Unknown"
            },
            "risk": {
                "score": state.risk_score,
                "tier": state.risk_level,
                "model": "CareGuard ML"
            },
            "claim": state.claim_data,
            "evidence": [e.text for e in state.evidence],
            "evidence_gaps": [g.description for g in state.evidence_gaps],
            "conversation": history
        }
        ctx.update(extra_ctx)
        return ctx

    def _generate_grounded_answer(
        self, question: str, context: dict, caveat_override: Optional[str]
    ) -> CopilotLLMOutput:
        provider = get_llm_provider()
        system_prompt = (
            "You are an investigator copilot for healthcare claims fraud.\n"
            "You MUST use ONLY the supplied investigation context to answer the question.\n"
            "Do not invent evidence, citations, numbers, provider history, policies, or ML explanations.\n"
            "If information is missing, explicitly say it is unavailable.\n"
            "Never declare fraud as confirmed. Distinguish evidence from interpretation.\n"
            "Understand the context of 'why' or 'what' from the conversation history.\n"
            "If the user changes their focus (e.g. 'Focus on billing'), acknowledge it and update the focus field.\n"
            "Return ONLY the requested JSON schema fields (answer, explanation, caveat, focus) and do NOT repeat the entire input context in the answer."
        )
        user_prompt = (
            f"Context: {json.dumps(context)}\n\n"
            f"Question: {question}"
        )
        
        try:
            structured_data = provider.structured_generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=CopilotLLMOutput,
                max_tokens=1000
            )
            return structured_data
        except (LLMProviderError, StructuredOutputError):
            # Fallback
            return CopilotLLMOutput(
                answer="I encountered an error generating the response or the information is unavailable.",
                explanation=None,
                caveat=caveat_override
            )

    def answer_question(self, request: CopilotQueryRequest) -> CopilotQueryResponse:
        start_time = time.time()
        
        # 1. Manage Conversation Memory
        if request.conversation_id:
            conv = self._conversation_repo.get_conversation(request.conversation_id)
            if not conv:
                conv = self._conversation_repo.create_conversation(request.investigation_id)
        else:
            conv = self._conversation_repo.create_conversation(request.investigation_id)
            
        history = [{"role": msg.role, "content": msg.content} for msg in conv.messages[-5:]]
        
        # Add user message
        self._conversation_repo.append_message(conv.conversation_id, "user", request.question)

        log_data = {
            "conversation_id": conv.conversation_id,
            "investigation_id": request.investigation_id,
            "intent": "UNKNOWN",
            "evidence_count": 0,
            "citation_count": 0,
            "llm_provider": None,
            "llm_status": None,
            "fallback_used": False,
            "latency_ms": 0.0,
            "answer_generated": False
        }

        def _log_and_return(resp: CopilotQueryResponse) -> CopilotQueryResponse:
            log_data["latency_ms"] = round((time.time() - start_time) * 1000, 2)
            log_data["answer_generated"] = True
            
            provider = get_llm_provider()
            if provider and hasattr(provider, "last_trace") and provider.last_trace:
                log_data["llm_provider"] = provider.last_trace.provider
                log_data["llm_status"] = provider.last_trace.status
                log_data["fallback_used"] = provider.last_trace.fallback_used
            
            logger.info("Copilot query processed", extra={"structured_log": log_data})
            return resp

        # 2. Retrieve InvestigationState
        state = self._state_provider.get_state(request.investigation_id)
        if not state:
            answer = "This investigation could not be accessed."
            self._conversation_repo.append_message(conv.conversation_id, "assistant", answer)
            return _log_and_return(CopilotQueryResponse(
                investigation_id=request.investigation_id,
                conversation_id=conv.conversation_id,
                question_type="UNKNOWN",
                answer=answer,
                confidence=0.0,
                runtime_trace=log_data
            ))

        # 3. Semantic Intent Routing
        history_text = " | ".join([m["content"] for m in history])
        intent = classify_intent_semantic(request.question, history_context=history_text)
        log_data["intent"] = intent
        
        # 4. Handle COMPARISON explicitly
        if intent == "COMPARISON":
            comp_answer = self._comparison_service.generate_comparison(request.investigation_id, request.question, history)
            self._conversation_repo.append_message(conv.conversation_id, "assistant", comp_answer)
            return _log_and_return(CopilotQueryResponse(
                investigation_id=request.investigation_id,
                conversation_id=conv.conversation_id,
                question_type=intent,
                answer=comp_answer,
                confidence=0.9,
                runtime_trace=log_data
            ))
            
        # 5. Assemble Context & Generate Grounded Answer
        extra_ctx = {}
        # Simple RAG integration fallback if evidence is directly requested
        if intent in ["EVIDENCE_QUERY", "EVIDENCE_GAP"]:
            # If we had a real RAG tool, we'd query it here. State already has evidence.
            pass

        context_obj = self._build_context(state, history, extra_ctx)
        
        llm_out = self._generate_grounded_answer(
            question=request.question,
            context=context_obj,
            caveat_override=None
        )
        
        answer_text = guardrails.sanitize_outgoing_answer(llm_out.answer)
        
        # Save focus to metadata if provided
        metadata = {"focus": llm_out.focus} if llm_out.focus else None
        self._conversation_repo.append_message(conv.conversation_id, "assistant", answer_text, metadata=metadata)
        
        log_data["evidence_count"] = len(state.evidence)
        log_data["citation_count"] = 0

        return _log_and_return(CopilotQueryResponse(
            investigation_id=request.investigation_id,
            conversation_id=conv.conversation_id,
            question_type=intent,
            answer=answer_text,
            explanation=llm_out.explanation,
            evidence=[],
            citations=[],
            tools_used=[],
            confidence=0.9,
            caveat=llm_out.caveat,
            runtime_trace=log_data
        ))
