"""
Realistic mock InvestigationState data used by the in-memory repository.

INTEGRATION POINT:
This entire file is throwaway once the real Investigation Orchestrator
(built by another team member) exists and produces real InvestigationState
objects. It exists only so the Copilot can be built and demoed standalone.
"""

from __future__ import annotations

from schemas.investigation import (
    CounterEvidence,
    CriticResult,
    Evidence,
    EvidenceGap,
    Citation,
    FinalReport,
    InvestigationState,
    InvestigationTraceStep,
    RiskFactor,
    SHAPFactor,
    DetectedPattern,
)


def build_inv_001() -> InvestigationState:
    return InvestigationState(
        investigation_id="INV-001",
        claim_id="C10234",
        provider_name="ABC Hospital",
        procedure="MRI",
        claim_amount=5000.0,
        claim_date="2026-06-14",
        risk_score=0.87,
        risk_factors=[
            RiskFactor(
                name="high_procedure_frequency",
                description="Provider billed an unusually high volume of MRI procedures this month compared to peers.",
                weight=0.34,
            ),
            RiskFactor(
                name="amount_outlier",
                description="Claim amount is above the 90th percentile for this procedure code in this region.",
                weight=0.21,
            ),
            RiskFactor(
                name="short_patient_provider_history",
                description="Patient has no prior claim history with this provider before this procedure.",
                weight=0.12,
            ),
        ],
        shap_factors=[
            SHAPFactor(
                feature="provider_monthly_procedure_count",
                shap_value=0.29,
                direction="increases_risk",
                description="Provider's monthly MRI count is the single largest contributor to the risk score.",
            ),
            SHAPFactor(
                feature="claim_amount_zscore",
                shap_value=0.18,
                direction="increases_risk",
                description="Claim amount deviates notably from the regional peer average for this procedure.",
            ),
            SHAPFactor(
                feature="patient_prior_claims_with_provider",
                shap_value=0.09,
                direction="increases_risk",
                description="Low prior claim history between patient and provider adds modest risk.",
            ),
            SHAPFactor(
                feature="diagnosis_procedure_alignment",
                shap_value=-0.07,
                direction="decreases_risk",
                description="Diagnosis code is consistent with the billed procedure, slightly reducing risk.",
            ),
        ],
        detected_patterns=[
            DetectedPattern(name="provider_frequency_anomaly"),
            DetectedPattern(name="amount_outlier_for_procedure_code"),
        ],
        evidence=[
            Evidence(
                evidence_id="EV-1",
                description="Provider MRI volume for the current month is 520 claims.",
                detail="ABC Hospital billed 520 MRI procedures in the current month, compared to a peer group 95th percentile of 310 per month.",
                source="Provider Claims Database",
                source_type="Mock", type="other", confidence=1.0,
                supports="provider_anomaly",
                timestamp="2026-08-10T09:00:00Z",
                added_by="investigation_agent",
            ),
            Evidence(
                evidence_id="EV-2",
                description="Claim amount is above the regional peer benchmark for this procedure code.",
                detail="The billed amount of $5,000 for this MRI procedure code is above the regional peer median of $3,200.",
                source="Claims Pricing Benchmark Dataset",
                source_type="Mock", type="other", confidence=1.0,
                supports="amount_outlier",
                timestamp="2026-08-10T09:05:00Z",
                added_by="investigation_agent",
            ),
            Evidence(
                evidence_id="EV-3",
                description="Diagnosis code on file is consistent with an MRI being a reasonable procedure.",
                detail="The patient's diagnosis code (M54.5 - low back pain) is a diagnosis for which MRI is a commonly accepted diagnostic procedure under standard clinical guidelines.",
                source="Clinical Coding Reference",
                source_type="Mock", type="other", confidence=1.0,
                supports="medical_necessity",
                timestamp="2026-08-10T09:10:00Z",
                added_by="investigation_agent",
            ),
        ],
        citations=[
            Citation(
                citation_id="CIT-1",
                title="Medical Necessity Guidelines for Advanced Imaging",
                source="Payer Clinical Policy Bulletin CPB-0042",
                source_type="Mock",
                excerpt="MRI may be considered medically necessary for persistent low back pain when conservative treatment has failed for at least six weeks.",
                url=None,
            )
        ],
        counter_evidence=[
            CounterEvidence(
                evidence_id="CE-1",
                description="Provider has a large registered patient base, which partially explains higher volume.",
                detail="ABC Hospital serves a larger regional patient population than most peer providers, which may account for some of the elevated procedure volume.",
                source="Provider Registry",
                source_type="Mock", type="other", confidence=1.0,
            ),
            CounterEvidence(
                evidence_id="CE-2",
                description="No prior fraud flags exist on this provider in the last 24 months.",
                detail="A review of the provider's compliance history shows no prior confirmed fraud findings in the last 24 months.",
                source="Provider Compliance History",
                source_type="Mock", type="other", confidence=1.0,
            ),
        ],
        evidence_gaps=[
            EvidenceGap(
                evidence_id="GAP-1",
                description="No documentation yet confirming six weeks of conservative treatment prior to MRI.",
                why_it_matters="This is required by the cited medical necessity policy to fully support the "
                               "claim as medically necessary.",
            ),
            EvidenceGap(
                evidence_id="GAP-2",
                description="Provider's historical MRI volume trend over the past 12 months has not been pulled.",
                why_it_matters="A 12-month trend would clarify whether this month's volume is a sudden spike or "
                               "a gradual, explainable increase.",
            ),
        ],
        investigation_trace=[
            InvestigationTraceStep(
                step_number=1,
                action="risk_scoring",
                description="Provider procedure frequency and claim amount were scored by the XGBoost risk model.",
                timestamp="2026-08-10T08:55:00Z",
            ),
            InvestigationTraceStep(
                step_number=2,
                action="peer_comparison",
                description="Peer comparison was performed against regional procedure-code benchmarks.",
                timestamp="2026-08-10T09:00:00Z",
            ),
            InvestigationTraceStep(
                step_number=3,
                action="policy_retrieval",
                description="Applicable medical necessity policy was retrieved for the diagnosis/procedure pair.",
                timestamp="2026-08-10T09:08:00Z",
            ),
            InvestigationTraceStep(
                step_number=4,
                action="patient_evidence_check",
                description="Patient-specific diagnosis and coding evidence was checked for consistency.",
                timestamp="2026-08-10T09:10:00Z",
            ),
            InvestigationTraceStep(
                step_number=5,
                action="counter_evidence_review",
                description="Counter-evidence regarding provider size and compliance history was evaluated.",
                timestamp="2026-08-10T09:15:00Z",
            ),
            InvestigationTraceStep(
                step_number=6,
                action="critic_review",
                description="Critic reviewed the draft conclusion for unsupported claims before finalizing.",
                timestamp="2026-08-10T09:20:00Z",
            ),
        ],
        critic_result=CriticResult(
            reviewed=True,
            notes="Conclusion is supported by evidence but should not overstate certainty; recommend escalation, "
                  "not automatic denial.",
            concerns=["Missing 12-month provider trend", "Missing conservative-treatment documentation"],
        ),
        final_report=FinalReport(
            description="Claim shows a high risk score driven primarily by provider procedure frequency and claim "
                    "amount outliers, partially offset by counter-evidence about provider size and compliance "
                    "history.",
            recommendation="escalate_for_review",
            rationale="The combination of provider frequency anomaly, amount outlier, and an incomplete medical "
                      "necessity documentation trail supports further human review before any payment decision.",
        ),
        created_at="2026-08-10T08:50:00Z",
        updated_at="2026-08-10T09:20:00Z",
    )


MOCK_INVESTIGATIONS = {
    "INV-001": build_inv_001(),
}


# --- Mock data used by adapters (provider/claim DB, RAG, ML) ---

PROVIDER_MRI_HISTORY = {
    "ABC Hospital": [
        {"month": "2026-01", "mri_count": 180},
        {"month": "2026-02", "mri_count": 195},
        {"month": "2026-03", "mri_count": 210},
        {"month": "2026-04", "mri_count": 240},
        {"month": "2026-05", "mri_count": 310},
        {"month": "2026-06", "mri_count": 355},
        {"month": "2026-07", "mri_count": 410},
        {"month": "2026-08", "mri_count": 520},
    ]
}

RELATED_CLAIMS = {
    "C10234": [
        {"claim_id": "C10199", "procedure": "X-Ray", "amount": 400.0, "date": "2026-05-02"},
        {"claim_id": "C10221", "procedure": "Physical Therapy", "amount": 900.0, "date": "2026-06-01"},
    ]
}

POLICY_DOCUMENTS = [
    {
        "id": "CIT-1",
        "title": "Medical Necessity Guidelines for Advanced Imaging",
        "source": "Payer Clinical Policy Bulletin CPB-0042",
        "excerpt": "MRI may be considered medically necessary for persistent low back pain when conservative "
                   "treatment has failed for at least six weeks.",
        "url": None,
    },
    {
        "id": "CIT-2",
        "title": "Provider Billing Frequency Review Standard",
        "source": "Payer Program Integrity Manual, Section 7.3",
        "excerpt": "Providers whose monthly procedure volume exceeds the regional 95th percentile for three "
                   "consecutive months should be flagged for utilization review.",
        "url": None,
    },
]
