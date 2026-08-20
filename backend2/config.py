"""
config.py — Single source of truth for shared constants across the V2 pipeline.
Import these in train_xgboost_fraud_v2.py, main.py, scoring, and evaluation.

IMPORTANT: Never define TIER_BINS, TIER_LABELS, or FRAUD_THRESHOLD locally in any module.
Always import from here so that training, validation, inference, and scored CSV all agree.
"""

# ── Risk Tier Bins ─────────────────────────────────────────────────────────────
# Calibrated from the holdout validation test set score distribution (n=1,353 test providers).
# Quantile-informed risk bands:
#   Low      = [0.000, 0.450]  (Bottom 75% of providers — clean billing history)
#   Medium   = (0.450, 0.520]  (75th–85th percentile — moderate billing & peer anomalies)
#   High     = (0.520, 0.580]  (85th–95th percentile — elevated peer & volume anomalies)
#   Critical = (0.580, 1.000]  (Top 5% highest risk providers + LEIE / Ghost Billing overrides)
TIER_BINS   = [0.00, 0.450, 0.520, 0.580, 1.00]
TIER_LABELS = ["Low", "Medium", "High", "Critical"]
TIER_COLORS = {"Low": "#4CAF50", "Medium": "#FFC107", "High": "#FF5722", "Critical": "#B71C1C"}

# ── Minimum Provider Claims Threshold for ML Behavioral Profiling ────────────
# Provider behavioral profiling requires sufficient claim history (n >= 5) to compute
# honest rate and variance metrics (e.g. std_claim_reimbursed, ghost_billing_rate).
# Payloads with fewer than 5 claims use LEIE Direct Exclusion + Rule-Based scoring
# with an explicit INSUFFICIENT_HISTORY_FOR_PROVIDER_ML status notice.
MIN_CLAIMS_FOR_PROVIDER_ML = 5

# ── Model Decision Threshold ───────────────────────────────────────────────────
# Used to binarise fraud probability into fraud_predicted = 0/1.
# Set at 0.40 to maximize recall (catching suspicious billing patterns)
FRAUD_THRESHOLD = 0.40
