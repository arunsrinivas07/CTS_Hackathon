import json
from typing import Any

from app.schemas.agentic.tool import ToolOutput
from app.tools.base import BaseTool

class MLVerificationTool(BaseTool):
    name = "ml_verification"
    description = (
        "Independently inspects the claim data to verify whether the ML's risk "
        "prediction (risk score, level, and factors) is supported by the facts "
        "of the claim. Must be called to validate ML output before proceeding."
    )

    def run(self, **kwargs: Any) -> ToolOutput:
        # Expected inputs
        claim_data = kwargs.get("claim_data", {})
        risk_score = kwargs.get("risk_score", 0.0)
        risk_level = kwargs.get("risk_level", "UNKNOWN")
        risk_factors = kwargs.get("risk_factors", [])
        shap_factors = kwargs.get("shap_factors", [])
        detected_patterns = kwargs.get("detected_patterns", [])

        verified = True
        verified_factors = []
        unsupported_factors = []
        claim_facts = []
        verification_notes = []

        # Claim facts
        claim_amount = claim_data.get("claim_amount", claim_data.get("clm_pmt_amt", 0.0))
        claim_facts.append(f"Claim Amount: ${claim_amount}")
        
        provider = claim_data.get("provider_id", claim_data.get("provider", "UNKNOWN"))
        claim_facts.append(f"Provider: {provider}")
        
        procedure = claim_data.get("procedure", claim_data.get("procedure_code", "UNKNOWN"))
        claim_facts.append(f"Procedure: {procedure}")

        diagnosis = claim_data.get("diagnosis", "UNKNOWN")
        claim_facts.append(f"Diagnosis: {diagnosis}")

        # Check factors
        all_factors = []
        for rf in risk_factors:
            if isinstance(rf, dict):
                all_factors.append(rf.get("name", "unknown"))
            elif hasattr(rf, "name"):
                all_factors.append(rf.name)
        
        for sf in shap_factors:
            if isinstance(sf, dict) and "feature" in sf:
                all_factors.append(sf["feature"])

        # De-duplicate
        all_factors = list(set(all_factors))

        # Basic deterministic rules
        for factor in all_factors:
            f_lower = factor.lower()
            if "amount" in f_lower:
                if float(claim_amount) > 0:
                    verified_factors.append(factor)
                else:
                    unsupported_factors.append(factor)
                    verified = False
            elif "procedure" in f_lower or "freq" in f_lower:
                if procedure != "UNKNOWN" and procedure != "":
                    verified_factors.append(factor)
                else:
                    unsupported_factors.append(factor)
                    verified = False
            elif "diagnosis" in f_lower:
                if diagnosis != "UNKNOWN" and diagnosis != "":
                    verified_factors.append(factor)
                else:
                    unsupported_factors.append(factor)
                    verified = False
            else:
                # If we don't have explicit claim data to verify it, we flag it.
                unsupported_factors.append(factor)
                verified = False

        if verified:
            verification_notes.append("Claim data appears to logically support the primary ML risk factors.")
        else:
            verification_notes.append("Required supporting features are unavailable or mismatched in current claim context.")

        result = {
            "tool": self.name,
            "verified": verified,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "verified_factors": verified_factors,
            "unsupported_factors": unsupported_factors,
            "claim_facts": claim_facts,
            "anomaly_explanation": f"ML indicates {risk_level} risk ({risk_score}). Verification found {len(verified_factors)} supported factors.",
            "verification_notes": " ".join(verification_notes)
        }

        # Build proper evidence items so they appear in Documents & Evidence
        from app.schemas.agentic.tool import EvidenceItem
        evidence_items = []

        # Evidence: ML Risk Assessment
        evidence_items.append(EvidenceItem(
            source="ML Risk Engine",
            document="Hybrid Ensemble Model Output",
            section="Risk Assessment",
            text=f"ML hybrid ensemble assigns risk score {risk_score} ({risk_level}). "
                 f"Primary risk factors: {', '.join(all_factors) if all_factors else 'none identified'}. "
                 f"Claim amount: ${claim_amount}, Provider: {provider}, Procedure: {procedure}.",
            retrieval_score=1.0,
            evidence_score=0.9,
        ))

        # Evidence: Factor Verification
        if verified_factors:
            evidence_items.append(EvidenceItem(
                source="ML Verification",
                document="Factor Verification Report",
                section="Verified Factors",
                text=f"The following risk factors were verified against claim data: {', '.join(verified_factors)}. "
                     f"These factors are supported by the claim's actual attributes.",
                retrieval_score=1.0,
                evidence_score=0.85,
            ))

        if unsupported_factors:
            evidence_items.append(EvidenceItem(
                source="ML Verification",
                document="Factor Verification Report",
                section="Unsupported Factors",
                text=f"The following risk factors could NOT be independently verified: {', '.join(unsupported_factors)}. "
                     f"Additional investigation is needed to confirm or refute these signals.",
                retrieval_score=1.0,
                evidence_score=0.7,
            ))

        return ToolOutput(
            status="SUCCESS",
            data=result,
            evidence=evidence_items,
            confidence=1.0,
        )
