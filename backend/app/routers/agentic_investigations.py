"""
Agentic Investigation Router - Integrated into main backend.

This router handles AI-powered investigations that use the agent orchestrator.
"""
from __future__ import annotations

from typing import Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_active_user
from app.agent.orchestrator import (
    finalize_investigation,
    run_iteration,
    run_to_completion,
    start_investigation,
)
from app.llm.client import LLMError
from app.store import get_store
from app.schemas.agentic.investigation import InvestigationState, InvestigationStatus
from app.schemas.agentic.trace import InvestigationTrace, build_investigation_trace

router = APIRouter(prefix="/agentic/investigations", tags=["Agentic Investigations"])


class StartInvestigationRequest(BaseModel):
    claim_id: str
    claim_data: dict[str, Any]
    risk_score: float
    risk_level: str
    shap_contributors: list[dict] = []
    anomaly_factors: list[dict] = []
    detected_patterns: list[dict] = []
    max_iterations: Optional[int] = 5
    max_revisions: Optional[int] = 2
    auto_run: bool = False


@router.post("/start", response_model=InvestigationState)
def start_agentic_investigation(
    req: StartInvestigationRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user),
) -> InvestigationState:
    """
    Start a new AI-powered investigation for a claim.
    Uses the agent orchestrator to autonomously investigate the claim.
    """
    # Normalization layer
    if "clm_pmt_amt" in req.claim_data and "claim_amount" not in req.claim_data:
        req.claim_data["claim_amount"] = float(req.claim_data.pop("clm_pmt_amt"))
    if "clm_tot_chrg_amt" in req.claim_data and "total_charge_amount" not in req.claim_data:
        req.claim_data["total_charge_amount"] = float(req.claim_data.pop("clm_tot_chrg_amt"))

    # ML integration normalization
    if req.anomaly_factors and not req.shap_contributors:
        req.shap_contributors = req.anomaly_factors

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
        # Apply normalization
        state.claim_amount = float(req.claim_data.get("claim_amount", 0.0))
        state.claim_date = req.claim_data.get("service_date")
        state.provider_name = (
            req.claim_data.get("provider_name")
            or req.claim_data.get("provider_id")
            or "UNKNOWN"
        )
        state.procedure = req.claim_data.get("procedure", "UNKNOWN")

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if req.auto_run:
        try:
            run_to_completion(state)
        except LLMError as exc:
            get_store().save(state)
            raise HTTPException(status_code=503, detail=f"LLM dependency unavailable: {exc}")

    get_store().save(state)
    return state


@router.get("/{investigation_id}", response_model=InvestigationState)
def get_agentic_investigation(
    investigation_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user),
) -> InvestigationState:
    """Get the current state of an agentic investigation."""
    state = get_store().get(investigation_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return state


@router.get("/{investigation_id}/trace", response_model=InvestigationTrace)
def get_investigation_trace(
    investigation_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user),
) -> InvestigationTrace:
    """Returns a privacy-safe, structured investigation trace for Copilot."""
    state = get_store().get(investigation_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return build_investigation_trace(state)


@router.post("/{investigation_id}/step", response_model=InvestigationState)
def step_investigation(
    investigation_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user),
) -> InvestigationState:
    """Run exactly one iteration of the investigation loop."""
    state = get_store().get(investigation_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Investigation not found")

    try:
        if state.status == InvestigationStatus.IN_PROGRESS:
            run_iteration(state)
        elif state.status in (
            InvestigationStatus.COUNTER_ANALYSIS,
            InvestigationStatus.MAX_ITERATIONS_REACHED,
        ):
            finalize_investigation(state)
    except LLMError as exc:
        get_store().save(state)
        raise HTTPException(status_code=503, detail=f"LLM dependency unavailable: {exc}")

    get_store().save(state)
    return state


def _run_background(investigation_id: str):
    """Background task to run investigation to completion."""
    import traceback
    import logging
    import time
    from app.agent.orchestrator import run_iteration, finalize_investigation
    from app.llm.client import LLMClient
    from app.store import get_store

    logger = logging.getLogger(__name__)
    logger.info(f"[AGENT] Background task started: {investigation_id}")

    state = get_store().get(investigation_id)
    if not state:
        logger.error(f"[AGENT ERROR] {investigation_id} not found in DB")
        return

    logger.info(f"[AGENT] State loaded: {investigation_id}")

    llm = LLMClient()
    state.status = InvestigationStatus.IN_PROGRESS
    state.current_reasoning = "Agent execution started"
    get_store().save(state)

    consecutive_failures = 0
    max_consecutive_failures = 3

    while state.status == InvestigationStatus.IN_PROGRESS:
        try:
            logger.info(
                f"[AGENT] Iteration {state.iteration_count + 1} started: {investigation_id}"
            )
            run_iteration(state, llm)
            get_store().save(state)
            logger.info(f"[AGENT] Iteration {state.iteration_count} persisted")
            consecutive_failures = 0
        except (LLMError, Exception) as exc:
            consecutive_failures += 1
            logger.warning(
                f"[AGENT] Iteration failed ({consecutive_failures}/{max_consecutive_failures}): {exc}"
            )

            if consecutive_failures >= max_consecutive_failures:
                logger.warning(f"[AGENT] Max consecutive failures reached. Forcing finalization.")
                if state.iteration_count > 0:
                    state.status = InvestigationStatus.MAX_ITERATIONS_REACHED
                    state.current_reasoning = f"Investigation halted after {state.iteration_count} iterations due to repeated LLM failures."
                else:
                    state.status = InvestigationStatus.FAILED
                    state.current_reasoning = f"Investigation could not start: {exc}"
                get_store().save(state)
                break
            else:
                backoff = min(2 ** consecutive_failures, 10)
                logger.info(f"[AGENT] Waiting {backoff}s before retry...")
                time.sleep(backoff)

    if state.status in (
        InvestigationStatus.COUNTER_ANALYSIS,
        InvestigationStatus.MAX_ITERATIONS_REACHED,
    ):
        try:
            logger.info(f"[AGENT] Starting counter-analysis and critic: {investigation_id}")
            finalize_investigation(state, llm)
            get_store().save(state)
            logger.info(f"[AGENT] Investigation completed: {investigation_id}")
        except Exception as exc:
            logger.error(f"[AGENT] Finalization error: {exc}")
            state.status = InvestigationStatus.REQUIRES_HUMAN_REVIEW
            state.current_reasoning = f"Partial investigation completed. Finalization encountered errors: {exc}"
            get_store().save(state)
            logger.error(f"[AGENT ERROR] {investigation_id}\n{traceback.format_exc()}")


@router.post("/{investigation_id}/run", response_model=InvestigationState)
def run_investigation(
    investigation_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user),
) -> InvestigationState:
    """Run the investigation to completion asynchronously."""
    state = get_store().get(investigation_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Investigation not found")

    background_tasks.add_task(_run_background, investigation_id)

    return state
