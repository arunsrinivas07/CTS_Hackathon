from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent.orchestrator import finalize_investigation, run_iteration, run_to_completion, start_investigation
from llm.client import LLMError
from api import store
from schemas.investigation import InvestigationState, InvestigationStatus
from schemas.trace import InvestigationTrace, build_investigation_trace

router = APIRouter(prefix="/api/investigations", tags=["investigations"])


class StartInvestigationRequest(BaseModel):
    claim_id: str
    claim_data: dict[str, Any]
    risk_score: float
    risk_level: str
    shap_contributors: list[dict] = []
    detected_patterns: list[dict] = []
    max_iterations: Optional[int] = 5
    max_revisions: Optional[int] = 2
    auto_run: bool = False  # if true, runs the full loop synchronously before returning


@router.post("/start", response_model=InvestigationState)
def start(req: StartInvestigationRequest) -> InvestigationState:
    # ---------------------------------------------------------
    # NORMALIZATION LAYER
    # ---------------------------------------------------------
    if "clm_pmt_amt" in req.claim_data and "claim_amount" not in req.claim_data:
        req.claim_data["claim_amount"] = float(req.claim_data.pop("clm_pmt_amt"))
    if "clm_tot_chrg_amt" in req.claim_data and "total_charge_amount" not in req.claim_data:
        req.claim_data["total_charge_amount"] = float(req.claim_data.pop("clm_tot_chrg_amt"))
    # ---------------------------------------------------------

    try:
        state = start_investigation(
            claim_id=req.claim_id,
            claim_data=req.claim_data,
            risk_score=req.risk_score,
            risk_level=req.risk_level,
            shap_contributors=req.shap_contributors,
            detected_patterns=req.detected_patterns,
            max_iterations=req.max_iterations or 5,
            max_revisions=req.max_revisions or 2,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if req.auto_run:
        try:
            run_to_completion(state)
        except LLMError as exc:
            store.save(state)
            raise HTTPException(status_code=503, detail=f"LLM dependency unavailable: {exc}")

    store.save(state)
    return state


@router.get("/{investigation_id}", response_model=InvestigationState)
def get_investigation(investigation_id: str) -> InvestigationState:
    state = store.get(investigation_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return state


@router.get("/{investigation_id}/trace", response_model=InvestigationTrace)
def get_investigation_trace(investigation_id: str) -> InvestigationTrace:
    """Returns a privacy-safe, structured investigation trace for Member 3 Copilot."""
    state = store.get(investigation_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return build_investigation_trace(state)


@router.post("/{investigation_id}/step", response_model=InvestigationState)
def step(investigation_id: str) -> InvestigationState:
    """Runs exactly one loop iteration (or one finalize pass if past the main loop)."""
    state = store.get(investigation_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Investigation not found")

    try:
        if state.status == InvestigationStatus.IN_PROGRESS:
            run_iteration(state)
        elif state.status in (InvestigationStatus.COUNTER_ANALYSIS, InvestigationStatus.MAX_ITERATIONS_REACHED):
            finalize_investigation(state)
        # else: terminal state (COMPLETED / REQUIRES_HUMAN_REVIEW / FAILED) -- no-op
    except LLMError as exc:
        store.save(state)
        raise HTTPException(status_code=503, detail=f"LLM dependency unavailable: {exc}")

    store.save(state)
    return state


@router.post("/{investigation_id}/run", response_model=InvestigationState)
def run(investigation_id: str) -> InvestigationState:
    """Runs the investigation to completion (or to a terminal state) synchronously."""
    state = store.get(investigation_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Investigation not found")

    try:
        run_to_completion(state)
    except LLMError as exc:
        store.save(state)
        raise HTTPException(status_code=503, detail=f"LLM dependency unavailable: {exc}")

    store.save(state)
    return state
