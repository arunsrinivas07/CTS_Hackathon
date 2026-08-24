"""
Investigation Orchestrator: the explicit, controllable state-machine loop
described in spec section 7/17/35.

    Guardrails -> Understand claim -> Reason/Plan -> Generate question ->
    Select tool -> Execute -> Observe -> Update state -> Evaluate evidence ->
    (loop) -> Counter-analysis -> Critic -> (revise up to 2x) -> Final report

This module coordinates the other agent/* modules but contains no tool or
LLM-prompt internals itself -- those live in their respective modules so
each piece stays independently testable.
"""
from __future__ import annotations

import json
import logging
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.agent.counter_analysis import run_counter_analysis
from app.agent.evidence_evaluator import evaluate_sufficiency
from app.agent.question_generator import generate_next_question
from app.agent.report_generator import build_final_report, draft_conclusion
from app.agent.critic import run_critic
from app.agent.state import initialize_investigation, new_id
from app.agent.tool_executor import deterministic_observation_text, execute_tool, record_observation
from app.agent.tool_router import resolve_tool
from app.llm.client import LLMClient, LLMError
from app.schemas.agentic.investigation import InvestigationObjective, InvestigationState, InvestigationStatus
from app.schemas.agentic.tool import ToolResultStatus

logger = logging.getLogger("agent.orchestrator")

def _derive_objectives(state: InvestigationState, llm: LLMClient) -> list[InvestigationObjective]:
    """Deterministically derive objectives from risk factors to save LLM calls."""
    objectives = []
    
    # 1. Address the primary risk factors
    if state.risk_factors:
        for rf in state.risk_factors:
            objectives.append(
                InvestigationObjective(
                    objective_id=new_id("obj"),
                    description=f"Verify if the {rf.name} anomaly has a legitimate clinical or billing explanation.",
                    related_risk_factors=[rf.name],
                )
            )
            
    # 2. Address detected patterns
    if state.detected_patterns:
        for p in state.detected_patterns:
            objectives.append(
                InvestigationObjective(
                    objective_id=new_id("obj"),
                    description=f"Investigate the detected {p.name} pattern for signs of intentional FWA.",
                    related_risk_factors=[],
                )
            )
            
    # Fallback
    if not objectives:
        objectives.append(
            InvestigationObjective(
                objective_id=new_id("obj"),
                description="Determine whether the claim reflects a genuine anomaly.",
                related_risk_factors=[],
            )
        )
        
    return objectives


def start_investigation(
    claim_id: str,
    claim_data: dict,
    risk_score: float,
    risk_level: str,
    shap_contributors: list[dict],
    detected_patterns: list[dict],
    max_iterations: int = 5,
    max_revisions: int = 2,
    llm: LLMClient | None = None,
) -> InvestigationState:
    """
    GUARDRAILS + Understand-claim-state + objective derivation. This is the
    entry point called with the output of the existing deterministic
    pipeline (ML/rules/priority) once a claim reaches the investigator queue.
    """
    llm = llm or LLMClient()

    if risk_score is None or not (0.0 <= risk_score <= 1.0):
        raise ValueError("Guardrail violation: risk_score must be a float in [0, 1].")
    if not claim_id:
        raise ValueError("Guardrail violation: claim_id is required.")

    state = initialize_investigation(
        claim_id=claim_id,
        claim_data=claim_data,
        risk_score=risk_score,
        risk_level=risk_level,
        shap_contributors=shap_contributors,
        detected_patterns=detected_patterns,
        max_iterations=max_iterations,
        max_revisions=max_revisions,
    )

    print("============================================================")
    print("CLAIMGUARD AGENTIC INVESTIGATION")
    print("============================================================")
    print("\n[CLAIM]")
    print(f"Claim ID: {claim_id}")
    print(f"Provider ID: {claim_data.get('provider_id', 'UNKNOWN')}")
    print(f"Beneficiary ID: {claim_data.get('bene_id', 'UNKNOWN')}")
    print(f"Claim Type: {claim_data.get('claim_type', 'UNKNOWN')}")
    print(f"Claim Amount: {claim_data.get('claim_amount', claim_data.get('clm_pmt_amt', 'UNKNOWN'))}")

    print("\n[ML]")
    print(f"Risk Score: {risk_score}")
    print(f"Risk Level: {risk_level}")
    shap_text = ", ".join(f"{s.get('feature')}" for s in shap_contributors) if shap_contributors else "None"
    print(f"SHAP Factors: {shap_text}")

    print("\n[PATTERN]")
    pattern_text = ", ".join(f"{p.get('pattern_type')}" for p in detected_patterns) if detected_patterns else "None"
    print(f"Detected Patterns: {pattern_text}")

    print("\n[PRIORITY]")
    # Placeholder priority calculation - can be derived based on risk_level
    priority_level = "CRITICAL" if risk_level == "CRITICAL" else "HIGH" if risk_score > 0.8 else "MEDIUM"
    print(f"Priority: {priority_level}")

    print("\n[GUARDRAIL]")
    print("Validation: PASS")

    print("\n[ORCHESTRATOR]")
    print("Investigation started")

    state.investigation_objectives = _derive_objectives(state, llm)
    state.current_hypothesis = (
        f"The claim exhibits elevated fraud risk (score={risk_score}, level={risk_level}) "
        f"potentially driven by: {', '.join(rf.name for rf in state.risk_factors) or 'unspecified factors'}."
    )
    state.status = InvestigationStatus.IN_PROGRESS
    state.touch()
    return state


def run_iteration(state: InvestigationState, llm: LLMClient | None = None) -> InvestigationState:
    """
    Runs exactly ONE loop iteration:
      generate question -> select/validate tool -> execute -> observe ->
      evaluate evidence -> decide next_action

    Mutates and returns `state`. Caller (API layer or `run_to_completion`)
    decides whether to call this again, move to counter-analysis, or stop.
    """
    llm = llm or LLMClient()

    if state.status not in (InvestigationStatus.IN_PROGRESS,):
        return state

    if state.iteration_count >= state.max_iterations:
        state.status = InvestigationStatus.MAX_ITERATIONS_REACHED
        state.touch()
        return state

    state.iteration_count += 1

    print("\n[REASON]")
    print(f"Current hypothesis: {state.current_hypothesis}")
    
    question = generate_next_question(state, llm)
    if question:
        print(f"\n[REASON]\nEvidence gap identified: {question.question}")
    if question is None:
        # No useful next question -- move on to counter-analysis/report.
        state.status = InvestigationStatus.COUNTER_ANALYSIS
        state.touch()
        return state

    state.questions.append(question)
    state.question_history.append(question.question)

    tool_name = resolve_tool(question)
    if tool_name is None:
        # Question was generated but no registered tool can answer it --
        # record as an unresolved gap rather than silently dropping it.
        record = execute_tool(question.preferred_tool or "unknown", question, state)
        record_observation(record, state, deterministic_observation_text(record))
        
        # Skip expensive LLM sufficiency check since nothing happened
        from app.schemas.agentic.evidence import EvidenceSufficiencyResult
        result = EvidenceSufficiencyResult(
            sufficient=False,
            reason="No tool was available to gather evidence.",
            missing_evidence=[f"Could not gather evidence for: {question.question}"],
            next_action="generate_question"
        )
        state.sufficiency_history.append(result)
    else:
        print(f"\n[TOOL]\nSelected tool: {tool_name or 'unknown'}")
        print(f"[TOOL]\nExecuting: {tool_name or 'unknown'}")
        record = execute_tool(tool_name or question.preferred_tool or "unknown", question, state)
        print("[TOOL]\nResult received")
        record_observation(record, state, deterministic_observation_text(record))
        print("[OBSERVE]\nInvestigation state updated")

        print("\n[REASON]\nRe-evaluating evidence")
        if state.iteration_count == 1:
            from app.schemas.agentic.evidence import EvidenceSufficiencyResult
            result = EvidenceSufficiencyResult(
                sufficient=False,
                reason="Initial ML verification complete. External policy evidence is required.",
                missing_evidence=["CMS policy rules"],
                next_action="generate_question"
            )
            state.sufficiency_history.append(result)
        else:
            result = evaluate_sufficiency(state, llm)

    if result.sufficient or result.next_action == "counter_analysis":
        state.status = InvestigationStatus.COUNTER_ANALYSIS
    elif result.next_action == "escalate":
        state.status = InvestigationStatus.REQUIRES_HUMAN_REVIEW
    else:
        state.status = InvestigationStatus.IN_PROGRESS

    print("\n[ORCHESTRATOR]\nInvestigation iteration completed.")
    print(f"\n[INVESTIGATION]\nStatus: {state.status.value}")

    state.touch()
    return state


def finalize_investigation(state: InvestigationState, llm: LLMClient | None = None) -> InvestigationState:
    """
    Runs counter-analysis -> critic -> (revise up to max_revisions) -> report.
    Called once state.status == COUNTER_ANALYSIS (or MAX_ITERATIONS_REACHED,
    which still deserves a best-effort report rather than dead-ending).
    """
    llm = llm or LLMClient()

    if state.status not in (InvestigationStatus.COUNTER_ANALYSIS, InvestigationStatus.MAX_ITERATIONS_REACHED):
        return state

    print("\n[COUNTER]\nSearching for counter-evidence")
    run_counter_analysis(state, llm)
    
    # Simple check for counter-evidence
    if state.counter_evidence:
        print(f"[COUNTER]\nCounter-evidence found: {len(state.counter_evidence)} items")
    else:
        print("[COUNTER]\nNo meaningful counter-evidence found")

    state.status = InvestigationStatus.CRITIC_REVIEW
    state.touch()

    print("\n[REASON]\nUpdating investigation hypothesis...")
    draft = draft_conclusion(state, llm)
    revision = 0
    
    print("\n[CRITIC]\nReviewing investigation")
    print("[CRITIC]\nGrounding check")
    print("[CRITIC]\nCitation check")
    critic_result = run_critic(state, draft.get("conclusion", ""), revision, llm)
    print(f"[CRITIC]\nResult: {critic_result.status}")

    while critic_result.status == "FAIL" and revision < state.max_revisions:
        print(f"[CRITIC]\nRevision required ({revision + 1}/{state.max_revisions})")
        revision += 1
        state.revision_count = revision
        logger.info("Critic FAIL (revision %s/%s): %s", revision, state.max_revisions, critic_result.issues)
        draft = draft_conclusion(state, llm)  # re-draft; issues are implicitly available via state history
        print("\n[CRITIC]\nRe-evaluating investigation")
        critic_result = run_critic(state, draft.get("conclusion", ""), revision, llm)
        print(f"[CRITIC]\nResult: {critic_result.status}")

    if critic_result.status == "FAIL":
        # Even if critic fails, still build a best-effort final report
        # so the frontend can show findings. Mark as REQUIRES_HUMAN_REVIEW
        # so the investigator knows it needs manual validation.
        build_final_report(state, draft, critic_result)
        state.status = InvestigationStatus.REQUIRES_HUMAN_REVIEW
        state.touch()
        return state

    build_final_report(state, draft, critic_result)
    state.status = InvestigationStatus.COMPLETED
    state.touch()
    
    print("\n[REPORT]\nFinal report generated")
    print("\n[COPILOT]\nInvestigation ready")

    print("\n============================================================")
    print("1. Executive Summary")
    print(f"   {state.final_report.claim_summary}")
    print("\n2. Investigation Overview")
    print(f"   Investigation ID : {state.investigation_id}")
    print(f"   Claim ID         : {state.claim_id}")
    print("\n3. Initial Claim Context")
    print(f"   Data: {state.claim_data}")
    print("\n4. Risk Assessment & ML Insights")
    print(f"   Risk Score: {state.risk_score} | Level: {state.risk_level}")
    print(f"   Factors: {', '.join(rf.name for rf in state.risk_factors)}")
    print("\n5. Identified Patterns")
    print(f"   {', '.join(p.name for p in state.detected_patterns)}")
    print("\n6. Investigation Objectives")
    print(f"   {', '.join(o.description for o in state.investigation_objectives)}")
    print("\n7. Investigation Trace & Queries")
    print(f"   {len(state.questions)} questions asked.")
    print("\n8. Tools Utilized")
    print(f"   {', '.join(sorted(set(tc.tool for tc in state.tool_calls)))}")
    print("\n9. Gathered Evidence")
    print(f"   {len(state.evidence)} evidence items collected.")
    print("\n10. Relevant Citations")
    print(f"   {len(state.citations)} citations recorded.")
    print("\n11. Counter-Evidence Analysis")
    print(f"   {len(state.counter_evidence)} counter-evidence items found.")
    print("\n12. Alternative Explanations")
    print(f"   {len(state.alternative_explanations)} explanations explored.")
    print("\n13. Unresolved Evidence Gaps")
    print(f"   {len(state.evidence_gaps)} gaps remaining.")
    print("\n14. Final Findings")
    print(f"   {len(state.final_report.findings)} findings concluded.")
    print("\n15. Confidence Score")
    print(f"   {state.final_report.confidence}")
    print("\n16. Critic & Compliance Review")
    print(f"   {critic_result.status} (Revisions: {state.revision_count})")
    print("\n17. Investigation Status")
    print(f"   {state.status.value}")
    print("============================================================\n")

    return state


def run_to_completion(state: InvestigationState, llm: LLMClient | None = None) -> InvestigationState:
    """Convenience driver: runs iterations until the loop naturally exits, then finalizes."""
    llm = llm or LLMClient()
    while state.status == InvestigationStatus.IN_PROGRESS:
        run_iteration(state, llm)
    if state.status in (InvestigationStatus.COUNTER_ANALYSIS, InvestigationStatus.MAX_ITERATIONS_REACHED):
        finalize_investigation(state, llm)
    return state
