"""
config.py — Single source of truth for shared constants across the V2 pipeline.
Import these in train_xgboost_fraud_v2.py, main.py, scoring, and evaluation.

IMPORTANT: Never define TIER_BINS, TIER_LABELS, or FRAUD_THRESHOLD locally in any module.
Always import from here so that training, validation, inference, and scored CSV all agree.
"""

# ── Risk Tier Bins ─────────────────────────────────────────────────────────────
# Calibrated from the KAGGLE_MASTER_TEST score distribution (Aug 2026 run).
# These are quantile-informed, not uniform:
#   Low      = [0.000, 0.465]  (majority of non-fraud providers cluster below 0.465)
#   Medium   = (0.465, 0.485]  (borderline region — monitor only)
#   High     = (0.485, 0.520]  (elevated risk — investigate on next cycle)
#   Critical = (0.520, 1.000]  (immediate investigation queue)
#
# NOTE: These are deliberately narrow around the decision boundary.
# If your score distribution shifts materially after retraining, re-calibrate
# these bins against the new fraud_predictions_providers.csv score percentiles.
TIER_BINS   = [0.00, 0.465, 0.485, 0.520, 1.00]
TIER_LABELS = ["Low", "Medium", "High", "Critical"]
TIER_COLORS = {"Low": "#4CAF50", "Medium": "#FFC107", "High": "#FF5722", "Critical": "#B71C1C"}

# ── Model Decision Threshold ───────────────────────────────────────────────────
# Used to binarise fraud probability into fraud_predicted = 0/1.
# Set conservatively at 0.40 to maximise recall (catching more fraud)
# at the cost of some precision. Adjust for investigator workload trade-off.
FRAUD_THRESHOLD = 0.40
