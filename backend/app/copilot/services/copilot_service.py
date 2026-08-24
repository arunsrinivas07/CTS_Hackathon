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

from app.copilot.adapters.investigation_state_adapter import InvestigationStateProvider
from app.copilot.adapters.conversation_adapter import get_conversation_repository
from app.copilot.schemas.copilot import CopilotQueryRequest, CopilotQueryResponse, QuestionType
from app.schemas.agentic.investigation import InvestigationState
from app.copilot.services import guardrails
from app.copilot.services.evidence_resolver import resolve_from_state
from app.copilot.services.intent_router import classify_intent_semantic
from app.copilot.services.comparison_service import ComparisonService
from app.copilot.services.tool_router import ToolRouter

from app.llm.factory import get_fast_llm
from app.llm.errors import LLMProviderError, StructuredOutputError

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
            "evidence": [e.description for e in state.evidence],
            "evidence_gaps": [g.description for g in state.evidence_gaps],
            "conversation": history
        }
        ctx.update(extra_ctx)
        return ctx

    def _generate_grounded_answer(
        self, question: str, context: dict, caveat_override: Optional[str]
    ) -> CopilotLLMOutput:
        provider = get_fast_llm()
        
        # Enhanced system prompt that acknowledges dynamic tool results
        system_prompt = (
            "You are an investigator copilot for healthcare claims fraud.\n"
            "You MUST use ONLY the supplied investigation context to answer the question.\n"
            "The context may include:\n"
            "  - Investigation state and evidence collected by the agent\n"
            "  - Dynamically retrieved RAG/CMS policy citations (rag_citations)\n"
            "  - Real-time ML model explanations (ml_explanation)\n"
            "  - Provider billing history (provider_history)\n"
            "Use these dynamically fetched results when available.\n"
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
            # LLM unavailable — construct a grounded answer directly from the context data
            return self._build_fallback_answer(question, context, caveat_override)

    def _build_fallback_answer(self, question: str, context: dict, caveat_override: Optional[str]) -> CopilotLLMOutput:
        """Build a deterministic answer from investigation context when LLM is unavailable."""
        q_lower = question.lower()
        inv = context.get("investigation", {})
        risk = context.get("risk", {})
        claim = context.get("claim", {})
        evidence = context.get("evidence", [])
        gaps = context.get("evidence_gaps", [])
        
        # Check for dynamically fetched tool results
        rag_citations = context.get("rag_citations", [])
        ml_explanation = context.get("ml_explanation", "")
        provider_history = context.get("provider_history", [])

        answer_parts = []

        # Risk / flagging questions
        if any(kw in q_lower for kw in ["flag", "risk", "why", "score"]):
            score = risk.get("score", 0)
            tier = risk.get("tier", "UNKNOWN")
            answer_parts.append(f"This claim has a risk score of {score:.3f} ({tier}).")
            if ml_explanation:
                answer_parts.append(f"\n{ml_explanation}")
            elif evidence:
                answer_parts.append("\nKey evidence collected:")
                for ev in evidence[:4]:
                    answer_parts.append(f"  • {ev}")

        # ML factors
        elif any(kw in q_lower for kw in ["ml", "factor", "shap", "feature", "model", "predict"]):
            if ml_explanation:
                answer_parts.append(ml_explanation)
            else:
                score = risk.get("score", 0)
                tier = risk.get("tier", "UNKNOWN")
                answer_parts.append(f"ML hybrid model assigned risk score {score:.3f} ({tier}).")
                ml_evidence = [e for e in evidence if "ml" in str(e).lower() or "risk" in str(e).lower()]
                if ml_evidence:
                    for ev in ml_evidence[:3]:
                        answer_parts.append(f"  • {ev}")
                else:
                    answer_parts.append("Detailed ML factor breakdown is not available in the current evidence.")

        # Provider
        elif any(kw in q_lower for kw in ["provider", "facility", "hospital", "clinic", "history", "billing"]):
            if provider_history:
                answer_parts.append("Provider history retrieved:")
                for prov_ev in provider_history[:3]:
                    answer_parts.append(f"  • {prov_ev.get('summary', str(prov_ev))}")
            else:
                prov_evidence = [e for e in evidence if "provider" in str(e).lower() or "billing" in str(e).lower()]
                if prov_evidence:
                    answer_parts.append("Provider information from investigation:")
                    for ev in prov_evidence[:3]:
                        answer_parts.append(f"  • {ev}")
                else:
                    prov_id = claim.get("provider_id", "Unknown")
                    answer_parts.append(f"Provider ID: {prov_id}. No specific provider evidence was collected during this investigation.")

        # Policy / CMS
        elif any(kw in q_lower for kw in ["policy", "cms", "guideline", "coverage", "medical necessity"]):
            if rag_citations:
                answer_parts.append("Relevant CMS policy evidence:")
                for cit in rag_citations[:3]:
                    answer_parts.append(f"  • {cit.get('title', 'Unknown')}: {cit.get('excerpt', '')[:150]}")
            else:
                answer_parts.append("No CMS policy evidence was retrieved for this query. Try asking a more specific policy question.")

        # Evidence / findings
        elif any(kw in q_lower for kw in ["evidence", "finding", "collect", "discover"]):
            if evidence:
                answer_parts.append(f"{len(evidence)} evidence items collected during investigation:")
                for ev in evidence[:5]:
                    answer_parts.append(f"  • {ev}")
            else:
                answer_parts.append("No evidence has been collected yet.")
            if gaps:
                answer_parts.append(f"\nUnresolved gaps ({len(gaps)}):")
                for g in gaps[:3]:
                    answer_parts.append(f"  • {g}")

        # Summary / recommendation
        elif any(kw in q_lower for kw in ["summary", "recommend", "next", "conclusion", "action"]):
            status = inv.get("status", "UNKNOWN")
            answer_parts.append(f"Investigation status: {status}.")
            if evidence:
                answer_parts.append(f"Evidence collected: {len(evidence)} items.")
            answer_parts.append("Recommendation: Review the evidence collected and decide based on investigator judgment.")

        # Default
        else:
            answer_parts.append(f"Investigation {inv.get('investigation_id','')}: Claim {inv.get('claim_id','')}.")
            answer_parts.append(f"Status: {inv.get('status','')}. Risk score: {risk.get('score', 0):.3f}.")
            if evidence:
                answer_parts.append(f"Evidence: {len(evidence)} items.")
            answer_parts.append("Ask a more specific question about risk, findings, provider, or evidence.")

        answer = "\n".join(answer_parts)
        return CopilotLLMOutput(
            answer=answer,
            explanation="Response generated from investigation context (LLM temporarily unavailable).",
            caveat=caveat_override or "LLM was rate-limited. This response uses direct evidence extraction.",
            focus=None
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
            
            provider = get_fast_llm()
            if provider and hasattr(provider, "last_trace") and provider.last_trace:
                log_data["llm_provider"] = provider.last_trace.provider
                log_data["llm_success"] = provider.last_trace.success
                log_data["fallback_used"] = provider.last_trace.fallback_used
            
            logger.info("Copilot query processed", extra={"structured_log": log_data})
            return resp

        # 2. Retrieve InvestigationState
        state = self._state_provider.get_state(request.investigation_id)
        if not state:
            # NO INVESTIGATION EXISTS YET
            # Return a helpful dynamic response that invites the user to start investigation
            answer = (
                f"I don't have an active investigation for {request.investigation_id} yet. "
                f"To help you with this claim, please start the investigation first by clicking "
                f"the 'Start Investigation' button. Once the agentic investigation completes, "
                f"I'll have access to all the evidence, risk factors, and findings to answer your questions."
            )
            self._conversation_repo.append_message(conv.conversation_id, "assistant", answer)
            return _log_and_return(CopilotQueryResponse(
                investigation_id=request.investigation_id,
                conversation_id=conv.conversation_id,
                question_type="NO_INVESTIGATION",
                answer=answer,
                confidence=1.0,
                caveat="Investigation not started yet. Start investigation to enable full copilot capabilities.",
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
            
        # 5. Dynamic Tool Invocation Based on Intent
        extra_ctx = {}
        tools_invoked = []
        
        # RAG - Policy questions
        if intent in ["EVIDENCE_QUERY", "EVIDENCE_GAP"] and any(kw in request.question.lower() for kw in ["policy", "cms", "guideline", "coverage", "medical necessity"]):
            try:
                rag_result = self._tool_router.route("POLICY_QUESTION", request.question, state)
                if rag_result and rag_result.citations:
                    extra_ctx["rag_citations"] = [c.dict() for c in rag_result.citations]
                    tools_invoked.append("rag_tool")
                    logger.info(f"RAG tool invoked: {len(rag_result.citations)} citations retrieved")
            except Exception as e:
                logger.warning(f"RAG tool invocation failed: {e}")
        
        # ML - Risk/model questions
        if intent in ["RISK_ASSESSMENT", "EXPLANATION"] and any(kw in request.question.lower() for kw in ["ml", "model", "risk", "score", "shap", "factor", "predict", "why", "flagged"]):
            try:
                ml_result = self._tool_router.route("ML_EXPLANATION", request.question, state)
                if ml_result:
                    extra_ctx["ml_explanation"] = ml_result.answer
                    tools_invoked.append("ml_tool")
                    logger.info(f"ML tool invoked: {ml_result.answer[:100]}")
            except Exception as e:
                logger.warning(f"ML tool invocation failed: {e}")
        
        # Provider History
        if intent in ["CLAIM_DETAILS", "EVIDENCE_QUERY"] and any(kw in request.question.lower() for kw in ["provider history", "billing history", "prior claims", "provider behavior"]):
            try:
                prov_result = self._tool_router.route("PROVIDER_HISTORY", request.question, state)
                if prov_result and prov_result.evidence:
                    extra_ctx["provider_history"] = [e.dict() for e in prov_result.evidence]
                    tools_invoked.append("provider_db_tool")
                    logger.info(f"Provider DB tool invoked: {len(prov_result.evidence)} evidence items")
            except Exception as e:
                logger.warning(f"Provider tool invocation failed: {e}")

        context_obj = self._build_context(state, history, extra_ctx)
        log_data["tools_invoked"] = tools_invoked
        
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
        log_data["citation_count"] = len(extra_ctx.get("rag_citations", []))

        # Build tools_used list
        tools_used_records = []
        if "rag_tool" in tools_invoked:
            tools_used_records.append(ToolUsageRecord(tool="rag_tool", purpose="Retrieve CMS policy documents"))
        if "ml_tool" in tools_invoked:
            tools_used_records.append(ToolUsageRecord(tool="ml_tool", purpose="Explain ML risk factors"))
        if "provider_db_tool" in tools_invoked:
            tools_used_records.append(ToolUsageRecord(tool="provider_db_tool", purpose="Retrieve provider billing history"))

        return _log_and_return(CopilotQueryResponse(
            investigation_id=request.investigation_id,
            conversation_id=conv.conversation_id,
            question_type=intent,
            answer=answer_text,
            explanation=llm_out.explanation,
            evidence=[],
            citations=[],
            tools_used=tools_used_records,
            confidence=0.9,
            caveat=llm_out.caveat,
            runtime_trace=log_data
        ))
