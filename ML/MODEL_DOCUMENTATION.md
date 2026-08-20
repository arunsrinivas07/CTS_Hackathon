# Medicare Fraud, Waste & Abuse (FWA) Detection System
## End-to-End Technical & Model Architecture Documentation

---

```
                                  ==================================================
                                    HEALTHCARE ANOMALY DETECTION ENGINE ARCHITECTURE
                                  ==================================================

   +----------------------------------------------------------------------------------------------------+
   |                                        DATA INGESTION LAYER                                        |
   |                                                                                                    |
   |   +--------------------------+   +--------------------------+   +------------------------------+   |
   |   |   7 Medical Claim Types  |   |   Beneficiary Summaries  |   |   Prescription Drug Events   |   |
   |   |   (Carrier, Inpatient,   |   |   (2015-2025 Demographics,  |   |   (Part D PDE Transactions,  |   |
   |   |   Outpatient, DME, HHA,  |   |   Mortality, Multi-Year      |   |   Dosage, Cost Sharing,      |   |
   |   |   Hospice, SNF)          |   |   Historical Enrollment)     |   |   Days Supply, Refills)      |   |
   |   +------------+-------------+   +------------+-------------+   +--------------+---------------+   |
   +----------------|------------------------------|--------------------------------|-------------------+
                    |                              |                                |
                    v                              v                                v
   +----------------------------------------------------------------------------------------------------+
   |                                 DATA CLEANING & HARMONIZATION                                      |
   |  * Strict Schema Normalization (Canonical Column Mapping across all 7 Claim Types)                 |
   |  * Date Standardization (dd-Mon-YYYY -> ISO-8601 & Epoch Integers)                                 |
   |  * Missingness Resolution (Sentinel Handling & Zero-Floor Duration Logic)                          |
   |  * Strict Separation: Medical Claims and Prescription (PDE) Never Blended                          |
   +-----------------------------------------------+--------------------------------+-------------------+
                                                   |                                |
                                                   v                                v
   +----------------------------------------------------------------+  +--------------------------------+
   |             FEATURE ENGINEERING LAYER (MEDICAL)                |  |   FEATURE ENGINEERING (PDE)    |
   |  * 59 Dimension Multi-Scale Representation                     |  |  * 32 Dimension Feature Vector |
   |  * Derived Financial & Intensity Ratios                        |  |  * Financial Share & Velocity  |
   |  * Peer-Comparison Statistics (Robust Z & Percentiles)         |  |  * Beneficiary Prior Rx Traj.  |
   |  * Temporal Cumulative & Windowed History (30d / 90d)          |  |  * Prescriber Velocity Trends  |
   |  * Zero Future Leakage (Strict Point-in-Time Causality)        |  |  * Point-in-Time History Only  |
   +-------------------------------+--------------------------------+  +----------------+---------------+
                                   |                                                    |
                                   v                                                    v
   +----------------------------------------------------------------+  +--------------------------------+
   |            STRATIFIED SAMPLING & TEMPORAL SPLIT                |  |   TEMPORAL SPLIT (PDE MODEL)   |
   |  * Training Period: 2014 - 2022 (216,701 Stratified Rows)      |  |  * Train: <= 2022 (501,190)    |
   |  * Held-Out Future Test: 2023 (50,579 Untouched Rows)          |  |  * Test:  2023    (14,330)     |
   |  * Joint Strata: Claim Type x Year x Payment Tiers             |  |  * Zero Leakage Verification   |
   +-------------------------------+--------------------------------+  +----------------+---------------+
                                   |                                                    |
                                   v                                                    v
   +----------------------------------------------------------------+  +--------------------------------+
   |              MODEL B: MEDICAL ANOMALY DETECTOR                 |  |    MODEL C: PDE RX DETECTOR    |
   |  * Algorithm: Isolation Forest (300 Trees, max_samples=256)    |  |  * Isolation Forest (300 Trees)|
   |  * Median Imputation + Standard Scaling (Fit on Train Only)    |  |  * Imputation + Standard Scale |
   |  * Claim-Type-Specific Percentile Calibration [0 - 100]        |  |  * Empirical Percentile Calib. |
   +-------------------------------+--------------------------------+  +----------------+---------------+
                                   |                                                    |
                                   +-----------------------+----------------------------+
                                                           |
                                                           v
   +----------------------------------------------------------------------------------------------------+
   |                                POST-SCORING COMPLIANCE & EXPLAINABILITY                            |
   |                                                                                                    |
   |   +-----------------------------------------------+  +-----------------------------------------+   |
   |   |        LEIE DETERMINISTIC VERIFICATION        |  |       LOCAL & GLOBAL EXPLAINABILITY     |   |
   |   |  * OIG LEIE Master Exclusion Index (543 NPIs) |  |  * TreeSHAP Exact Decomposition         |   |
   |   |  * Service Date vs. Exclusion Period Checking |  |  * Top 5 Anomaly Drivers                |   |
   |   |  * Additive Risk Adjustment (+30 pts, max 100)|  |  * Top 3 Normalizing Mitigators         |   |
   |   |  * Statutory Citation & Regulatory Breakdown  |  |  * Full Audit Trail & Human Evidence    |   |
   |   +-----------------------+-----------------------+  +--------------------+--------------------+   |
   +---------------------------|-----------------------------------------------|------------------------+
                               |                                               |
                               +-----------------------+-----------------------+
                                                       |
                                                       v
   +----------------------------------------------------------------------------------------------------+
   |                                    PRODUCTION FASTAPI SERVICE                                      |
   |  * Endpoints: POST /api/v1/predict | GET /health | Interactive Swagger UI (/docs)                  |
   |  * Sub-10ms Inference Latency, Complete Pydantic Schema Validation, Human-in-the-Loop Disclaimers |
   +----------------------------------------------------------------------------------------------------+
```

---

## 1. Problem Statement

Medicare Fraud, Waste, and Abuse (FWA) accounts for an estimated **$60 billion to $100 billion in improper payments annually** across the United States healthcare system. Traditional detection mechanisms rely on static, rule-based claim edits or post-payment retrospective audits that suffer from major vulnerabilities:
1. **Rule Evasion**: Fraudulent actors rapidly mutate billing patterns, split claims across multiple taxonomy codes, or bill just below review thresholds to bypass rigid heuristic rules.
2. **High Latency & "Pay-and-Chase"**: Audits conducted months or years after reimbursement result in low fund recovery rates, high legal costs, and unmitigated leakage.
3. **High False Positive Rates**: Rigid thresholds penalize complex, legitimate clinical cases (e.g., intensive inpatient surgeries or rare specialty pharmacy treatments).
4. **Lack of Explainability**: Black-box scoring creates investigator fatigue and hinders regulatory compliance actions.

### Core Objectives
This platform provides an **unsupervised, multi-tiered statistical anomaly detection and compliance verification architecture** designed to score medical claims and prescription events in real-time. The system:
- Isolates multi-dimensional behavioral, financial, and clinical outliers across all major Medicare claim settings.
- Maintains strict temporal causality to avoid data leakage.
- Incorporates deterministic OIG List of Excluded Individuals and Entities (LEIE) compliance screening.
- Produces TreeSHAP-driven feature explanations for transparent, human-in-the-loop review.

---

## 2. Dataset Inventory

The project is built upon historical Medicare longitudinal data spanning **2014 through 2025**, comprising millions of claims, beneficiary profiles, pharmacy records, and regulatory exclusion lists.

| Dataset Domain | File Path / Source | Temporal Span | Total Record Count | Description & Scope |
|---|---|---|---|---|
| **Carrier Claims** | `data/raw/claims/carrier.csv` | 2015–2023 | 1,121,004 claims | Non-institutional physician, lab, and clinical specialist claims. |
| **Inpatient Claims** | `data/raw/claims/inpatient.csv` | 2015–2023 | 58,066 claims | Acute inpatient hospital stays, DRG assignments, and surgical procedures. |
| **Outpatient Claims** | `data/raw/claims/outpatient.csv` | 2015–2023 | 575,092 claims | Hospital outpatient department, clinic, and day-surgery visits. |
| **DME Claims** | `data/raw/claims/dme.csv` | 2015–2023 | 103,828 claims | Durable Medical Equipment, Prosthetics, Orthotics, and Supplies. |
| **HHA Claims** | `data/raw/claims/hha.csv` | 2015–2023 | 6,215 claims | Home Health Agency episodes of care and skilled nursing visits. |
| **Hospice Claims** | `data/raw/claims/hospice.csv` | 2014–2023 | 12,107 claims | Palliative and terminal care claims. |
| **SNF Claims** | `data/raw/claims/snf.csv` | 2015–2023 | 12,548 claims | Skilled Nursing Facility rehabilitation and extended post-acute care. |
| **Beneficiary History** | `data/raw/beneficiary/beneficiary_*.csv` | 2015–2025 (11 files) | 1,888,860 rows | Annual beneficiary demographic snapshots, state codes, mortality, and chronic flags. |
| **Prescription Events** | `data/raw/pde/pde.csv` | 2015–2023 | 515,520 rows | Medicare Part D Prescription Drug Event (PDE) transaction records. |
| **OIG LEIE Master** | `data/raw/leie/LEIE_MASTER.csv` | Active Master File | 543 distinct NPIs | Office of Inspector General List of Excluded Individuals/Entities. |

---

## 3. Seven Medical Claim Types

Medical claims are categorized into seven distinct clinical and institutional operational environments, each exhibiting unique cost distributions, lengths of stay, and billing characteristics:

```
+---------------------------------------------------------------------------------------------------+
| Setting     | Median Payment | Median Duration | Key Clinical Characteristics                     |
|-------------+----------------+-----------------+--------------------------------------------------|
| Carrier     | $995.35        | 0 days (Point)  | Professional services; high volume, low variance |
| DME         | $0.00 - $6.56  | 0 days (Point)  | Equipment leases & supplies; specific HCPCS codes|
| HHA         | $8,823.69      | 45-60 days      | Episodic home nursing; recurring visits          |
| Hospice     | $13,374.32     | 30-90 days      | Continuous palliative care; per-diem billing     |
| Inpatient   | $1,476.60      | 3-7 days        | Severe acute events; heavy right-skew (max $598k)|
| Outpatient  | $1,003.50      | 0-1 days        | Ambulatory surgical & diagnostic procedures      |
| SNF         | $13,098.21     | 20-100 days     | Extended physical therapy & post-acute nursing   |
+---------------------------------------------------------------------------------------------------+
```

### Claim Type Specifications
1. **Carrier (Professional / Part B)**: Submitted by independent physicians and group practices. Evaluated primarily on procedure counts, diagnosis density, and billing velocity relative to provider peers.
2. **Durable Medical Equipment (DME)**: Specialized medical appliances. High risk for unbundling and phantom billing; evaluated against submitted charge vs. payment ratios and quantity velocity.
3. **Home Health Agency (HHA)**: Billed as 30- or 60-day episodic units. Monitored for excessive episode duration, high payment per visit, and rapid re-certification.
4. **Hospice**: Per-diem palliative care. Analyzed for outlier episode durations and billing continuity anomalies.
5. **Inpatient (Part A)**: High-dollar institutional stays. Scored on length of stay (LOS), DRG intensity, procedure-to-diagnosis ratios, and total charges.
6. **Outpatient (Part B Institutional)**: High-frequency hospital clinic visits. Monitored for service unit inflation and unexpected multi-procedure unbundling.
7. **Skilled Nursing Facility (SNF)**: Post-acute convalescent care with daily benefit limits (up to 100 days). Evaluated on stay lengths and cumulative per-patient billing caps.

---

## 4. Beneficiary Data

Beneficiary files provide annual longitudinal demographic and status indicators across 11 calendar years (2015–2025).

### Key Beneficiary Attributes
- `BENE_ID`: Canonical beneficiary identifier linking claims across institutional, professional, and pharmacy settings.
- `BENE_BIRTH_DT` & `BENE_AGE_AT_CLAIM`: Point-in-time age dynamically computed at claim service date. Allows detection of pediatric billing in Medicare or claims for deceased patients.
- `BENE_DEATH_DT` & `BENE_IS_DECEASED`: Binary flag and date verifying whether service dates occurred post-mortem (a classic indicator of identity theft and phantom billing).
- `SEX_IDENT_CD` & `BENE_RACE_CD`: Demographic attributes used for baseline cohort normalization.
- `STATE_CODE`: Geographic territory code used to detect cross-state billing irregularities.

### Longitudinal Beneficiary Linkage
Each medical and PDE transaction is joined against the beneficiary’s historical record up to the day of service, computing prior utilization trajectory without looking ahead into future records.

---

## 5. PDE Data (Prescription Drug Events)

Medicare Part D (PDE) transactions capture retail, mail-order, and institutional drug dispensing events. **PDE data is strictly separated from Medical Claims** into a dedicated anomaly detection pipeline (Model C) because pharmacy claims follow distinct transactional rules, payment structures, and dispensing cadences.

### PDE Transactional Attributes
- `PDE_ID`, `BENE_ID`, `PRSCRBR_ID`: Transaction, patient, and prescriber identifiers.
- `SRVC_DT`: Date prescription was filled.
- `QTY_DSPNSD_NUM`: Metric quantity of drug units (tablets, capsules, milliliters).
- `DAYS_SUPLY_NUM`: Estimated day duration of the dispensed supply (e.g., 30, 90 days).
- `FILL_NUM`: Refill sequence number (0 = original dispensing, 1–99 = refills).
- `TOT_RX_CST_AMT`: Gross prescription cost.
- **Payment Breakdown Fields**:
  - `PTNT_PAY_AMT`: Beneficiary out-of-pocket copay/coinsurance.
  - `CVRD_D_PLAN_PD_AMT`: Amount paid by Part D plan under standard benefit.
  - `NCVRD_PLAN_PD_AMT`: Non-covered payment amount.
  - `GDC_BLW_OOPT_AMT` & `GDC_ABV_OOPT_AMT`: Gross drug cost below/above out-of-pocket threshold.
  - `LICS_AMT`: Low-Income Cost-Sharing Subsidy amount.
  - `PLRO_AMT`: Patient Liability Reduction for Other third-party payers.

---

## 6. Data Cleaning & Preprocessing

Raw CMS data contains disparate formats, legacy coding, and missing values across claim types. A centralized normalization engine (`scripts/normalize_medical_claims.py`) harmonizes all sources into unified representations.

```
                    RAW CMS CLAIM SOURCES (7 Types)
  [Carrier] [Inpatient] [Outpatient] [DME] [HHA] [Hospice] [SNF]
                         |
                         v
  +-------------------------------------------------------------+
  |              SCHEMA HARMONIZATION & MAPPING                 |
  |  * Resolve Provider ID priority:                            |
  |    ORG_NPI_NUM -> AT_PHYSN_NPI -> PRF_PHYSN_NPI -> PRVDR_NUM|
  |  * Map Submitted Charges:                                   |
  |    CLM_TOT_CHRG_AMT vs NCH_CARR_CLM_SBMTD_CHRG_AMT          |
  |  * Standardize Dates: dd-Mon-YYYY -> ISO YYYY-MM-DD         |
  |  * Preserve Raw Values with 'SRC__' Prefix                  |
  +-------------------------------------------------------------+
                         |
                         v
            UNIFIED NORMALIZED CLAIMS TABLE
```

### Preprocessing Protocol
1. **Schema Harmonization**: Mapped heterogeneous columns (e.g., `CLM_LINE_NUM` vs. `LINE_NUM`, `REV_CNTR_UNIT_CNT` vs. `LINE_SRVC_CNT`) into canonical normalized fields.
2. **Provider Hierarchy Resolution**: Applied deterministic coalesce logic across attending physician, operating physician, referring physician, and organization NPIs.
3. **Date Standardization**: Parsed text dates (e.g., `16-Mar-2015`) into valid ISO dates and derived integer epoch days for sliding window computations.
4. **Invalid Duration Correction**: In cases where `CLAIM_END_DATE` was prior to `CLAIM_START_DATE`, `CLAIM_DURATION_DAYS` was set to `0` or `NaN` rather than negative values.
5. **Preservation of Raw Fields**: Kept all original raw columns with `SRC__` prefix for downstream auditability.

---

## 7. Medical Feature Engineering (Model B — 59 Features)

Model B transforms raw medical claims into a **59-dimensional vector** capturing point-in-time financials, intensity ratios, peer deviations, demographic context, and longitudinal beneficiary history.

```
+------------------------------------------------------------------------------------------------------+
| Feature Category       | Count | Key Features & Formulations                                         |
|------------------------+-------+---------------------------------------------------------------------|
| Core Transactional     | 9     | YEAR, CLM_PMT_AMT, CLM_TOT_CHRG_AMT, UNPAID_CHARGE,                  |
|                        |       | CLAIM_DURATION_DAYS, LINE_COUNT, UNIT_COUNT, DIAG_COUNT, PROC_COUNT |
|------------------------+-------+---------------------------------------------------------------------|
| Financial & Intensity  | 4     | PAYMENT_PER_LINE = CLM_PMT_AMT / LINE_COUNT                          |
| Ratios                 |       | CHARGE_PER_LINE  = CLM_TOT_CHRG_AMT / LINE_COUNT                     |
|                        |       | PAYMENT_PER_UNIT = CLM_PMT_AMT / UNIT_COUNT                          |
|                        |       | CHARGE_PER_UNIT  = CLM_TOT_CHRG_AMT / UNIT_COUNT                     |
|------------------------+-------+---------------------------------------------------------------------|
| Peer Comparison Stats  | 18    | For each metric m in {Payment, Charge, Duration, Lines, Diags, Procs}|
| (Within Claim Type)    |       | 1. Metric_VS_TYPE_MEDIAN = Value / Median_m                         |
|                        |       | 2. Metric_TYPE_ROBUST_Z  = (Value - Median_m) / (1.4826 * MAD_m)    |
|                        |       | 3. Metric_TYPE_PERCENTILE = Empirical Percentile Rank [0 - 100]      |
|------------------------+-------+---------------------------------------------------------------------|
| Beneficiary Point-in-  | 2     | PAYMENT_VS_BENE_PREV_AVG = CLM_PMT_AMT / HIST_PREV_AVG_PAY          |
| Time Comparisons       |       | PAYMENT_VS_BENE_PREV_MAX = CLM_PMT_AMT / HIST_PREV_MAX_PAY          |
|------------------------+-------+---------------------------------------------------------------------|
| Beneficiary Demographics| 5    | BENE_AGE_AT_CLAIM, BENE_IS_DECEASED, SEX_IDENT_CD, BENE_RACE_CD,    |
|                        |       | STATE_CODE                                                          |
|------------------------+-------+---------------------------------------------------------------------|
| Longitudinal History   | 8     | HIST_PREV_CLAIM_CNT, HIST_PREV_TOTAL_PAY, HIST_PREV_AVG_PAY,         |
| (Cumulative Prior)     |       | HIST_PREV_MAX_PAY, HIST_PREV_PROVIDER_CNT, HIST_PREV_TYPE_CNT,       |
|                        |       | HIST_DAYS_SINCE_PREV, HIST_DAYS_SINCE_SAME_TYPE                    |
|------------------------+-------+---------------------------------------------------------------------|
| Temporal Sliding       | 6     | HIST_W30_CLAIM_CNT, HIST_W30_TOTAL_PAY, HIST_W30_PROVIDER_CNT       |
| Windows (30d & 90d)    |       | HIST_W90_CLAIM_CNT, HIST_W90_TOTAL_PAY, HIST_W90_PROVIDER_CNT       |
|------------------------+-------+---------------------------------------------------------------------|
| One-Hot Claim Type     | 7     | CLMTYPE_carrier, CLMTYPE_dme, CLMTYPE_hha, CLMTYPE_hospice,         |
| Encodings              |       | CLMTYPE_inpatient, CLMTYPE_outpatient, CLMTYPE_snf                  |
+------------------------------------------------------------------------------------------------------+
```

---

## 8. PDE Feature Engineering (Model C — 32 Features)

Model C extracts **32 features** focused on pharmacy dispensing mechanics, cost distribution, refill velocity, beneficiary utilization history, and prescriber practice patterns.

```
+------------------------------------------------------------------------------------------------------+
| Feature Category       | Count | Key Features & Formulations                                         |
|------------------------+-------+---------------------------------------------------------------------|
| Pass-Through Fields    | 13    | YEAR, QTY_DSPNSD_NUM, DAYS_SUPLY_NUM, FILL_NUM, TOT_RX_CST_AMT,      |
|                        |       | PTNT_PAY_AMT, CVRD_D_PLAN_PD_AMT, NCVRD_PLAN_PD_AMT,                |
|                        |       | GDC_BLW_OOPT_AMT, GDC_ABV_OOPT_AMT, OTHR_TROOP_AMT, LICS_AMT,       |
|                        |       | PLRO_AMT                                                            |
|------------------------+-------+---------------------------------------------------------------------|
| Derived Dispensing &   | 7     | COST_PER_UNIT         = TOT_RX_CST_AMT / QTY_DSPNSD_NUM              |
| Financial Ratios       |       | COST_PER_DAY          = TOT_RX_CST_AMT / DAYS_SUPLY_NUM              |
|                        |       | PATIENT_PAYMENT_RATIO = PTNT_PAY_AMT / TOT_RX_CST_AMT                |
|                        |       | PLAN_PAYMENT_RATIO    = CVRD_D_PLAN_PD_AMT / TOT_RX_CST_AMT          |
|                        |       | QUANTITY_PER_DAY      = QTY_DSPNSD_NUM / DAYS_SUPLY_NUM              |
|                        |       | DAYS_SUPPLY           = DAYS_SUPLY_NUM                              |
|                        |       | REFILL_FREQUENCY      = FILL_NUM                                    |
|------------------------+-------+---------------------------------------------------------------------|
| Beneficiary Historical | 8     | BENE_PREV_RX_COUNT, BENE_PREV_RX_COST, BENE_PREV_AVG_RX_COST,        |
| Rx Trajectory (Prior)  |       | BENE_PREV_MAX_RX_COST, BENE_RX_30D, BENE_RX_COST_30D,               |
|                        |       | BENE_RX_90D, BENE_RX_COST_90D                                       |
|------------------------+-------+---------------------------------------------------------------------|
| Prescriber Historical  | 4     | PRESCRIBER_RX_COUNT, PRESCRIBER_AVG_RX_COST, PRESCRIBER_MAX_RX_COST, |
| Practice Profile       |       | PRESCRIBER_UNIQUE_BENEFICIARIES                                     |
+------------------------------------------------------------------------------------------------------+
```

---

## 9. Temporal Leakage Prevention

Temporal leakage is the most critical failure mode in healthcare machine learning. If future claims are used to compute historical statistics or train models, models learn artificial patterns that fail catastrophically in production.

```
                                  STRICT TEMPORAL BARRIER (POINT-IN-TIME CAUSALITY)
   PAST CLAIMS                                       CURRENT CLAIM (T_0)                 FUTURE CLAIMS
   [ Claim t_{-k} ] ---> [ Claim t_{-1} ] ---------> | SCORED IN REAL-TIME | <---[X]--- [ Claim t_{+1} ]
   =============================================     +---------------------+     =====================
   * Cumulative Counts: Included                     * Features Derived          * Strictly Excluded
   * 30-day / 90-day Windows: Included               * Scalers Applied           * No Future Lookahead
   * Training Period: 2014-2022                      * Isolation Forest Score    * Held-Out Test: 2023
```

### Verification & Guardrails
1. **Strict Holdout Split**: All data from **2014–2022** is used exclusively for training. All **2023** data is held out untouched for evaluation.
2. **Prior-Only Trajectory Scan**: For any transaction at date $T$, historical aggregates (prior claim counts, sums, 30d/90d windows) only evaluate records where $\text{Service Date} < T$. Current transaction values are appended to historical arrays *after* features are computed.
3. **Training-Only Reference Statistics**: Peer group medians, MADs, and percentiles (`medical_claim_type_stats.json`) were computed strictly on 2015–2022 training rows.
4. **Leakage Validation Checks**: Run via `scripts/temporal_split_model_b.py` and validated across 1,888,860 rows:
   - `[T1]` First claims for any beneficiary have exactly `0` or `NaN` prior counts: **PASS (0 failures)**.
   - `[T2]` Days since previous claim $< 0$ (future leak): **PASS (0 occurrences)**.
   - `[T3]` 30-day count $>$ 90-day count: **PASS (0 occurrences)**.
   - `[T4]` Non-monotone cumulative claim counts: **PASS (0 occurrences)**.
   - `[T5]` Zero CLAIM_ID overlap between train and test: **PASS (0 overlapping IDs)**.

---

## 10. Train / Test Strategy

The evaluation framework mirrors real-world deployment where a model trained on historical data must score future, unseen claims.

```
+------------------------------------------------------------------------------------------------------+
| Split Dataset       | Calendar Years | Row Count | Percentage | Purpose                              |
|---------------------+----------------+-----------+------------+--------------------------------------|
| Medical Full Train  | 2014 - 2022    | 1,838,281 | 97.32%     | Full historical training corpus      |
| Medical Train Sample| 2014 - 2022    | 216,701   | 11.79%     | Stratified, balanced training set    |
| Medical Test Set    | 2023           | 50,579    | 2.68%      | Untouched future validation holdout  |
| PDE Training Set    | 2015 - 2022    | 501,190   | 97.22%     | Part D historical training corpus    |
| PDE Test Set        | 2023           | 14,330    | 2.78%      | Untouched future validation holdout  |
+------------------------------------------------------------------------------------------------------+
```

---

## 11. Stratified Sampling Strategy

In the raw Medicare data, low-acuity Carrier and Outpatient claims account for over **89.7%** of all claims, while critical institutional settings like Inpatient, Hospice, SNF, and HHA account for less than **5%**. An unstratified sample would cause Isolation Forests to under-sample severe institutional fraud.

### Stratification Matrix
Training data was stratified across **1,848 joint strata** defined by:
$$\text{Stratum} = \text{CLAIM\_TYPE} \times \text{YEAR} \times \text{PAYMENT\_TIER} \times \text{DIAG\_TIER}$$

```
+------------------------------------------------------------------------------------------------------+
| Claim Type     | Raw Training Rows | Raw Share | Stratified Sample Rows | Stratified Share | Boost    |
|----------------+-------------------+-----------+------------------------+------------------+----------|
| Carrier        | 1,092,137         | 59.41%    | 54,080                 | 24.96%           | 0.42x    |
| DME            | 101,216           | 5.51%     | 43,926                 | 20.27%           | 3.68x    |
| HHA            | 6,070             | 0.33%     | 5,232                  | 2.41%            | 7.30x    |
| Hospice        | 11,924            | 0.65%     | 10,459                 | 4.83%            | 7.43x    |
| Inpatient      | 56,203            | 3.06%     | 40,144                 | 18.53%           | 6.05x    |
| Outpatient     | 558,338           | 30.37%    | 51,456                 | 23.75%           | 0.78x    |
| SNF            | 12,393            | 0.67%     | 11,404                 | 5.26%            | 7.85x    |
| TOTAL          | 1,838,281         | 100.0%    | 216,701                | 100.0%           | Balanced |
+------------------------------------------------------------------------------------------------------+
```

---

## 12. Model B Architecture (Medical Claim Anomaly Detection)

Model B detects complex billing, duration, and intensity anomalies across all seven medical claim types.

```
                              MODEL B INFERENCE PIPELINE
  Raw Medical Claim
         |
         v
  +-------------------------------------------------------------+
  | Step 1: Feature Engine (build_model_b_features)             |
  | * Derives ratios, joins bene history, applies peer stats    |
  | * Output: 59-dimensional vector                             |
  +-------------------------------------------------------------+
         |
         v
  +-------------------------------------------------------------+
  | Step 2: SimpleImputer (strategy='median')                   |
  | * Medians frozen from training sample (imputer.pkl)         |
  +-------------------------------------------------------------+
         |
         v
  +-------------------------------------------------------------+
  | Step 3: StandardScaler (with_mean=True, with_std=True)      |
  | * Mean & Variance frozen from training sample (scaler.pkl)  |
  +-------------------------------------------------------------+
         |
         v
  +-------------------------------------------------------------+
  | Step 4: Isolation Forest Ensemble (300 Isolation Trees)     |
  | * Computes mean path length across trees                    |
  | * Output: Raw decision function score in [-0.70, +0.13]     |
  +-------------------------------------------------------------+
         |
         v
  +-------------------------------------------------------------+
  | Step 5: Claim-Type-Specific Percentile Calibration          |
  | * Maps raw score to [0 - 100] relative to claim type peers  |
  +-------------------------------------------------------------+
```

---

## 13. Model C Architecture (Prescription Drug Anomaly Detection)

Model C is a dedicated Part D pharmacy anomaly detection engine isolated from medical claim structures.

```
                               MODEL C INFERENCE PIPELINE
  Raw PDE Transaction
         |
         v
  +-------------------------------------------------------------+
  | Step 1: PDE Feature Engine (build_model_c_features)         |
  | * Computes cost/unit, cost/day, bene & prescriber velocity  |
  | * Output: 32-dimensional vector                             |
  +-------------------------------------------------------------+
         |
         v
  +-------------------------------------------------------------+
  | Step 2: SimpleImputer (strategy='median')                   |
  | * Medians frozen from PDE training dataset (imputer.pkl)    |
  +-------------------------------------------------------------+
         |
         v
  +-------------------------------------------------------------+
  | Step 3: StandardScaler (with_mean=True, with_std=True)      |
  | * Mean & Std frozen from PDE training dataset (scaler.pkl)  |
  +-------------------------------------------------------------+
         |
         v
  +-------------------------------------------------------------+
  | Step 4: Isolation Forest Ensemble (300 Trees, 32 Features)  |
  | * Output: Raw decision function score in [-0.75, +0.12]     |
  +-------------------------------------------------------------+
         |
         v
  +-------------------------------------------------------------+
  | Step 5: Empirical Percentile Calibration                    |
  | * Maps raw score to [0 - 100] calibrated risk score         |
  +-------------------------------------------------------------+
```

---

## 14. Model Hyperparameters

Both models use tuned `IsolationForest` architectures from `scikit-learn`:

```
+------------------------------------------------------------------------------------------------------+
| Hyperparameter         | Model B (Medical) Value   | Model C (PDE) Value       | Technical Rationale |
|------------------------+---------------------------+---------------------------+---------------------|
| `n_estimators`         | 300                       | 300                       | Ensures asymptotic  |
|                        |                           |                           | path length stability|
| `max_samples`          | 256 (default)             | 256 (default)             | Prevents masking &  |
|                        |                           |                           | swamping effects    |
| `contamination`        | "auto"                    | "auto"                    | Retains threshold-  |
|                        |                           |                           | free decision curve |
| `max_features`         | 1.0 (all features)        | 1.0 (all features)        | Full space splits   |
| `bootstrap`            | False                     | False                     | Sub-sampling without|
|                        |                           |                           | replacement         |
| `random_state`         | 42                        | 42                        | Exact deterministic |
|                        |                           |                           | reproducibility     |
| `n_jobs`               | -1 (all CPU cores)        | -1 (all CPU cores)        | Parallel execution  |
+------------------------------------------------------------------------------------------------------+
```

---

## 15. Score Calibration & Risk Stratification

Raw Isolation Forest decision scores $s \in [-1.0, +0.5]$ represent the average depth of isolation trees:
$$s(x, n) = 2^{-\frac{E(h(x))}{c(n)}}$$
Negative scores represent anomalies, while positive scores represent normal observations. However, raw scores vary significantly across claim types (an Inpatient stay has naturally different score bounds than a Carrier visit).

### Empirical Calibration Formula
For a claim of type $t$ with raw decision score $r$:
1. Determine the percentile rank $P_t(r)$ of score $r$ within the frozen training distribution for claim type $t$:
   $$P_t(r) = \frac{\text{count}(r_{\text{train}, t} < r) + 0.5 \times \text{count}(r_{\text{train}, t} == r)}{N_t} \times 100$$
2. Invert percentile rank so higher scores represent higher anomaly risk:
   $$\text{Calibrated Risk Score} = 100 - P_t(r) \in [0, 100]$$

### Risk Tier Boundaries
- **CRITICAL**: $\text{Score} \ge 80.0$ (Top anomaly tier; immediate compliance review required)
- **HIGH**: $60.0 \le \text{Score} < 80.0$ (Significant multi-feature deviation)
- **MEDIUM**: $40.0 \le \text{Score} < 60.0$ (Moderate variance from peer norms)
- **LOW**: $\text{Score} < 40.0$ (Within standard clinical/financial population norms)

---

## 16. Explainability (TreeSHAP Integration)

To eliminate black-box opacity and provide actionable evidence for investigators, the API embeds real-time **TreeSHAP (SHapley Additive exPlanations)**.

```
                           SHAP TREE-EXPLAINER DECOMPOSITION
  
   Isolation Forest Expected Base Value: E[f(x)] = -0.4316
   
   ANOMALY DRIVERS (Negative SHAP -> Pushes Score Toward Anomaly):
   ----------------------------------------------------------------------------------
   [!] UNPAID_CHARGE ($7,500.00)                 ====> SHAP: -0.5651 (Severe Outlier)
   [!] CLAIM_DURATION_DAYS_TYPE_ROBUST_Z (+10.0) ====> SHAP: -0.4216 (Stay Outlier)
   [!] NUM_DIAGNOSES_TYPE_ROBUST_Z (-10.0)       ====> SHAP: -0.3374 (Abnormal Coding)
   
   NORMALIZING MITIGATORS (Positive SHAP -> Anchors Score in Normal Range):
   ----------------------------------------------------------------------------------
   [*] CLMTYPE_carrier = 0                       ====> SHAP: +0.0973 (Expected Setting)
   [*] BENE_RACE_CD = 1                          ====> SHAP: +0.0791 (Standard Cohort)
```

### Investigator Evidence Structure
Every API response returns structured evidence objects containing:
- `feature`: Exact feature name.
- `value`: Raw, unscaled feature value.
- `shap_contribution`: Exact directional SHAP value.
- `driver_type`: `anomaly_driver` (pushes risk up) or `normal_driver` (mitigating factor).
- `interpretation`: Plain-language explanation for compliance staff.

---

## 17. LEIE Compliance Integration (OIG Exclusions)

The **Office of Inspector General (OIG) List of Excluded Individuals and Entities (LEIE)** contains individuals and entities prohibited from participating in Medicare and Medicaid under Sections 1128 and 1156 of the Social Security Act.

```
                                LEIE VERIFICATION FLOW
  
  Transaction Provider NPI + Service Date
                     |
                     v
  +-------------------------------------------------------------+
  | NPI Normalization Engine                                    |
  | * Strips '.0', trims whitespace, zero-pads to 10 digits     |
  +-------------------------------------------------------------+
                     |
                     v
  +-------------------------------------------------------------+
  | In-Memory LEIE Hash Index Lookup (543 Excluded NPIs)        |
  | * Evaluates: EXCLDATE <= ServiceDate < REINDATE             |
  +-------------------------------------------------------------+
           |                                         |
    [Active Exclusion]                        [No Exclusion]
           |                                         |
           v                                         v
  +-------------------------------+         +-------------------+
  | Compliance Risk Adjustment:   |         | No Adjustment     |
  | Final Score = Min(100, ML+30) |         | Final Score = ML  |
  | Status: ACTIVE_EXCLUSION      |         | Status: NOT_FOUND |
  | Statutory Reason Appended     |         +-------------------+
  +-------------------------------+
```

### Statutory Exclusion Codes
- `1128a1`: Mandatory exclusion for conviction related to Medicare/Medicaid fraud.
- `1128a2`: Mandatory exclusion for patient abuse or neglect.
- `1128a3`: Mandatory exclusion for felony healthcare fraud.
- `1128a4`: Mandatory exclusion for felony controlled substance conviction.
- `1128b1`–`1128b15`: Permissive exclusions (misdemeanor fraud, license revocation, loan default).

---

## 18. API Architecture & Request / Response Lifecycle

The production service is built with **FastAPI** and **Pydantic v2**, offering sub-10ms response times and interactive OpenAPI (Swagger) documentation.

### API Architecture Highlights
- Single Entrypoint: `POST /api/v1/predict` handles both `MEDICAL_CLAIM` and `PDE` transactions.
- In-Memory Artifacts: Models, imputers, scalers, and LEIE indexes are pre-loaded at startup.
- Dynamic Duration & Feature Synthesis: Derives missing fields, ratios, and longitudinal metrics on the fly.

### Request Payloads

#### Medical Claim Request (`MEDICAL_CLAIM`)
```json
{
  "transaction_type": "MEDICAL_CLAIM",
  "claim_id": "CLM-INP-88219",
  "bene_id": -10000010254618,
  "provider_id": "1578657367",
  "claim_type": "inpatient",
  "claim_start_date": "2023-02-01",
  "claim_end_date": "2023-02-15",
  "clm_pmt_amt": 14500.0,
  "clm_tot_chrg_amt": 22000.0,
  "line_count": 6,
  "unit_count": 14,
  "diag_count": 8,
  "proc_count": 4
}
```

#### Prescription Request (`PDE`)
```json
{
  "transaction_type": "PDE",
  "pde_id": "PDE-RX-99102",
  "bene_id": -10000010254618,
  "prscrbr_id": 9999920279,
  "srvc_dt": "15-Jan-2023",
  "qty_dspnsd_num": 240,
  "days_suply_num": 5,
  "fill_num": 12,
  "tot_rx_cst_amt": 12500.0,
  "ptnt_pay_amt": 0.0,
  "cvrd_d_plan_pd_amt": 12500.0,
  "ncvrd_plan_pd_amt": 0.0
}
```

---

## 19. Validation Results

The models were evaluated against untouched temporal test sets from **calendar year 2023**.

```
+------------------------------------------------------------------------------------------------------+
| Check Code | Validation Check Description               | Target Criteria      | Outcome & Status    |
|------------+--------------------------------------------+----------------------+---------------------|
| `V1`       | Missing / NaN Scores in Prediction Output  | 0 NaN values         | PASS (0 NaNs)       |
| `V2`       | Finite Decision Function Bounds            | All finite real nums | PASS (100% Finite)  |
| `V3`       | Calibrated Risk Score Boundary             | Strictly [0, 100]    | PASS (Min 0, Max 100|
| `V4`       | Full Claim Type Representation             | All 7 Types Present  | PASS (7/7 Present)  |
| `V5`       | Population ID Overlap Check                | 0 Overlapping IDs    | PASS (0 Overlap)    |
| `V6`       | Temporal Purity Verification               | Test year == 2023    | PASS (100% 2023)    |
| `V7`       | Training-Only Peer Stats Purity            | Reference Year <=22  | PASS (No 2023 Stats)|
| `V8`       | Prediction Coverage Rate                   | 100% Scored Rows     | PASS (50,579 / 50.5k|
| `V9`       | Anomaly Detection Non-Triviality           | Anomaly % in (0, 100)| PASS (3.85% Anomaly)|
+------------------------------------------------------------------------------------------------------+
```

### Test Set Score Distributions (Model B Medical — 50,579 Test Rows)
- **Mean Calibrated Risk Score**: 16.085
- **Median Calibrated Risk Score**: 13.824
- **95th Percentile Risk Score**: 35.406
- **Risk Level Breakdown**:
  - `LOW`: 35,405 claims (70.0%)
  - `MEDIUM`: 7,587 claims (15.0%)
  - `HIGH`: 5,058 claims (10.0%)
  - `CRITICAL`: 2,529 claims (5.0%)

---

## 20. Limitations & Compliance Boundaries

1. **Unsupervised Nature**: Isolation Forests identify *statistical anomalies*, not verified criminal intent. High scores indicate unusual behavior requiring clinical review, not automatic fraud.
2. **Cold-Start Beneficiaries / Providers**: Providers or patients with no prior history rely on median imputation for historical features until longitudinal baseline data accumulates.
3. **Data Drift Across Policy Changes**: Major regulatory changes (e.g., CMS payment rule revisions) alter billing norms and require periodic reference baseline updates.
4. **Human-in-the-Loop Requirement**: All API responses include a mandatory regulatory disclaimer: *Scores are statistical indicators and do not constitute proof of fraud or policy violation without clinical audit.*

---

## 21. Production Deployment & Scalability Structure

```
                                ENTERPRISE DEPLOYMENT TOPOLOGY
  
  [ External Ingestion / EMR / CMS EDI Feeds ]
                       |
                       v
         [ HTTPS / TLS Load Balancer ]
                       |
        +--------------+--------------+
        |                             |
        v                             v
  [ FastAPI Node 1 ]           [ FastAPI Node 2 ]  (Stateless Container Pods)
  * Pre-loaded Models          * Pre-loaded Models
  * In-Memory LEIE             * In-Memory LEIE
        |                             |
        +--------------+--------------+
                       |
                       +-----> [ Redis / Dragonfly Feature Cache ]
                       |       * Sub-millisecond Bene/Prescriber History
                       |
                       +-----> [ PostgreSQL / TimescaleDB Audit Store ]
                       |       * Transaction Scores, SHAP Values, Decision Logs
                       |
                       +-----> [ Kafka / RabbitMQ Event Bus ]
                               * Async Streaming for Retrospective Audits
```

### Production Best Practices
1. **Containerization**: Deploy FastAPI containers via Kubernetes (EKS/GKE) with horizontal pod autoscaling based on CPU and request queues.
2. **Feature Store Integration**: Cache beneficiary and prescriber longitudinal vectors in Redis or Feast for $O(1)$ lookups.
3. **Model Versioning & Drift Monitoring**: Track model performance, data drift, and score distribution shifts using MLflow and Evidently AI.
4. **CI/CD Quality Gates**: Automated test suites (`pytest tests/test_api_e2e.py`) enforce all 9 validation checks before any model promotion.
