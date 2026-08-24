# CareGuard AI — Multi-Tier Healthcare Anomaly & Fraud Detection Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.6-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg?style=flat&logo=python)](https://www.python.org/)
[![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-1.4.2-F7931E.svg?style=flat&logo=scikitlearn)](https://scikit-learn.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?style=flat&logo=docker)](https://www.docker.com/)

**CareGuard AI** is an enterprise-grade Medicare Fraud, Waste, and Abuse (FWA) detection system. It combines **unsupervised point-of-service anomaly detection across all 7 CMS medical claim settings**, **dedicated Part D prescription drug event (PDE) anomaly detection**, and **deterministic HHS OIG regulatory compliance screening**.

---

## 🏛️ System Architecture Overview

```
                                ====================================================
                                  CAREGUARD AI DUAL-MODEL ANOMALY ARCHITECTURE
                                ====================================================

       RAW DATA SOURCES                                ML TRAINING & INGESTION PIPELINES                                 PRODUCTION INFERENCE
  ┌─────────────────────────┐              ┌─────────────────────────────────────────────────────────┐              ┌───────────────────────────┐
  │ 7 Medical Claim Types   │ ───────────► │ MODEL B PIPELINE (scripts/train_model_b.py)             │ ───────────► │ POST /api/v1/predict      │
  │ (Carrier, Inpatient,    │              │ • Median Imputer → StandardScaler → IsolationForest     │              │ (Claim-Level Medical)     │
  │ Outpatient, DME, etc.)  │              │ • 59 Features: Financial, Peer Ratios, Trajectory (30d) │              └─────────────┬─────────────┘
  └─────────────────────────┘              └─────────────────────────────────────────────────────────┘                            │
                                                                                                                                  │
  ┌─────────────────────────┐              ┌─────────────────────────────────────────────────────────┐                            │
  │ Part D Prescription     │ ───────────► │ MODEL C PIPELINE (scripts/train_model_c_pde.py)         │ ───────────► │ POST /api/v1/predict      │
  │ Drug Events (PDE)       │              │ • Median Imputer → StandardScaler → IsolationForest     │              │ (Part D Rx Anomaly)       │
  └─────────────────────────┘              │ • 32 Features: Refills, Unit Cost, Prescriber Velocity  │              └─────────────┬─────────────┘
                                           └─────────────────────────────────────────────────────────┘                            │
                                                                                                                                  │
  ┌─────────────────────────┐                                                                                                     │
  │ HHS OIG LEIE Master     │ ────────────────────────────── (Layer 0 Deterministic Gatekeeper) ──────────────────────────────────┘
  │ Exclusions Database     │                                 Direct NPI Exclusion Check & Risk Override
  └─────────────────────────┘
```

### Core Tiers & Capabilities:
1. **Layer 0: Deterministic Regulatory Gatekeeper (`backend/leie_checker.py`)**
   - Instant O(1) lookup against HHS Office of Inspector General (OIG) LEIE exclusions.
   - Automatically overrides any transaction to **1.00 Critical Risk** if the provider was excluded on the date of service.
2. **Model B: Point-of-Service Medical Claim Anomaly Detector (`models/model_b_claim/`)**
   - Unsupervised **Isolation Forest** (300 trees, 59 features) across all **7 CMS medical claim settings** (Carrier, Inpatient, Outpatient, DME, HHA, Hospice, SNF).
   - Evaluates multi-dimensional billing outliers, extreme length of stay, coding density stuffing, and setting-specific peer deviations.
3. **Model C: Part D Prescription Drug Event (PDE) Anomaly Detector (`models/model_c_pde/`)**
   - Dedicated pharmacy anomaly detector (300 trees, 32 features) evaluating pill-mill over-dispensing, refill frequency, daily unit pricing, and prescriber patient concentration.

---

## 📁 Repository Structure

```
c:/ML/
├── backend/                             # Production FastAPI Backend & Scoring Engines
│   ├── config.py                        # Centralized Risk Tiers & Threshold Configuration
│   ├── feature_engine.py                # Runtime 59/32 Feature Synthesis & History Lookups
│   ├── leie_checker.py                  # High-speed O(1) LEIE Exclusion Screener
│   └── main.py                          # FastAPI REST API Endpoints & Request Models
├── data/
│   ├── raw/                             # Raw Ingested CMS & LEIE Datasets
│   │   ├── beneficiary/                 # Beneficiary Annual Files (2015–2025)
│   │   ├── claims/                      # 7 Claim Types (carrier, inpatient, outpatient, etc.)
│   │   ├── leie/                        # LEIE_MASTER.csv (OIG Exclusion Master)
│   │   └── pde/                         # pde.csv (Part D Prescription Drug Events)
│   ├── processed/                       # Processed Training & Reference Data
│   │   ├── medical/                     # Normalized Medical Claims & Stratified Samples
│   │   ├── pde/                         # PDE Feature Matrix & Part D Datasets
│   │   └── reference/                   # Claim Stats, Stratification, & Feature Definitions
│   └── outputs/                         # Validation Reports, Test Scores, & Artifact Logs
├── models/                              # Serialized Production ML Artifacts
│   ├── model_b_claim/                   # Model B Isolation Forest, Imputer, Scaler, Calib
│   └── model_c_pde/                     # Model C Isolation Forest, Imputer, Scaler, Calib
├── scripts/                             # End-to-End ETL, Training & Validation Pipelines
│   ├── normalize_medical_claims.py      # Normalize 7 Claim Types to Unified Medical Schema
│   ├── build_bene_history_features.py   # Compute Point-in-Time Longitudinal Beneficiary Features
│   ├── compute_claim_type_stats.py      # Compute Setting Medians, MAD, & Percentile Anchors
│   ├── stratified_sample_model_b.py     # 3D Stratified Sampler (216,701 Training Rows)
│   ├── train_model_b.py                 # Train Model B Medical Anomaly Isolation Forest
│   ├── calibrate_model_b.py             # Calibrate Model B Raw Scores into Percentiles
│   ├── validate_model_b.py              # 9-Point Temporal Validation Suite (Untouched 2023 Data)
│   ├── build_pde_features.py            # Feature Engineering for Part D Pharmacy Transactions
│   ├── train_model_c_pde.py             # Train Model C PDE Rx Anomaly Isolation Forest
│   ├── calibrate_model_c_pde.py         # Calibrate Model C Raw Scores into Percentiles
│   ├── explain_anomaly_models.py        # SHAP Global Feature Importance & Explanations
│   └── leie_verification.py             # Audit & Verify LEIE Direct Exclusion Matching
├── tests/                               # Test Automation Suite
│   └── test_api_e2e.py                  # Comprehensive End-to-End API Test Suite
├── Dockerfile                           # Production Docker Container Specification
├── docker-compose.yml                   # Multi-container orchestration
├── requirements.txt                     # Pinned Python Dependencies
└── README.md                            # Main Project Documentation (This File)
```

---

## ⚡ Prerequisites & Installation

### 1. Python Environment
* Python **3.10** or **3.11** recommended.

```bash
# Clone or navigate to the workspace
cd c:\ML

# Create and activate virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 🔄 End-to-End Pipeline Execution Guide

You can reproduce the entire ETL, feature engineering, model training, and validation lifecycle using the modular scripts in `scripts/`:

### Phase 1: Medical Claims Normalization & Feature Pipeline
```bash
# 1. Normalize 7 raw claim CSVs into unified schema (1,888,860 rows)
python scripts/normalize_medical_claims.py

# 2. Build point-in-time longitudinal beneficiary history (Lifetime & 30D/90D windows)
python scripts/build_bene_history_features.py

# 3. Compute CMS claim-type peer benchmark statistics (Medians, MAD, Percentile anchors)
python scripts/compute_claim_type_stats.py

# 4. Generate 3D stratified sample (216,701 rows: CLAIM_TYPE × YEAR × PAYMENT_TIER)
python scripts/stratified_sample_model_b.py
```

### Phase 2: Model B (Medical Claims) Training, Calibration & Validation
```bash
# 5. Train Model B Isolation Forest (59 features, 300 trees)
python scripts/train_model_b.py

# 6. Generate empirical percentile calibration tables
python scripts/calibrate_model_b.py

# 7. Execute 9-point automated temporal validation on untouched 2023 test data
python scripts/validate_model_b.py
```

### Phase 3: Model C (Part D Prescription Drug Events) Pipeline
```bash
# 8. Extract 32 PDE features (unit cost, refill frequency, prescriber volume)
python scripts/build_pde_features.py

# 9. Train Model C Isolation Forest on historical data (YEAR <= 2022)
python scripts/train_model_c_pde.py

# 10. Calibrate Model C percentile scores
python scripts/calibrate_model_c_pde.py
```

### Phase 4: SHAP Feature Importance & Compliance Audits
```bash
# 11. Generate SHAP TreeExplainer feature importance rankings
python scripts/explain_anomaly_models.py

# 12. Audit LEIE exclusion database integrity
python scripts/leie_verification.py
```

---

## 🚀 Running the Production API Server

### Local Uvicorn Execution:
Start the high-performance FastAPI server with hot-reload enabled:

```bash
uvicorn backend.main:app --reload --port 8000
```

* **API Root:** `http://127.0.0.1:8000`
* **Interactive Swagger UI Documentation:** `http://127.0.0.1:8000/docs`
* **Redoc Documentation:** `http://127.0.0.1:8000/redoc`

### Docker Deployment:
```bash
# Build and run with Docker Compose
docker compose up --build -d

# Verify container status
docker compose ps
```

---

## 📡 REST API Reference & Sample Payloads

The API exposes the primary prediction endpoint:
* `POST /api/v1/predict` — Evaluates medical claims (Model B) or PDE prescription events (Model C) with automated LEIE screening.
* `GET /health` — Service health & artifact status.

---

### Sample Payloads for All 7 Medical Claim Types & PDE

#### 1. Inpatient Hospital Claim (`inpatient`)
```bash
curl -X POST http://localhost:8000/api/v1/predict \
     -H "Content-Type: application/json" \
     -d '{
       "transaction_type": "MEDICAL_CLAIM",
       "claim_id": "CLM-INP-88201",
       "bene_id": "-10000010254618",
       "provider_id": "011500",
       "at_physn_npi": "9999870899",
       "org_npi_num": "1578657367",
       "claim_type": "inpatient",
       "claim_start_date": "2022-03-10",
       "claim_end_date": "2022-03-17",
       "clm_pmt_amt": 14250.00,
       "clm_tot_chrg_amt": 18500.00,
       "line_count": 12,
       "unit_count": 7.0,
       "diag_count": 8,
       "proc_count": 3
     }'
```

#### 2. Outpatient Hospital Claim (`outpatient`)
```json
{
  "transaction_type": "MEDICAL_CLAIM",
  "claim_id": "CLM-OUT-55102",
  "bene_id": "-10000010254618",
  "provider_id": "01S023",
  "at_physn_npi": "9999995696",
  "org_npi_num": "1942394739",
  "claim_type": "outpatient",
  "claim_start_date": "2022-04-15",
  "claim_end_date": "2022-04-15",
  "clm_pmt_amt": 850.50,
  "clm_tot_chrg_amt": 1200.00,
  "line_count": 4,
  "unit_count": 4.0,
  "diag_count": 3,
  "proc_count": 2
}
```

#### 3. Carrier / Physician Claim (`carrier`)
```json
{
  "transaction_type": "MEDICAL_CLAIM",
  "claim_id": "CLM-CARR-10923",
  "bene_id": "-10000010254618",
  "provider_id": "1063654341",
  "at_physn_npi": "9999971093",
  "org_npi_num": "1063654341",
  "claim_type": "carrier",
  "claim_start_date": "2022-05-18",
  "claim_end_date": "2022-05-18",
  "clm_pmt_amt": 165.00,
  "clm_tot_chrg_amt": 220.00,
  "line_count": 2,
  "unit_count": 2.0,
  "diag_count": 2,
  "proc_count": 1
}
```

#### 4. Skilled Nursing Facility Claim (`snf`)
```json
{
  "transaction_type": "MEDICAL_CLAIM",
  "claim_id": "CLM-SNF-77402",
  "bene_id": "-10000010254618",
  "provider_id": "015037",
  "at_physn_npi": "9999841890",
  "org_npi_num": "1336780048",
  "claim_type": "snf",
  "claim_start_date": "2022-06-01",
  "claim_end_date": "2022-06-21",
  "clm_pmt_amt": 9850.00,
  "clm_tot_chrg_amt": 12400.00,
  "line_count": 6,
  "unit_count": 20.0,
  "diag_count": 5,
  "proc_count": 2
}
```

#### 5. Home Health Agency Claim (`hha`)
```json
{
  "transaction_type": "MEDICAL_CLAIM",
  "claim_id": "CLM-HHA-33910",
  "bene_id": "-10000010254850",
  "provider_id": "017879",
  "at_physn_npi": "9999873695",
  "org_npi_num": "1225513278",
  "claim_type": "hha",
  "claim_start_date": "2022-07-01",
  "claim_end_date": "2022-07-28",
  "clm_pmt_amt": 3450.00,
  "clm_tot_chrg_amt": 4200.00,
  "line_count": 8,
  "unit_count": 12.0,
  "diag_count": 4,
  "proc_count": 1
}
```

#### 6. Durable Medical Equipment Claim (`dme`)
```json
{
  "transaction_type": "MEDICAL_CLAIM",
  "claim_id": "CLM-DME-44019",
  "bene_id": "-10000010254618",
  "provider_id": "015037",
  "at_physn_npi": "9999841890",
  "org_npi_num": "1336780048",
  "claim_type": "dme",
  "claim_start_date": "2022-08-05",
  "claim_end_date": "2022-08-05",
  "clm_pmt_amt": 450.00,
  "clm_tot_chrg_amt": 600.00,
  "line_count": 2,
  "unit_count": 2.0,
  "diag_count": 2,
  "proc_count": 1
}
```

#### 7. Hospice Claim (`hospice`)
```json
{
  "transaction_type": "MEDICAL_CLAIM",
  "claim_id": "CLM-HOSP-99014",
  "bene_id": "-10000010254676",
  "provider_id": "011517",
  "at_physn_npi": "9999872291",
  "org_npi_num": "1861497935",
  "claim_type": "hospice",
  "claim_start_date": "2022-09-01",
  "claim_end_date": "2022-09-21",
  "clm_pmt_amt": 6200.00,
  "clm_tot_chrg_amt": 6200.00,
  "line_count": 3,
  "unit_count": 21.0,
  "diag_count": 3,
  "proc_count": 0
}
```

#### 8. Part D Prescription Drug Event (`pde`)
```json
{
  "transaction_type": "PDE",
  "pde_id": "PDE-RX-100293",
  "bene_id": "-10000010254618",
  "prscrbr_id": "9999987089",
  "srvc_dt": "2022-10-15",
  "qty_dspnsd_num": 60.0,
  "days_suply_num": 30.0,
  "fill_num": 1,
  "tot_rx_cst_amt": 450.00,
  "ptnt_pay_amt": 25.00,
  "cvrd_d_plan_pd_amt": 425.00,
  "ncvrd_plan_pd_amt": 0.0,
  "gdc_blw_oopt_amt": 0.0,
  "gdc_abv_oopt_amt": 0.0,
  "othr_troop_amt": 0.0,
  "lics_amt": 0.0,
  "plro_amt": 0.0,
  "brnd_gnrc_cd": "G",
  "phrmcy_srvc_type_cd": 1
}
```

---

## 🎯 Risk Scoring & Calibration Mechanics

### 1. Empirical Percentile Calibration
Raw Isolation Forest decision scores are converted to setting-specific risk scores:
$$\text{Calibrated Risk Score} = \left(1 - \frac{\text{Percentile Rank within Setting}}{100}\right) \times 100$$

### 2. Actionable Operational Tiers
| Final Score | Risk Tier | Operational & Clinical Action |
|:---:|:---:|---|
| **$80 – 100$** | **CRITICAL** | **Immediate Payment Freeze** $\rightarrow$ Referred to Special Investigations Unit (SIU) or LEIE enforcement. |
| **$60 – 79$** | **HIGH** | **Pre-Payment Medical Review** $\rightarrow$ Medical records & itemized coding review required. |
| **$40 – 59$** | **MEDIUM** | **Post-Payment Routine Audit** $\rightarrow$ Queued for retrospective peer review. |
| **$0 – 39$** | **LOW** | **Auto-Adjudicated / Approved** $\rightarrow$ Cleared for standard Medicare payment. |

---

## 🧪 Automated Testing Suite

CareGuard AI includes comprehensive automated integration and unit tests:

```bash
# Run the full end-to-end API test suite
pytest tests/test_api_e2e.py -v
```

### Coverage Includes:
* End-to-end scoring across all 7 medical claim types.
* Part D PDE prescription anomaly detection and SHAP explanations.
* LEIE direct NPI exclusion detection and Critical 1.00 overrides.
* Null handling and unknown entity fallback imputation.