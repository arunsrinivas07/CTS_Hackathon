from pydantic import BaseModel
from typing import Optional, List
from app.adapters.investigation_state_adapter import InvestigationStateProvider
from llm.factory import get_llm_provider
import re

class ComparisonContext(BaseModel):
    claim_a_id: str
    claim_a_context: dict
    claim_b_id: str
    claim_b_context: dict
    question: str
    history: List[dict]

class ComparisonLLMOutput(BaseModel):
    answer: str

class ComparisonService:
    def __init__(self, state_provider: InvestigationStateProvider):
        self.state_provider = state_provider
        
    def _extract_claim_id_from_question(self, question: str, default_id: str) -> str:
        # Simplistic extraction for MVP, in a real system we'd use the LLM intent extraction.
        # The user's prompt will often just say "Compare C10234 with C10235".
        matches = re.findall(r'(?:inv_c|C)\d{5}', question, re.IGNORECASE)
        for m in matches:
            # normalize to inv_c format
            target_id = m.lower() if m.lower().startswith("inv_") else f"inv_{m.lower()}"
            if target_id != default_id:
                return target_id
        return default_id
        
    def generate_comparison(self, investigation_id: str, question: str, history: List[dict]) -> str:
        target_claim_id = self._extract_claim_id_from_question(question, investigation_id)
        
        state_a = self.state_provider.get_state(investigation_id)
        state_b = self.state_provider.get_state(target_claim_id)
        
        if not state_a or not state_b:
            return f"I cannot compare these claims because I do not have access to both {investigation_id} and {target_claim_id}."
            
        def _build_summary(state):
            return {
                "risk_score": state.risk_score,
                "risk_tier": state.risk_level,
                "provider": state.claim_data.get("provider_id", "Unknown"),
                "claim_amount": state.claim_data.get("amount", "Unknown"),
                "evidence_gaps": [g.description for g in state.evidence_gaps],
                "retrieved_evidence": [e.text for e in state.evidence],
                "investigation_status": state.status.value
            }
            
        ctx = ComparisonContext(
            claim_a_id=investigation_id,
            claim_a_context=_build_summary(state_a),
            claim_b_id=target_claim_id,
            claim_b_context=_build_summary(state_b),
            question=question,
            history=history
        )
        
        provider = get_llm_provider()
        
        system_prompt = """You are a comparison engine for a healthcare fraud investigator copilot.
You are comparing two claims.
IMPORTANT INSTRUCTIONS:
- Explicitly distinguish between FACT (data present), INFERENCE (reasoning), and MISSING INFORMATION (unknowns).
- Never invent missing facts or claim amounts.
- Compare risk signals, evidence, and gaps.
- Output ONLY the final markdown answer in the 'answer' field."""
        user_prompt = f"Context:\n{ctx.model_dump_json(indent=2)}\n\nQuestion: {question}"
        
        try:
            res = provider.structured_generate(system_prompt=system_prompt, user_prompt=user_prompt, response_model=ComparisonLLMOutput)
            return res.answer
        except Exception as e:
            import traceback
            traceback.print_exc()
            return "I encountered an error trying to compare the claims."
