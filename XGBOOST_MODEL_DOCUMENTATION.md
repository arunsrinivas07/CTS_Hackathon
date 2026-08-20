# CareGuard AI — Medicare Provider-Level XGBoost Fraud Detection Engine (V2)

> [!IMPORTANT]
> **Decoupled Two-Layer Architecture (Version 2 Update)**:
> In Version 2, **HHS OIG LEIE compliance is completely decoupled from the XGBoost ML training pipeline**. 
> - **Layer 1 (Deterministic)**: `check_leie_direct_exclusion` in `backend2/main.py` performs direct NPI/Name lookups against `LEIE_MASTER.csv` and triggers a `1.00 Critical Risk` override for active exclusions.
> - **Layer 2 (Pure Behavioral ML)**: The XGBoost model (`train_xgboost_fraud_v2.py`) is trained on **46 pure behavioral features** (removing geographic LEIE state risk flags to eliminate bias).
> - **Full Technical Reference**: See [VERSION_2_MODEL_EXPLANATION.md](VERSION_2_MODEL_EXPLANATION.md) for detailed frontend schemas and hybrid scoring.

---

## 1. Executive Summary & Objective

The **Medicare Provider-Level Fraud Detection Engine (V2)** is an end-to-end Machine Learning pipeline designed to detect fraudulent billing patterns across Medicare providers. Driven by **XGBoost (Extreme Gradient Boosting)**, the system evaluates provider-level billing anomalies, physician stacking, ghost beneficiary post-death billing, diagnosis/procedure code densities, and CMS peer benchmarks (specialty × state billing ratios).

---

## 2. 14-Step Training Pipeline Workflow (`train_xgboost_fraud_v2.py`)

The V2 pipeline script is structured into **14 distinct, modular steps**:

```
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ STEP 0: IMPORTS                                                             │
 │   • Core Data Science: NumPy, Pandas, Scikit-Learn, XGBoost                 │
 │   • Plotting: Matplotlib, Seaborn                                           │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
 ┌──────────────────────────────────────▼──────────────────────────────────────┐
 │ STEP 1: CONFIGURATION & PATH RESOLUTION                                     │
 │   • Datasets: KAGGLE_MASTER_TRAIN.csv, KAGGLE_MASTER_TEST.csv,             │
 │     CMS_PROVIDER_MASTER.csv                                                 │
 │   • Hyperparameters (TEST_SIZE=0.20, FRAUD_THRESHOLD=0.40)                  │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
 ┌──────────────────────────────────────▼──────────────────────────────────────┐
 │ STEP 2: LOGGER SETUP (`setup_logger`)                                       │
 │   • Dual logging to stdout and `training_log_v2.txt`                        │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
 ┌──────────────────────────────────────▼──────────────────────────────────────┐
 │ STEP 3: DATA LOADING (`load_data`)                                          │
 │   • Ingests Kaggle master train/test sets & chunked CMS Provider Master    │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
 ┌──────────────────────────────────────▼──────────────────────────────────────┐
 │ STEP 4: PROVIDER-LEVEL AGGREGATION (`aggregate_to_provider`)                │
 │   • Aggregates claim rows into provider profiles (Ghost billing, ratios)   │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
 ┌──────────────────────────────────────▼──────────────────────────────────────┐
 │ STEP 5: CMS PEER BENCHMARK CONSTRUCTION (`build_cms_peer_benchmarks`)       │
 │   • Computes state-level provider billing averages across 8.2M CMS records   │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
 ┌──────────────────────────────────────▼──────────────────────────────────────┐
 │ STEP 6: JOIN PEER FEATURES (`join_cms_peer_features`)                       │
 │   • Computes provider billing ratios vs. state peers (Reimbursement Ratio)  │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
 ┌──────────────────────────────────────▼──────────────────────────────────────┐
 │ STEP 7: PREPROCESSING & CHRONIC RECODING                                    │
 │   • Recodes chronic condition flags ({1: Yes, 2: No} → {1, 0})              │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
 ┌──────────────────────────────────────▼──────────────────────────────────────┐
 │ STEP 8: IMPUTATION & ENCODING (`impute_and_encode`)                         │
 │   • Train-only LabelEncoder fitting & median imputation (Zero Data Leakage) │
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
 │ STEP 11: MODEL EVALUATION & PLOTTING (`evaluate_and_plot`)                  │
 │   • ROC-AUC, PR curve, confusion matrix, and feature importances by Gain    │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
 ┌──────────────────────────────────────▼──────────────────────────────────────┐
 │ STEP 12: SAVE MODEL ARTIFACTS (`save_artifacts`)                            │
 │   • Saves `xgboost_fraud_model_v2.pkl` and `cms_peer_benchmarks.csv`        │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
 ┌──────────────────────────────────────▼──────────────────────────────────────┐
 │ STEP 13: SCORE TEST SET & RISK TIERS (`score_test_and_save`)                │
 │   • Scores test providers & bins into risk tiers (Low, Medium, High, Critical)│
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
 ┌──────────────────────────────────────▼──────────────────────────────────────┐
 │ STEP 14: MAIN ORCHESTRATOR (`main`)                                         │
 │   • Executes steps 1-13 in sequence and logs run status                      │
 └─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Step-by-Step Breakdown

### Step 0: Imports
Loads essential libraries: `pandas`, `numpy`, `xgboost.XGBClassifier`, `sklearn.preprocessing.LabelEncoder`, `sklearn.metrics`, `matplotlib`, and `seaborn`.

### Step 1: Configuration & Path Resolution
Defines relative path resolution for execution from `F:\CTS_main\` or `backend2/`:
- `RANDOM_STATE = 42`
- `TEST_SIZE = 0.20` (80/20 stratified validation split)
- `FRAUD_THRESHOLD = 0.40` (calibrated decision threshold)

### Step 2: Logger Setup (`setup_logger`)
Configures dual file-and-console logging stored at `backend2/models/xgboost_fraud_v2/training_log_v2.txt`.

### Step 3: Data Loading (`load_data`)
Ingests CMS Kaggle master training set (`558,211` claims), test set (`135,392` claims), and chunked `CMS_PROVIDER_MASTER.csv` (`8,253,347` provider rows).

### Step 4: Provider-Level Aggregation (`aggregate_to_provider`)
Aggregates claim-level rows to one row per Provider ID:
- **Ghost Billing Rate**: Proportion of claims submitted after beneficiary death (`ClaimStartDt > DOD`).
- **Physician Stacking**: Average count of unique attending, operating, and other physicians per claim.
- **Diagnosis/Procedure Density**: Average count of diagnosis (1-10) and procedure (1-6) codes per claim.

### Step 5 & 6: CMS Peer Benchmark Construction & Join (`build_cms_peer_benchmarks` & `join_cms_peer_features`)
Computes state-level provider billing averages across 8.2M CMS records and joins peer benchmark ratios:
- `Reimbursement_vs_StatePeer_Ratio`: Provider average reimbursement divided by state peer average.

### Step 7: Preprocessing & Chronic Recoding (`recode_chronic`)
Recodes CMS chronic condition flags from `{1: Yes, 2: No}` to `{1: Yes, 0: No}` and computes chronic burden scores.

### Step 8: Imputation & Encoding (`impute_and_encode`)
Fits `LabelEncoder` objects and computes medians **strictly on training data** to prevent data leakage. Unseen test categories are handled safely.

### Step 9: Exploratory Data Analysis (`run_eda`)
Generates EDA charts saved in `backend2/models/xgboost_fraud_v2/eda_plots/`.

### Step 10: XGBoost Model Training (`train_xgboost`)
Trains an `XGBClassifier` with:
- Dynamic class weight balancing: `scale_pos_weight = neg / pos`
- Early stopping: `early_stopping_rounds = 40` evaluated on validation AUCPR (`eval_metric="aucpr"`).

### Step 11: Model Evaluation & Plotting (`evaluate_and_plot`)
Computes accuracy metrics and saves performance plots in `backend2/models/xgboost_fraud_v2/model_plots/`:
1. `01_roc_curve.png`
2. `02_precision_recall_curve.png`
3. `03_confusion_matrix.png`
4. `04_feature_importance.png`

### Step 12: Save Model Artifacts (`save_artifacts`)
Serializes model, encoders, medians, thresholds, and peer lookup tables to `xgboost_fraud_model_v2.pkl` and `cms_peer_benchmarks.csv`.

### Step 13: Score Test Set & Risk Tiers (`score_test_and_save`)
Scores provider test set and bins risk tiers (`Low`, `Medium`, `High`, `Critical`).

### Step 14: Main Orchestrator (`main`)
Orchestrates steps 1 through 13 in sequence.

---

## 4. Hyperparameters & Class Imbalance Strategy

| Parameter | Value | Description |
| :--- | :--- | :--- |
| `n_estimators` | `1000` | Maximum tree boosting iterations |
| `learning_rate` | `0.02` | Shrinkage factor |
| `max_depth` | `6` | Maximum tree depth |
| `scale_pos_weight` | `neg / pos` | Dynamically balances positive fraud sample weighting |
| `eval_metric` | `aucpr` | Area under Precision-Recall Curve early stopping metric |
| `early_stopping_rounds` | `40` | Halts training when validation AUCPR plateaus |

---

## 5. Validation Results & Performance Metrics

Evaluated on an independent **20% Stratified Validation Holdout Set** (`1,082` providers):

| Metric | Score | Interpretation |
| :--- | :--- | :--- |
| **ROC-AUC** | **0.9468** | Exceptional discrimination between legitimate and fraudulent providers |
| **Avg Precision (AUCPR)** | **0.6823** | Strong precision across recall thresholds |
| **Decision Threshold** | **0.40** | Calibrated decision boundary |

---

## 6. Complete Pure Behavioral Feature Set Reference (46 Features)

### Financial & Reimbursement (11 Features)
- `InscClaimAmtReimbursed`, `DeductibleAmtPaid`, `IPAnnualReimbursementAmt`, `IPAnnualDeductibleAmt`, `OPAnnualReimbursementAmt`, `OPAnnualDeductibleAmt`, `ReimbursementPerDay`, `DeductibleRatio`, `IPvsOPReimbursementRatio`, `TotalAnnualReimbursement`, `TotalAnnualDeductible`

### Temporal & Billing Duration (4 Features)
- `ClaimDurationDays`, `AdmissionToDischarge`, `AgeAtClaim`, `ClaimAfterDeath` (Ghost beneficiary flag)

### Beneficiary Demographics (4 Features)
- `Gender`, `Race`, `RenalDiseaseIndicator`, `IsDead`

### Coverage & Insurance (4 Features)
- `NoOfMonths_PartACov`, `NoOfMonths_PartBCov`, `PartACoverageGap`, `PartBCoverageGap`

### Physician Interactions (4 Features)
- `HasAttendingPhysician`, `HasOperatingPhysician`, `HasOtherPhysician`, `PhysicianCount`

### Clinical Diagnosis & Procedure (3 Features)
- `DiagnosisCodeCount`, `ProcedureCodeCount`, `HasAdmitDiagnosis`

### Chronic Condition Burden (11 Features)
- `Chronic_Alzheimer`, `Chronic_HeartFailure`, `Chronic_KidneyDisease`, `Chronic_Cancer`, `Chronic_COPD`, `Chronic_Depression`, `Chronic_Diabetes`, `Chronic_IschemicHeart`, `Chronic_Osteoprorosis`, `Chronic_RheumatoidArthritis`, `Chronic_Stroke`

### CMS State Peer Benchmarks (5 Features)
- `Reimbursement_vs_StatePeer_Ratio`, `State_Peer_Avg_Services`, `State_Peer_Avg_Reimbursement`, `State_Peer_Avg_RiskScore`, `State_Peer_Diabetes_Pct`
