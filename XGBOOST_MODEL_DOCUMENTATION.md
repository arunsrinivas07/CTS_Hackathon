# CareGuard AI — Medicare Provider-Level XGBoost Fraud Detection Engine (V2)

> [!IMPORTANT]
> **Decoupled Two-Layer Architecture (Version 2 Update)**:
> In Version 2, **HHS OIG LEIE compliance is completely decoupled from the XGBoost ML training pipeline**. 
> - **Layer 1 (Deterministic)**: `check_leie_direct_exclusion` in `backend2/main.py` performs direct NPI/Name lookups against `LEIE_MASTER.csv` and triggers a `1.00 Critical Risk` override for active exclusions.
> - **Layer 2 (Pure Behavioral ML)**: The XGBoost model (`train_xgboost_fraud_v2.py`) is trained on **59 pure behavioral & CMS peer features** (removing geographic LEIE state risk flags to eliminate bias).
> - **Single Source of Truth**: All risk tier boundaries (`TIER_BINS = [0.00, 0.465, 0.485, 0.520, 1.00]`) and decision threshold (`FRAUD_THRESHOLD = 0.40`) are defined centrally in `backend2/config.py`.
> - **Full Technical Reference**: See [VERSION_2_MODEL_EXPLANATION.md](VERSION_2_MODEL_EXPLANATION.md) for detailed frontend schemas and hybrid scoring.

---

## 1. Executive Summary & Objective

The **Medicare Provider-Level Fraud Detection Engine (V2)** is an end-to-end Machine Learning pipeline designed to detect fraudulent billing patterns across Medicare providers. Driven by **XGBoost (Extreme Gradient Boosting)**, the system evaluates provider-level billing anomalies, physician stacking, ghost beneficiary post-death billing, diagnosis/procedure code densities, and **CMS peer benchmarks** (specialty × state billing ratios across 8.2M CMS records).

---

## 2. 14-Step Training Pipeline Workflow (`train_xgboost_fraud_v2.py`)

The V2 pipeline script is structured into **14 distinct, modular steps**:

```
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ STEP 0: IMPORTS                                                             │
 │   • Core Data Science: NumPy, Pandas, Scikit-Learn, XGBoost                 │
 │   • Shared Config: FRAUD_THRESHOLD, TIER_BINS, TIER_LABELS (config.py)     │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
 ┌──────────────────────────────────────▼──────────────────────────────────────┐
 │ STEP 1: CONFIGURATION & PATH RESOLUTION                                     │
 │   • Datasets: KAGGLE_MASTER_TRAIN.csv, KAGGLE_MASTER_TEST.csv,             │
 │     CMS_PROVIDER_MASTER.csv                                                 │
 │   • Hyperparameters (TEST_SIZE=0.20, Stratified 5-Fold CV)                  │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
 ┌──────────────────────────────────────▼──────────────────────────────────────┐
 │ STEP 2: LOGGER SETUP (`setup_logger`)                                       │
 │   • Dual logging to stdout and `training_log_v2.txt`                        │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
 ┌──────────────────────────────────────▼──────────────────────────────────────┐
 │ STEP 3: DATA LOADING (`load_data`)                                          │
 │   • Ingests Kaggle master train/test sets & 47 CMS Provider Master columns   │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
 ┌──────────────────────────────────────▼──────────────────────────────────────┐
 │ STEP 4: PROVIDER-LEVEL AGGREGATION (`aggregate_to_provider`)                │
 │   • Aggregates claim rows into provider profiles (Ghost billing, ratios)   │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
 ┌──────────────────────────────────────▼──────────────────────────────────────┐
 │ STEP 5: CMS PEER BENCHMARK CONSTRUCTION (`build_cms_peer_benchmarks`)       │
 │   • Computes specialty × state provider billing averages across 8.2M CMS   │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
 ┌──────────────────────────────────────▼──────────────────────────────────────┐
 │ STEP 6: JOIN PEER FEATURES (`join_cms_peer_features`)                       │
 │   • Benchmarks against Internal Medicine specialty baseline per state       │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
 ┌──────────────────────────────────────▼──────────────────────────────────────┐
 │ STEP 7: PREPROCESSING & CHRONIC RECODING                                    │
 │   • Recodes chronic condition flags ({1: Yes, 2: No} → {1, 0})              │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
 ┌──────────────────────────────────────▼──────────────────────────────────────┐
 │ STEP 8: IMPUTATION & ENCODING (`impute_and_encode`)                         │
 │   • Train-only LabelEncoder (with UNKNOWN class) & median imputation        │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
 ┌──────────────────────────────────────▼──────────────────────────────────────┐
 │ STEP 9: EXPLORATORY DATA ANALYSIS (`run_eda`)                               │
 │   • Generates analytical EDA charts saved in `eda_plots/`                   │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
 ┌──────────────────────────────────────▼──────────────────────────────────────┐
 │ STEP 10: XGBOOST MODEL TRAINING (`train_xgboost`)                           │
 │   • Dynamic class weighting (`scale_pos_weight`), early stopping on AUCPR   │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
 ┌──────────────────────────────────────▼──────────────────────────────────────┐
 │ STEP 11: PER-TIER & MODEL EVALUATION (`evaluate_and_plot`)                  │
 │   • Stratified 5-fold CV, per-risk-tier precision/recall breakdown, plots   │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
 ┌──────────────────────────────────────▼──────────────────────────────────────┐
 │ STEP 12: SAVE MODEL ARTIFACTS (`save_artifacts`)                            │
 │   • Saves `xgboost_fraud_model_v2.pkl` and `cms_peer_benchmarks.csv`        │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
 ┌──────────────────────────────────────▼──────────────────────────────────────┐
 │ STEP 13: SCORE TEST SET & RISK TIERS (`score_test_and_save`)                │
 │   • Scores test providers & bins into risk tiers using config.py TIER_BINS  │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
 ┌──────────────────────────────────────▼──────────────────────────────────────┐
 │ STEP 14: MAIN ORCHESTRATOR (`main`)                                         │
 │   • Executes steps 1-13 in sequence and logs run status                      │
 └─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Minimal JSON Payload Compatibility Test

### Input Payload
```json
{
  "transaction_type": "MEDICAL_CLAIM",
  "claim_id": "CLM-LOW-001",
  "bene_id": "BENE-100",
  "provider_id": "9876543210",
  "claim_type": "carrier",
  "claim_start_date": "2009-06-15",
  "claim_end_date": "2009-06-15",
  "clm_pmt_amt": 85.00,
  "clm_tot_chrg_amt": 110.00,
  "line_count": 2,
  "diag_count": 1,
  "proc_count": 1
}
```

### Can Version 2 predict correctly on this minimal input?
**YES, absolutely.** 

The V2 inference pipeline (`run_inference_on_df` in `backend2/main.py`) performs automatic key translation and robust feature imputation:
1. **Field Mapping**:
   - `provider_id` → `Provider`
   - `claim_id` → `ClaimID`
   - `bene_id` → `BeneID`
   - `clm_pmt_amt` → `InscClaimAmtReimbursed` ($85.00)
   - `clm_tot_chrg_amt - clm_pmt_amt` → `DeductibleAmtPaid` ($25.00)
   - `claim_start_date` & `claim_end_date` → `ClaimStartDt` & `ClaimEndDt` (Duration = 1 day)
2. **Missing Field Imputation**: Missing optional fields (`State`, `ChronicCond_*`) are safely encoded via the `"UNKNOWN"` categorical class and median feature imputation trained on the master set.
3. **Execution Result**:
   - **Fraud Score**: `0.059` (5.9% probability)
   - **Risk Tier**: `Low`
   - **Scoring Status**: `SCORED_BY_HYBRID_ML`

---

## 4. Hyperparameters & Validation Strategy

| Parameter | Value | Description |
| :--- | :--- | :--- |
| `n_estimators` | `1000` | Maximum tree boosting iterations |
| `learning_rate` | `0.02` | Shrinkage factor |
| `max_depth` | `6` | Maximum tree depth |
| `scale_pos_weight` | `neg / pos` | Dynamically balances positive fraud sample weighting |
| `eval_metric` | `aucpr` | Area under Precision-Recall Curve early stopping metric |
| `early_stopping_rounds` | `40` | Halts training when validation AUCPR plateaus |
| `cross_validation` | `5-Fold Stratified` | Unbiased generalization estimation |

---

## 5. Validation Results & Performance Metrics

Evaluated on Stratified 5-Fold Cross-Validation and an independent **20% Validation Holdout Set**:

| Metric | Score | Interpretation |
| :--- | :--- | :--- |
| **Cross-Validation Mean ROC-AUC** | **0.9351 ± 0.0079** | Honest 5-fold cross-validation score across all folds |
| **Holdout ROC-AUC** | **0.9570** | Exceptional discrimination on held-out test split |
| **Holdout Avg Precision (AUCPR)** | **0.6724** | Strong precision across recall thresholds |
| **Decision Threshold** | **0.40** | Calibrated decision boundary (`config.py`) |

---

## 6. Complete Pure Behavioral & CMS Peer Feature Set Reference (59 Features)

### 1. Provider Volume & Claims Features (3 Features)
- `total_claims`, `unique_beneficiaries`, `claims_per_beneficiary`

### 2. Provider Financial & Billing Features (10 Features)
- `total_reimbursement`, `avg_claim_reimbursed`, `max_claim_reimbursed`, `std_claim_reimbursed`, `reimbursement_per_claim`, `avg_deductible_paid`, `avg_ip_annual_reimb`, `avg_op_annual_reimb`, `avg_total_annual_reimb`, `ip_vs_op_ratio`

### 3. Temporal & Billing Duration Features (2 Features)
- `avg_claim_duration`, `avg_los`

### 4. Beneficiary Demographics & Risk Features (4 Features)
- `avg_bene_age`, `avg_chronic_burden`, `renal_disease_rate`, `any_deceased_bene`

### 5. High-Risk Fraud Signals (6 Features)
- `ghost_billing_rate`, `ghost_billing_claim_count`, `physician_stacking_avg`, `max_physicians_on_claim`, `multi_physician_claim_pct`, `unusual_billing_combo_cnt`

### 6. Clinical Complexity Density Features (2 Features)
- `avg_diagnosis_density`, `avg_procedure_density`

### 7. Provider Chronic Condition Rates (11 Features)
- `cc_alzheimer_rate`, `cc_heartfailure_rate`, `cc_kidneydisease_rate`, `cc_cancer_rate`, `cc_obstrpulmonary_rate`, `cc_depression_rate`, `cc_diabetes_rate`, `cc_ischemicheart_rate`, `cc_osteoprorosis_rate`, `cc_rheumatoidarthritis_rate`, `cc_stroke_rate`

### 8. Provider Categorical Identity (1 Feature)
- `primary_state` (Encoded with `"UNKNOWN"` class handling)

### 9. CMS Specialty × State Peer Benchmarks & Billing Anomaly Ratios (20 Features)
- `charge_vs_peer_ratio` (Provider reimbursement / Peer submitted charge)
- `benes_vs_peer_ratio` (Beneficiary volume ratio)
- `avg_age_vs_peer` (Age distribution ratio)
- `chronic_burden_vs_peer_risk_proxy` (Chronic burden / Peer median risk score)
- `peer_median_drug_to_medical_ratio` (Drug vs. medical billing split)
- `peer_median_stdz_to_allowed_ratio` (Geographic standardized payment spread)
- `peer_median_pymt_to_charge_ratio` (Payment efficiency ratio)
- `peer_median_Tot_Sbmtd_Chrg` (State specialty submitted charge baseline)
- `peer_median_Tot_Mdcr_Pymt_Amt` (State specialty Medicare payment baseline)
- `peer_median_Tot_Benes` (State specialty beneficiary count baseline)
- `peer_median_Bene_Avg_Risk_Scre` (CMS beneficiary HCC risk score baseline)
- `peer_median_Rndrng_Prvdr_RUCA` (Rural-Urban Commuting Area index baseline)
- `peer_median_Drug_Sprsn_Ind` (Prescription data suppression rate)
- `peer_median_Bene_CC_BH_Alcohol_Drug_V1_Pct` (Substance abuse prevalence)
- `peer_median_Bene_CC_BH_Depress_V1_Pct` (Depression prevalence)
- `peer_median_Bene_CC_BH_PTSD_V1_Pct` (PTSD prevalence)
- `peer_median_Bene_CC_BH_Alz_NonAlzdem_V2_Pct` (Dementia prevalence)
- `peer_median_Bene_CC_PH_Diabetes_V2_Pct` (Diabetes prevalence)
- `peer_median_Bene_CC_PH_HF_NonIHD_V2_Pct` (Heart failure prevalence)
- `peer_median_Bene_CC_PH_CKD_V2_Pct` (Chronic kidney disease prevalence)
- `peer_median_Bene_CC_PH_IschemicHeart_V2_Pct` (Ischemic heart disease prevalence)
- `peer_median_Bene_CC_PH_Stroke_TIA_V2_Pct` (Stroke / TIA prevalence)
- `peer_median_Bene_CC_PH_Hypertension_V2_Pct` (Hypertension prevalence)
