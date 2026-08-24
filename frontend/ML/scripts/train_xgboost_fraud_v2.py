"""
================================================================================
  Medicare Provider-Level Fraud Detection — XGBoost v2 Pipeline
================================================================================
  Datasets used:
    • KAGGLE_MASTER_TRAIN.csv       → aggregated to provider rows (has PotentialFraud)
    • KAGGLE_MASTER_TEST.csv        → aggregated for final scoring (no label)
    • CMS_PROVIDER_MASTER.csv       → peer benchmark features (specialty × state)
    • LEIE_MASTER.csv               → Layer 1 Direct Compliance Gatekeeper (Decoupled from ML)

  Key difference from v1:
    v1 → one row = one claim     (claim-level model)
    v2 → one row = one provider  (provider-level model + CMS peer benchmarks)

  Output artifacts (saved to OUTPUT_DIR):
    • xgboost_fraud_model_v2.pkl        ← trained model + feature list + encoders
    • fraud_predictions_providers.csv   ← provider-level scores + risk tiers
    • eda_plots/                        ← EDA charts
    • model_plots/                      ← ROC, PR, confusion matrix, importance
    • training_log_v2.txt               ← full run log
================================================================================
"""

# ──────────────────────────────────────────────────────────────────────────────
# 0.  IMPORTS
# ──────────────────────────────────────────────────────────────────────────────
import os, sys, warnings, pickle, logging
from datetime import datetime

import numpy  as np
import pandas as pd
import matplotlib.pyplot    as plt
import matplotlib.gridspec  as gridspec
import seaborn              as sns

from sklearn.model_selection  import train_test_split, StratifiedKFold
from sklearn.preprocessing    import LabelEncoder
from sklearn.metrics          import (
    classification_report, confusion_matrix,
    roc_auc_score, roc_curve,
    precision_recall_curve, average_precision_score,
    f1_score, matthews_corrcoef,
)
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")
pd.set_option("display.max_columns", 80)
pd.set_option("display.width", 220)


# ──────────────────────────────────────────────────────────────────────────────
# 1.  CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(CURRENT_DIR).lower() in ("backend", "backend2"):
    ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
else:
    ROOT_DIR = CURRENT_DIR

datasets_dir = os.path.join(ROOT_DIR, "datasets")
if os.path.exists(os.path.join(datasets_dir, "KAGGLE_MASTER_TRAIN.csv")):
    BASE_DIR = datasets_dir
else:
    BASE_DIR = os.path.join(ROOT_DIR, "processed_data")

OUTPUT_DIR = os.path.join(ROOT_DIR, "backend2", "models", "xgboost_fraud_v2")

PATHS = {
    "train"   : os.path.join(BASE_DIR, "KAGGLE_MASTER_TRAIN.csv"),
    "test"    : os.path.join(BASE_DIR, "KAGGLE_MASTER_TEST.csv"),
    "cms"     : os.path.join(BASE_DIR, "CMS_PROVIDER_MASTER.csv"),
}

RANDOM_STATE    = 42
TEST_SIZE       = 0.20

# Shared constants — NEVER redefine locally; always import from config.py
try:
    from backend2.config import FRAUD_THRESHOLD, TIER_BINS, TIER_LABELS
except ImportError:
    from config import FRAUD_THRESHOLD, TIER_BINS, TIER_LABELS

# CMS columns to read — all high-value fraud signals across 82 available columns
CMS_USECOLS = [
    # Provider identity
    "Rndrng_Prvdr_State_Abrvtn",
    "Rndrng_Prvdr_Type",
    "Rndrng_Prvdr_RUCA",           # Rural-Urban Commuting Area code (1-10)
    # Billing volumes
    "Tot_HCPCS_Cds",
    "Tot_Benes",
    "Tot_Srvcs",
    "Tot_Sbmtd_Chrg",
    "Tot_Mdcr_Alowd_Amt",
    "Tot_Mdcr_Pymt_Amt",
    "Tot_Mdcr_Stdzd_Amt",          # Geographic-standardised payment (cleaner baseline)
    # Drug service breakdown
    "Drug_Sprsn_Ind",              # Suppression flag (< 10 patients) — small-volume fraud signal
    "Drug_Tot_Benes",
    "Drug_Tot_Srvcs",
    "Drug_Sbmtd_Chrg",
    "Drug_Mdcr_Pymt_Amt",
    # Medical service breakdown
    "Med_Sprsn_Ind",
    "Med_Tot_HCPCS_Cds",           # Distinct medical codes = upcoding risk
    "Med_Tot_Benes",
    "Med_Sbmtd_Chrg",
    "Med_Mdcr_Pymt_Amt",
    # Beneficiary risk
    "Bene_Avg_Age",
    "Bene_Avg_Risk_Scre",
    "Bene_Dual_Cnt",               # Dual Medicare+Medicaid count
    "Bene_Age_LT_65_Cnt",          # Under-65 beneficiary count
    "Bene_Age_GT_84_Cnt",          # Very elderly count
    # Behavioural health conditions (all 11 — new!)
    "Bene_CC_BH_Alcohol_Drug_V1_Pct",
    "Bene_CC_BH_Anxiety_V1_Pct",
    "Bene_CC_BH_Bipolar_V1_Pct",
    "Bene_CC_BH_Depress_V1_Pct",
    "Bene_CC_BH_PTSD_V1_Pct",
    "Bene_CC_BH_Schizo_OthPsy_V1_Pct",
    "Bene_CC_BH_Alz_NonAlzdem_V2_Pct",
    # Physical health conditions
    "Bene_CC_PH_Diabetes_V2_Pct",
    "Bene_CC_PH_HF_NonIHD_V2_Pct",
    "Bene_CC_PH_CKD_V2_Pct",
    "Bene_CC_PH_Afib_V2_Pct",
    "Bene_CC_PH_Cancer6_V2_Pct",
    "Bene_CC_PH_COPD_V2_Pct",
    "Bene_CC_PH_IschemicHeart_V2_Pct",
    "Bene_CC_PH_Hyperlipidemia_V2_Pct",
    "Bene_CC_PH_Hypertension_V2_Pct",
    "Bene_CC_PH_Stroke_TIA_V2_Pct",
    "Bene_CC_PH_Osteoporosis_V2_Pct",
    "Bene_CC_PH_Arthritis_V2_Pct",
]


# ──────────────────────────────────────────────────────────────────────────────
# 2.  LOGGER SETUP
# ──────────────────────────────────────────────────────────────────────────────
def setup_logger(output_dir: str) -> logging.Logger:
    os.makedirs(output_dir, exist_ok=True)
    log_path = os.path.join(output_dir, "training_log_v2.txt")
    logger   = logging.getLogger("fraud_pipeline_v2")
    logger.setLevel(logging.INFO)
    logger.handlers = []
    fh = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s  %(message)s",
                                       datefmt="%Y-%m-%d %H:%M:%S"))
    import io
    ch = logging.StreamHandler(io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace"))
    ch.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


# ──────────────────────────────────────────────────────────────────────────────
# 3.  DATA LOADING
# ──────────────────────────────────────────────────────────────────────────────
def load_data(logger) -> dict:
    logger.info("\n" + "="*70)
    logger.info("  STEP 1 — DATA LOADING")
    logger.info("="*70)

    dfs = {}

    # Kaggle train/test (full load)
    for name in ("train", "test"):
        path = PATHS[name]
        logger.info(f"\n  Loading {name}  →  {os.path.basename(path)}")
        df = pd.read_csv(path, low_memory=False)
        logger.info(f"    Rows : {df.shape[0]:>10,}  |  Cols : {df.shape[1]}")
        dfs[name] = df

    # CMS Provider Master — read only needed columns, chunk to save RAM
    logger.info(f"\n  Loading cms  →  CMS_PROVIDER_MASTER.csv  (chunked, selected cols)")
    cms_chunks = []
    chunk_size = 500_000
    for chunk in pd.read_csv(PATHS["cms"], usecols=CMS_USECOLS,
                              low_memory=False, chunksize=chunk_size):
        cms_chunks.append(chunk)
    cms_df = pd.concat(cms_chunks, ignore_index=True)
    logger.info(f"    Rows : {cms_df.shape[0]:>10,}  |  Cols : {cms_df.shape[1]}")
    dfs["cms"] = cms_df

    return dfs


# LEIE is completely decoupled from XGBoost feature training.
# Layer 1 Direct NPI/Name Exclusion check is performed at runtime in backend2/main.py.


# ──────────────────────────────────────────────────────────────────────────────
# 5.  CLAIM-LEVEL PREPROCESSING (applied before aggregation)
# ──────────────────────────────────────────────────────────────────────────────
DATE_COLS = ["ClaimStartDt", "ClaimEndDt", "AdmissionDt", "DischargeDt", "DOB", "DOD"]

CHRONIC_COLS = [
    "ChronicCond_Alzheimer", "ChronicCond_Heartfailure",
    "ChronicCond_KidneyDisease", "ChronicCond_Cancer",
    "ChronicCond_ObstrPulmonary", "ChronicCond_Depression",
    "ChronicCond_Diabetes", "ChronicCond_IschemicHeart",
    "ChronicCond_Osteoporasis", "ChronicCond_rheumatoidarthritis",
    "ChronicCond_stroke",
]

DIAG_COLS = [f"ClmDiagnosisCode_{i}" for i in range(1, 11)]
PROC_COLS = [f"ClmProcedureCode_{i}" for i in range(1, 7)]


def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    for col in DATE_COLS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def recode_chronic(df: pd.DataFrame) -> pd.DataFrame:
    """CMS encodes 1=Yes, 2=No → recode to 1=Yes, 0=No."""
    for col in CHRONIC_COLS:
        if col in df.columns:
            df[col] = df[col].map({1: 1, 2: 0}).fillna(0).astype(int)
    return df


def preprocess_claims(df: pd.DataFrame) -> pd.DataFrame:
    """Apply date parsing and chronic condition recoding at claim level."""
    df = df.copy()

    # Safe defaults for any missing columns from PDF extraction or partial CSVs
    required_defaults = {
        "Provider"                : "UNKNOWN_PROV",
        "ClaimID"                 : "CLM_UNKNOWN",
        "BeneID"                  : "BENE_UNKNOWN",
        "ClaimStartDt"            : pd.NaT,
        "ClaimEndDt"              : pd.NaT,
        "AdmissionDt"             : pd.NaT,
        "DischargeDt"             : pd.NaT,
        "DOB"                     : pd.NaT,
        "DOD"                     : pd.NaT,
        "AttendingPhysician"      : np.nan,
        "OperatingPhysician"      : np.nan,
        "OtherPhysician"          : np.nan,
        "ClaimType"               : "Outpatient",
        "RenalDiseaseIndicator"   : "0",
        "State"                   : "UNKNOWN",
        "InscClaimAmtReimbursed"  : 0.0,
        "DeductibleAmtPaid"       : 0.0,
        "IPAnnualReimbursementAmt": 0.0,
        "OPAnnualReimbursementAmt": 0.0,
        "IPAnnualDeductibleAmt"   : 0.0,
        "OPAnnualDeductibleAmt"   : 0.0,
    }
    for col, default_val in required_defaults.items():
        if col not in df.columns:
            df[col] = default_val

    df = parse_dates(df)
    df = recode_chronic(df)

    # Basic derived features needed for aggregation
    df["ClaimDurationDays"]    = (df["ClaimEndDt"] - df["ClaimStartDt"]).dt.days.fillna(0).clip(lower=0)
    df["AdmissionToDischarge"] = (df["DischargeDt"] - df["AdmissionDt"]).dt.days.fillna(0).clip(lower=0)
    df["AgeAtClaim"]           = ((df["ClaimStartDt"] - df["DOB"]).dt.days / 365.25).fillna(65).clip(lower=0, upper=120)
    df["IsDead"]               = df["DOD"].notna().astype(int)
    df["ClaimAfterDeath"]      = (df["DOD"].notna() & (df["ClaimStartDt"] > df["DOD"])).astype(int)

    df["HasAttending"]  = df["AttendingPhysician"].notna().astype(int)
    df["HasOperating"]  = df["OperatingPhysician"].notna().astype(int)
    df["HasOther"]      = df["OtherPhysician"].notna().astype(int)
    df["PhysicianCount"]= df["HasAttending"] + df["HasOperating"] + df["HasOther"]

    df["DiagnosisCodeCount"] = df[[c for c in DIAG_COLS if c in df.columns]].notna().sum(axis=1)
    df["ProcedureCodeCount"] = df[[c for c in PROC_COLS if c in df.columns]].notna().sum(axis=1)

    existing_cc = [c for c in CHRONIC_COLS if c in df.columns]
    df["ChronicCondCount"] = df[existing_cc].sum(axis=1)

    df["ClaimTypeIP"] = df["ClaimType"].astype(str).str.lower().str.contains("inpatient").astype(int)

    df["IPAnnualReimbursementAmt"] = df.get("IPAnnualReimbursementAmt", pd.Series(0, index=df.index)).fillna(0)
    df["OPAnnualReimbursementAmt"] = df.get("OPAnnualReimbursementAmt", pd.Series(0, index=df.index)).fillna(0)
    df["IPAnnualDeductibleAmt"]    = df.get("IPAnnualDeductibleAmt", pd.Series(0, index=df.index)).fillna(0)
    df["OPAnnualDeductibleAmt"]    = df.get("OPAnnualDeductibleAmt", pd.Series(0, index=df.index)).fillna(0)
    df["DeductibleAmtPaid"]        = df.get("DeductibleAmtPaid", pd.Series(0, index=df.index)).fillna(0)
    df["InscClaimAmtReimbursed"]   = df.get("InscClaimAmtReimbursed", pd.Series(0, index=df.index)).fillna(0)

    df["TotalAnnualReimbursement"] = df["IPAnnualReimbursementAmt"] + df["OPAnnualReimbursementAmt"]

    return df


# ──────────────────────────────────────────────────────────────────────────────
# 6.  PROVIDER-LEVEL AGGREGATION
# ──────────────────────────────────────────────────────────────────────────────
def aggregate_to_provider(df: pd.DataFrame, has_label: bool, logger) -> pd.DataFrame:
    """
    Aggregate claim-level rows to one row per Provider.
    Fraud label = majority vote if has_label=True.
    """
    logger.info("\n" + "="*70)
    logger.info("  STEP 3 — PROVIDER-LEVEL AGGREGATION")
    logger.info("="*70)

    df = preprocess_claims(df)

    agg_dict = {
        # Counts & volumes
        "ClaimID"               : "count",
        "BeneID"                : pd.Series.nunique,
        "InscClaimAmtReimbursed": ["sum", "mean", "max", "std"],
        "DeductibleAmtPaid"     : "mean",
        "ClaimDurationDays"     : "mean",
        "AdmissionToDischarge"  : "mean",
        "AgeAtClaim"            : "mean",
        # Fraud signals
        "ClaimAfterDeath"       : "mean",      # ghost billing rate
        "PhysicianCount"        : "mean",
        "DiagnosisCodeCount"    : "mean",
        "ProcedureCodeCount"    : "mean",
        "ChronicCondCount"      : "mean",
        "ClaimTypeIP"           : "mean",      # IP claim ratio
        # Annual financials
        "TotalAnnualReimbursement"  : "mean",
        "IPAnnualReimbursementAmt"  : "mean",
        "OPAnnualReimbursementAmt"  : "mean",
        "IPAnnualDeductibleAmt"     : "mean",
        "OPAnnualDeductibleAmt"     : "mean",
        # Boolean flags
        "IsDead"                : "max",       # any deceased beneficiary
        "RenalDiseaseIndicator" : lambda x: (x.astype(str).str.strip()=="1").mean(),
        # State info (most frequent)
        "State"                 : lambda x: x.mode()[0] if len(x) > 0 else "UNKNOWN",
    }

    # Add chronic condition means
    for cc in CHRONIC_COLS:
        if cc in df.columns:
            agg_dict[cc] = "mean"

    prov_df = df.groupby("Provider").agg(agg_dict)

    # Flatten multi-level column names
    cols = []
    for c in prov_df.columns:
        if isinstance(c, tuple):
            base, stat = c
            if stat in ("count", "mean", "sum", "max", "std", "<lambda>", "<lambda_0>"):
                cols.append(f"{base}_{stat}".replace("<lambda>", "fn").replace("<lambda_0>", "fn"))
            else:
                cols.append(f"{base}_{stat}")
        else:
            cols.append(c)
    prov_df.columns = cols
    prov_df = prov_df.reset_index()

    # Rename for clarity
    rename_map = {
        "ClaimID_count"                     : "total_claims",
        "BeneID_nunique"                    : "unique_beneficiaries",
        "InscClaimAmtReimbursed_sum"        : "total_reimbursement",
        "InscClaimAmtReimbursed_mean"       : "avg_claim_reimbursed",
        "InscClaimAmtReimbursed_max"        : "max_claim_reimbursed",
        "InscClaimAmtReimbursed_std"        : "std_claim_reimbursed",
        "DeductibleAmtPaid_mean"            : "avg_deductible_paid",
        "ClaimDurationDays_mean"            : "avg_claim_duration",
        "AdmissionToDischarge_mean"         : "avg_los",
        "AgeAtClaim_mean"                   : "avg_bene_age",
        "ClaimAfterDeath_mean"              : "ghost_billing_rate",
        "PhysicianCount_mean"               : "avg_physician_count",
        "DiagnosisCodeCount_mean"           : "avg_diagnosis_density",
        "ProcedureCodeCount_mean"           : "avg_procedure_density",
        "ChronicCondCount_mean"             : "avg_chronic_burden",
        "ClaimTypeIP_mean"                  : "ip_claim_ratio",
        "TotalAnnualReimbursement_mean"     : "avg_total_annual_reimb",
        "IPAnnualReimbursementAmt_mean"     : "avg_ip_annual_reimb",
        "OPAnnualReimbursementAmt_mean"     : "avg_op_annual_reimb",
        "IPAnnualDeductibleAmt_mean"        : "avg_ip_annual_ded",
        "OPAnnualDeductibleAmt_mean"        : "avg_op_annual_ded",
        "IsDead_max"                        : "any_deceased_bene",
        "RenalDiseaseIndicator_fn"          : "renal_disease_rate",
        "State_fn"                          : "primary_state",
    }

    # Rename chronic means
    for cc in CHRONIC_COLS:
        old = f"{cc}_mean"
        if old in prov_df.columns:
            rename_map[old] = f"cc_{cc.replace('ChronicCond_', '').lower()}_rate"

    prov_df = prov_df.rename(columns=rename_map)

    # Derived ratio features (upcoding & volume anomaly signals)
    prov_df["physician_stacking_rate"] = (prov_df["avg_physician_count"] >= 3).astype(int)
    prov_df["claims_per_beneficiary"]  = (
        prov_df["total_claims"] / prov_df["unique_beneficiaries"].replace(0, np.nan)
    )
    prov_df["reimbursement_per_claim"] = (
        prov_df["total_reimbursement"] / prov_df["total_claims"].replace(0, np.nan)
    )
    ip_r = prov_df["avg_ip_annual_reimb"].replace(0, np.nan)
    op_r = prov_df["avg_op_annual_reimb"].replace(0, np.nan)
    prov_df["ip_vs_op_ratio"]          = ip_r / op_r

    if has_label and "PotentialFraud" in df.columns:
        fraud_map = df.groupby("Provider")["PotentialFraud"].agg(
            lambda x: int((x.str.lower() == "yes").mean() >= 0.5)
        )
        prov_df["fraud_label"] = prov_df["Provider"].map(fraud_map).fillna(0).astype(int)
        fraud_rate = prov_df["fraud_label"].mean()
        logger.info(f"\n  Providers      : {len(prov_df):,}")
        logger.info(f"  Fraud rate     : {fraud_rate:.3f}  ({prov_df['fraud_label'].sum():,} flagged)")
    else:
        prov_df["fraud_label"] = 0

    logger.info(f"  Final provider feature matrix: {prov_df.shape}")
    return prov_df


# ──────────────────────────────────────────────────────────────────────────────
# 7.  CMS PEER BENCHMARK JOIN
# ──────────────────────────────────────────────────────────────────────────────
def build_cms_peer_benchmarks(cms_df: pd.DataFrame, logger) -> pd.DataFrame:
    """
    Aggregate CMS Provider Master by (State × ProviderType) to build
    peer group statistics. Returns one row per (state, type) with
    median, p75, p95 benchmarks for key billing and clinical metrics.
    """
    logger.info("\n" + "="*70)
    logger.info("  STEP 4 — CMS PEER BENCHMARK CONSTRUCTION")
    logger.info("="*70)

    cms = cms_df.copy()
    cms["Rndrng_Prvdr_State_Abrvtn"] = cms["Rndrng_Prvdr_State_Abrvtn"].astype(str).str.strip().str.upper()
    cms["Rndrng_Prvdr_Type"]         = cms["Rndrng_Prvdr_Type"].astype(str).str.strip().str.lower()

    # Derive computed billing ratios BEFORE aggregation — valid at provider level
    for c in ["Drug_Mdcr_Pymt_Amt", "Med_Mdcr_Pymt_Amt", "Tot_Sbmtd_Chrg",
              "Tot_Mdcr_Pymt_Amt", "Tot_Mdcr_Stdzd_Amt", "Tot_Mdcr_Alowd_Amt",
              "Drug_Tot_Benes", "Med_Tot_Benes", "Tot_Benes",
              "Drug_Sbmtd_Chrg", "Med_Sbmtd_Chrg", "Rndrng_Prvdr_RUCA"]:
        if c in cms.columns:
            cms[c] = pd.to_numeric(cms[c], errors="coerce")

    # Drug-to-Medical billing ratio (unusual splits flag fraud specialisation)
    if "Drug_Mdcr_Pymt_Amt" in cms.columns and "Med_Mdcr_Pymt_Amt" in cms.columns:
        cms["drug_to_medical_ratio"] = (
            cms["Drug_Mdcr_Pymt_Amt"] /
            (cms["Med_Mdcr_Pymt_Amt"] + cms["Drug_Mdcr_Pymt_Amt"]).replace(0, np.nan)
        )

    # Standardised-to-allowed payment spread (geographic billing anomaly)
    if "Tot_Mdcr_Stdzd_Amt" in cms.columns and "Tot_Mdcr_Alowd_Amt" in cms.columns:
        cms["stdz_to_allowed_ratio"] = (
            cms["Tot_Mdcr_Stdzd_Amt"] /
            cms["Tot_Mdcr_Alowd_Amt"].replace(0, np.nan)
        )

    # Payment-to-charge ratio (low = overcharging, high = unusual)
    if "Tot_Mdcr_Pymt_Amt" in cms.columns and "Tot_Sbmtd_Chrg" in cms.columns:
        cms["pymt_to_charge_ratio"] = (
            cms["Tot_Mdcr_Pymt_Amt"] /
            cms["Tot_Sbmtd_Chrg"].replace(0, np.nan)
        )

    # Suppression flag: Y/N → binary (small-volume = potential fraud setup)
    for flag_col in ["Drug_Sprsn_Ind", "Med_Sprsn_Ind"]:
        if flag_col in cms.columns:
            cms[flag_col] = (cms[flag_col].astype(str).str.strip().str.upper() == "Y").astype(int)

    numeric_cols = [
        "Tot_Sbmtd_Chrg", "Tot_Mdcr_Alowd_Amt", "Tot_Mdcr_Pymt_Amt",
        "Tot_Mdcr_Stdzd_Amt", "Tot_Benes", "Tot_Srvcs",
        "Bene_Avg_Risk_Scre", "Bene_Avg_Age",
        "Bene_Dual_Cnt", "Bene_Age_LT_65_Cnt", "Bene_Age_GT_84_Cnt",
        "Rndrng_Prvdr_RUCA",
        # Drug breakdown
        "Drug_Tot_Benes", "Drug_Sbmtd_Chrg", "Drug_Mdcr_Pymt_Amt",
        "drug_to_medical_ratio", "stdz_to_allowed_ratio", "pymt_to_charge_ratio",
        # Suppression
        "Drug_Sprsn_Ind", "Med_Sprsn_Ind",
        # BH conditions
        "Bene_CC_BH_Alcohol_Drug_V1_Pct", "Bene_CC_BH_Anxiety_V1_Pct",
        "Bene_CC_BH_Bipolar_V1_Pct", "Bene_CC_BH_Depress_V1_Pct",
        "Bene_CC_BH_PTSD_V1_Pct", "Bene_CC_BH_Schizo_OthPsy_V1_Pct",
        "Bene_CC_BH_Alz_NonAlzdem_V2_Pct",
        # PH conditions
        "Bene_CC_PH_Diabetes_V2_Pct", "Bene_CC_PH_HF_NonIHD_V2_Pct",
        "Bene_CC_PH_CKD_V2_Pct", "Bene_CC_PH_Afib_V2_Pct",
        "Bene_CC_BH_Depress_V1_Pct", "Bene_CC_PH_Cancer6_V2_Pct",
        "Bene_CC_PH_COPD_V2_Pct", "Bene_CC_PH_IschemicHeart_V2_Pct",
        "Bene_CC_PH_Hyperlipidemia_V2_Pct", "Bene_CC_PH_Hypertension_V2_Pct",
        "Bene_CC_PH_Stroke_TIA_V2_Pct", "Bene_CC_PH_Osteoporosis_V2_Pct",
        "Bene_CC_PH_Arthritis_V2_Pct",
    ]
    for c in numeric_cols:
        if c in cms.columns:
            cms[c] = pd.to_numeric(cms[c], errors="coerce")

    group_key = ["Rndrng_Prvdr_State_Abrvtn", "Rndrng_Prvdr_Type"]

    def peer_agg(x):
        row = {}
        for col in numeric_cols:
            if col in x.columns:
                vals = x[col].dropna()
                row[f"peer_median_{col}"]   = vals.median()
                row[f"peer_p75_{col}"]      = vals.quantile(0.75)
                row[f"peer_p95_{col}"]      = vals.quantile(0.95)
        return pd.Series(row)

    logger.info("  Building peer group aggregations (may take 30-60s for 8M rows)...")
    peer = cms.groupby(group_key).apply(peer_agg, include_groups=False).reset_index()
    logger.info(f"  Peer benchmark table: {peer.shape}")
    return peer


def join_cms_peer_features(prov_df: pd.DataFrame, peer_df: pd.DataFrame,
                             logger) -> pd.DataFrame:
    """
    Statistical join: Kaggle State × 'Internal Medicine' (default type)
    Since Kaggle has no specialty column, we use 'internal medicine' as
    the universal peer group (broadest coverage, ~14% of CMS rows).
    This gives us real peer benchmark ratios against a common baseline.
    """
    logger.info("\n  Joining CMS peer benchmarks onto provider table ...")

    if peer_df is None or len(peer_df) == 0:
        return prov_df

    # Check state column name in peer_df (either Rndrng_Prvdr_State_Abrvtn or primary_state)
    state_col = "Rndrng_Prvdr_State_Abrvtn" if "Rndrng_Prvdr_State_Abrvtn" in peer_df.columns else "primary_state"
    if state_col not in peer_df.columns:
        return prov_df

    # Kaggle has no specialty column → use 'internal medicine' as the fixed peer group.
    # It is the largest CMS specialty (~14% of rows), giving maximum state coverage.
    # This is an explicit design choice: every provider is benchmarked against the
    # 'internal medicine' state peer baseline, not against the state average across all specialties,
    # which would mix cardiologists, oncologists, etc. into a single meaningless baseline.
    DEFAULT_SPECIALTY = "internal medicine"
    type_col = "Rndrng_Prvdr_Type" if "Rndrng_Prvdr_Type" in peer_df.columns else None

    if type_col is not None:
        peer_specialty = peer_df[peer_df[type_col].str.lower().str.strip() == DEFAULT_SPECIALTY].copy()
        if len(peer_specialty) == 0:
            # fallback: use all rows grouped by state if the specialty is absent
            peer_specialty = peer_df.copy()
            logger.info(f"    Specialty '{DEFAULT_SPECIALTY}' not found — falling back to state-only averages")
        else:
            logger.info(f"    Using peer specialty: '{DEFAULT_SPECIALTY}' ({len(peer_specialty):,} rows)")
    else:
        peer_specialty = peer_df.copy()

    peer_by_state = peer_specialty.groupby(state_col).mean(numeric_only=True).reset_index()
    peer_by_state = peer_by_state.rename(columns={state_col: "primary_state"})

    # Both sides cast to str — unmatched rows get NaN, imputed later
    prov_df["primary_state"]       = prov_df["primary_state"].astype(str)
    peer_by_state["primary_state"] = peer_by_state["primary_state"].astype(str)

    prov_df = prov_df.merge(peer_by_state, on="primary_state", how="left")

    if "peer_median_Tot_Sbmtd_Chrg" in prov_df.columns:
        prov_df["charge_vs_peer_ratio"] = (
            prov_df["total_reimbursement"] /
            prov_df["peer_median_Tot_Sbmtd_Chrg"].replace(0, np.nan)
        )

    if "peer_median_Tot_Benes" in prov_df.columns:
        prov_df["benes_vs_peer_ratio"] = (
            prov_df["unique_beneficiaries"] /
            prov_df["peer_median_Tot_Benes"].replace(0, np.nan)
        )

    if "peer_median_Bene_Avg_Age" in prov_df.columns:
        prov_df["avg_age_vs_peer"] = (
            prov_df["avg_bene_age"] /
            prov_df["peer_median_Bene_Avg_Age"].replace(0, np.nan)
        )

    # chronic_burden_vs_peer_risk_proxy: avg chronic cond count / peer median HCC risk score.
    # Named *_proxy to be explicit that these are different scales (0-11 count vs 0.5-3.0 HCC).
    # Useful as an ordinal anomaly signal — do NOT interpret as a calibrated ratio.
    if "peer_median_Bene_Avg_Risk_Scre" in prov_df.columns:
        prov_df["chronic_burden_vs_peer_risk_proxy"] = (
            prov_df["avg_chronic_burden"] /
            prov_df["peer_median_Bene_Avg_Risk_Scre"].replace(0, np.nan)
        )

    logger.info(f"  Provider table after CMS join: {prov_df.shape}")
    return prov_df


# ──────────────────────────────────────────────────────────────────────────────
# 8.  FEATURE LISTS
# ──────────────────────────────────────────────────────────────────────────────
BASE_PROVIDER_FEATURES = [
    # Volume features
    "total_claims",
    "unique_beneficiaries",
    "claims_per_beneficiary",
    # Billing features
    "total_reimbursement",
    "avg_claim_reimbursed",
    "max_claim_reimbursed",
    "std_claim_reimbursed",
    "reimbursement_per_claim",
    "avg_deductible_paid",
    # Financial ratios
    "avg_ip_annual_reimb",
    "avg_op_annual_reimb",
    "avg_total_annual_reimb",
    "ip_vs_op_ratio",
    # Temporal
    "avg_claim_duration",
    "avg_los",
    # Beneficiary demographics
    "avg_bene_age",
    "avg_chronic_burden",
    "renal_disease_rate",
    "any_deceased_bene",
    # Fraud signals
    "ghost_billing_rate",
    "physician_stacking_rate",
    "avg_physician_count",
    "ip_claim_ratio",
    # Clinical complexity
    "avg_diagnosis_density",
    "avg_procedure_density",
]

# Chronic condition rates (will be added dynamically)
CC_RATE_COLS = [
    f"cc_{cc.replace('ChronicCond_', '').lower()}_rate"
    for cc in CHRONIC_COLS
]

# CMS peer benchmark features — expanded to include drug/billing ratios, RUCA, all BH/PH conditions
PEER_FEATURE_COLS = [
    # Provider-vs-peer ratio features (computed in join_cms_peer_features)
    "charge_vs_peer_ratio",
    "benes_vs_peer_ratio",
    "avg_age_vs_peer",
    "chronic_burden_vs_peer_risk_proxy",      # ordinal proxy, NOT calibrated ratio
    # Billing anomaly ratios (from peer baseline)
    "peer_median_drug_to_medical_ratio",      # drug vs medical billing split
    "peer_median_stdz_to_allowed_ratio",      # geographic billing spread
    "peer_median_pymt_to_charge_ratio",       # payment efficiency
    # Volume baselines
    "peer_median_Tot_Sbmtd_Chrg",
    "peer_median_Tot_Mdcr_Pymt_Amt",
    "peer_median_Tot_Benes",
    # Risk baselines
    "peer_median_Bene_Avg_Risk_Scre",
    "peer_median_Rndrng_Prvdr_RUCA",          # rural vs urban peer baseline
    "peer_median_Drug_Sprsn_Ind",             # suppression rate
    # BH chronic conditions
    "peer_median_Bene_CC_BH_Alcohol_Drug_V1_Pct",
    "peer_median_Bene_CC_BH_Depress_V1_Pct",
    "peer_median_Bene_CC_BH_PTSD_V1_Pct",
    "peer_median_Bene_CC_BH_Alz_NonAlzdem_V2_Pct",
    # PH chronic conditions
    "peer_median_Bene_CC_PH_Diabetes_V2_Pct",
    "peer_median_Bene_CC_PH_HF_NonIHD_V2_Pct",
    "peer_median_Bene_CC_PH_CKD_V2_Pct",
    "peer_median_Bene_CC_PH_IschemicHeart_V2_Pct",
    "peer_median_Bene_CC_PH_Stroke_TIA_V2_Pct",
    "peer_median_Bene_CC_PH_Hypertension_V2_Pct",
]

CAT_COLS = ["primary_state"]


# ──────────────────────────────────────────────────────────────────────────────
# 9.  IMPUTATION + ENCODING
# ──────────────────────────────────────────────────────────────────────────────
def impute_and_encode(train_df: pd.DataFrame, test_df: pd.DataFrame,
                       feature_cols: list, logger) -> tuple:
    """
    Fit imputation medians and label encoders on TRAIN only.
    Apply to both train and test to prevent data leakage.
    """
    logger.info("\n  Imputing missing values and encoding categoricals ...")
    medians  = {}
    encoders = {}

    active_features = [f for f in feature_cols if f in train_df.columns]

    for col in active_features:
        if col in CAT_COLS:
            le = LabelEncoder()
            train_df[col] = train_df[col].astype(str).fillna("UNKNOWN")
            test_df[col]  = test_df[col].astype(str).fillna("UNKNOWN")
            # Inject 'UNKNOWN' as a dedicated class before fitting so unseen states
            # at inference time map to 'UNKNOWN' rather than the alphabetically-first state.
            all_values = pd.concat([
                train_df[col],
                pd.Series(["UNKNOWN"])
            ]).unique().tolist()
            le.fit(all_values)
            encoders[col] = le
            known = set(le.classes_)
            test_df[col]  = test_df[col].apply(lambda x: x if x in known else "UNKNOWN")
            train_df[col] = le.transform(train_df[col])
            test_df[col]  = le.transform(test_df[col])
        else:
            med = train_df[col].median()
            if np.isnan(med):
                med = 0.0
            medians[col]  = med
            train_df[col] = train_df[col].fillna(med)
            test_df[col]  = test_df[col].fillna(med)

    logger.info(f"    Imputed {len(medians)} numeric  +  {len(encoders)} categorical features")
    return train_df, test_df, encoders, medians


# ──────────────────────────────────────────────────────────────────────────────
# 10.  EDA
# ──────────────────────────────────────────────────────────────────────────────
def run_eda(prov_df: pd.DataFrame, output_dir: str, logger):
    """EDA charts for provider-level aggregated data."""
    logger.info("\n" + "="*70)
    logger.info("  STEP 5 — EXPLORATORY DATA ANALYSIS (Provider Level)")
    logger.info("="*70)

    eda_dir = os.path.join(output_dir, "eda_plots")
    os.makedirs(eda_dir, exist_ok=True)

    df  = prov_df.copy()
    lbl = "fraud_label"
    palette = {0: "#1976D2", 1: "#D32F2F"}

    def save(fig, name):
        fig.savefig(os.path.join(eda_dir, name), dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info(f"    Saved: {name}")

    # 1. Provider class distribution
    fig, ax = plt.subplots(figsize=(6, 4))
    counts = df[lbl].value_counts().sort_index()
    bars   = ax.bar(["Not Fraud", "Fraud"], counts.values,
                    color=["#1976D2", "#D32F2F"], width=0.5, edgecolor="white")
    for bar, v in zip(bars, counts.values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f"{v:,}\n({v/len(df)*100:.1f}%)",
                ha="center", va="bottom", fontsize=11, fontweight="bold")
    ax.set_title("Provider-Level Class Distribution — PotentialFraud", fontsize=12)
    ax.set_ylabel("Number of Providers")
    ax.spines[["top","right"]].set_visible(False)
    save(fig, "01_provider_class_distribution.png")

    # helper: safe histogram — skips if data is empty / all-NaN
    def safe_hist(ax, series, bins, color, label, alpha=0.65):
        clean = series.dropna()
        if len(clean) == 0:
            return False
        ax.hist(clean, bins=bins, alpha=alpha, color=color, label=label, edgecolor="none")
        return True

    # 2. Ghost billing rate
    if "ghost_billing_rate" in df.columns:
        fig, ax = plt.subplots(figsize=(8, 4))
        for label, color in palette.items():
            sub = df[df[lbl]==label]["ghost_billing_rate"]
            safe_hist(ax, sub, 40, color, "Fraud" if label else "Not Fraud")
        ax.set_title("Ghost Billing Rate by Fraud Label (Post-Death Claims)")
        ax.set_xlabel("Fraction of Claims After Beneficiary Death")
        ax.set_ylabel("Number of Providers")
        ax.legend()
        ax.spines[["top","right"]].set_visible(False)
        save(fig, "02_ghost_billing_rate.png")

    # 3. Total reimbursement distribution
    if "total_reimbursement" in df.columns:
        fig, axes = plt.subplots(1, 2, figsize=(13, 4))
        cap = df["total_reimbursement"].quantile(0.97)
        for label, ax in zip([0, 1], axes):
            data = df[df[lbl]==label]["total_reimbursement"].clip(upper=cap)
            safe_hist(ax, data, 50, palette[label], None, alpha=0.85)
            ax.set_title(f"{'Fraud' if label else 'Not Fraud'} — Total Reimbursement")
            ax.set_xlabel("Total Provider Reimbursement ($)")
            ax.set_ylabel("Count")
            ax.spines[["top","right"]].set_visible(False)
        plt.suptitle("Provider Total Reimbursement by Fraud Label", fontsize=12)
        save(fig, "03_total_reimbursement.png")

    # 4. Physician stacking rate
    if "avg_physician_count" in df.columns:
        fig, ax = plt.subplots(figsize=(7, 4))
        for label, color in palette.items():
            sub = df[df[lbl]==label]["avg_physician_count"]
            safe_hist(ax, sub, 20, color, "Fraud" if label else "Not Fraud")
        ax.set_title("Avg Physicians per Claim by Fraud Label (Physician Stacking)")
        ax.set_xlabel("Average Physician Count")
        ax.set_ylabel("Number of Providers")
        ax.legend()
        ax.spines[["top","right"]].set_visible(False)
        save(fig, "04_physician_stacking.png")

    # 5. Chronic burden
    if "avg_chronic_burden" in df.columns:
        fig, ax = plt.subplots(figsize=(8, 4))
        for label, color in palette.items():
            sub = df[df[lbl]==label]["avg_chronic_burden"]
            safe_hist(ax, sub, 25, color, "Fraud" if label else "Not Fraud")
        ax.set_title("Avg Chronic Condition Burden by Fraud Label")
        ax.set_xlabel("Average Chronic Conditions per Claim")
        ax.set_ylabel("Number of Providers")
        ax.legend()
        ax.spines[["top","right"]].set_visible(False)
        save(fig, "05_chronic_burden.png")

    # 6. Charge vs peer ratio (upcoding signal) — skipped if all-NaN (no CMS state match)
    if "charge_vs_peer_ratio" in df.columns and df["charge_vs_peer_ratio"].notna().any():
        fig, ax = plt.subplots(figsize=(8, 4))
        cap = df["charge_vs_peer_ratio"].quantile(0.97)
        for label, color in palette.items():
            sub = df[df[lbl]==label]["charge_vs_peer_ratio"].clip(upper=cap)
            safe_hist(ax, sub, 40, color, "Fraud" if label else "Not Fraud")
        ax.set_title("Provider Charge vs Peer Median (Upcoding Signal)")
        ax.set_xlabel("Provider Total Charge / Peer Median Charge")
        ax.set_ylabel("Number of Providers")
        ax.legend()
        ax.spines[["top","right"]].set_visible(False)
        save(fig, "06_charge_vs_peer_ratio.png")
    else:
        logger.info("    Skipped: 06_charge_vs_peer_ratio.png (no CMS state match — all NaN)")

    # 7. IP vs OP ratio
    if "ip_vs_op_ratio" in df.columns and df["ip_vs_op_ratio"].notna().any():
        fig, ax = plt.subplots(figsize=(8, 4))
        cap = df["ip_vs_op_ratio"].quantile(0.97)
        for label, color in palette.items():
            sub = df[df[lbl]==label]["ip_vs_op_ratio"].clip(upper=cap)
            safe_hist(ax, sub, 40, color, "Fraud" if label else "Not Fraud")
        ax.set_title("Inpatient vs Outpatient Reimbursement Ratio by Fraud Label")
        ax.set_xlabel("IP Annual Reimbursement / OP Annual Reimbursement")
        ax.set_ylabel("Number of Providers")
        ax.legend()
        ax.spines[["top","right"]].set_visible(False)
        save(fig, "07_ip_vs_op_ratio.png")
    else:
        logger.info("    Skipped: 07_ip_vs_op_ratio.png (all NaN)")

    # 8. Feature correlation heatmap
    all_feature_cols = BASE_PROVIDER_FEATURES + CC_RATE_COLS + PEER_FEATURE_COLS
    available = [f for f in all_feature_cols if f in df.columns and f != lbl]
    num_df    = df[available + [lbl]].select_dtypes(include=[np.number])
    corr_vals = num_df.corr()[[lbl]].drop(lbl).sort_values(lbl, ascending=False)
    top20     = pd.concat([corr_vals.head(10), corr_vals.tail(10)])

    fig, ax = plt.subplots(figsize=(6, 9))
    sns.heatmap(top20, annot=True, fmt=".2f", cmap="RdYlGn",
                center=0, linewidths=0.4, ax=ax, cbar_kws={"shrink": 0.6})
    ax.set_title("Top 20 Provider Feature Correlations\nwith Fraud Label", fontsize=12)
    ax.set_xticklabels(["Corr. w/ Fraud"])
    save(fig, "08_feature_correlation.png")

    logger.info(f"\n  EDA complete — plots saved to: {eda_dir}")


def run_cross_validation(X, y, logger, n_splits=5):
    """Run Stratified K-Fold Cross-Validation for unbiased metric evaluation."""
    logger.info("\n" + "="*70)
    logger.info(f"  STEP 5B — STRATIFIED {n_splits}-FOLD CROSS-VALIDATION")
    logger.info("="*70)

    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE)
    auc_scores, ap_scores = [], []

    for fold, (train_idx, val_idx) in enumerate(skf.split(X, y), 1):
        X_tr_f, y_tr_f = X[train_idx], y[train_idx]
        X_va_f, y_va_f = X[val_idx], y[val_idx]

        neg, pos = np.bincount(y_tr_f.astype(int))
        scale_pw = round(neg / pos, 4)

        fold_model = XGBClassifier(
            n_estimators=300, max_depth=5, min_child_weight=3,
            learning_rate=0.03, gamma=0.1, reg_alpha=0.1, reg_lambda=1.0,
            subsample=0.80, colsample_bytree=0.80, scale_pos_weight=scale_pw,
            tree_method="hist", eval_metric="aucpr", random_state=RANDOM_STATE,
            n_jobs=-1, verbosity=0
        )
        fold_model.fit(X_tr_f, y_tr_f, eval_set=[(X_va_f, y_va_f)], verbose=False)
        probs = fold_model.predict_proba(X_va_f)[:, 1]
        
        auc_f = roc_auc_score(y_va_f, probs)
        ap_f  = average_precision_score(y_va_f, probs)
        auc_scores.append(auc_f)
        ap_scores.append(ap_f)
        logger.info(f"  Fold {fold}/{n_splits} — ROC-AUC: {auc_f:.4f}  |  PR-AUC (AP): {ap_f:.4f}")

    mean_auc, std_auc = np.mean(auc_scores), np.std(auc_scores)
    mean_ap, std_ap   = np.mean(ap_scores), np.std(ap_scores)
    logger.info(f"\n  Cross-Validation Results ({n_splits}-Fold Stratified):")
    logger.info(f"    Mean ROC-AUC : {mean_auc:.4f} ± {std_auc:.4f}")
    logger.info(f"    Mean PR-AUC  : {mean_ap:.4f} ± {std_ap:.4f}")
    return {"cv_auc_mean": mean_auc, "cv_auc_std": std_auc, "cv_ap_mean": mean_ap, "cv_ap_std": std_ap}


# ──────────────────────────────────────────────────────────────────────────────
# 11.  XGBOOST TRAINING
# ──────────────────────────────────────────────────────────────────────────────
def train_xgboost(X_train, y_train, X_val, y_val, logger) -> XGBClassifier:
    """Train XGBoost with early stopping on validation AUCPR."""
    neg, pos   = np.bincount(y_train.astype(int))
    scale_pw   = round(neg / pos, 4)
    logger.info(f"\n  Class balance  →  Neg: {neg:,}  |  Pos: {pos:,}")
    logger.info(f"  scale_pos_weight = {scale_pw}")

    model = XGBClassifier(
        n_estimators          = 1000,
        max_depth             = 5,
        min_child_weight      = 3,
        learning_rate         = 0.02,
        gamma                 = 0.1,
        reg_alpha             = 0.1,
        reg_lambda            = 1.0,
        subsample             = 0.80,
        colsample_bytree      = 0.80,
        colsample_bylevel     = 0.80,
        scale_pos_weight      = scale_pw,
        tree_method           = "hist",
        eval_metric           = "aucpr",
        early_stopping_rounds = 40,
        random_state          = RANDOM_STATE,
        n_jobs                = -1,
        verbosity             = 1,
    )

    logger.info("\n  Training XGBoost v2 (Provider Level)  ...")
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=100)
    logger.info(f"\n  Best iteration  : {model.best_iteration}")
    logger.info(f"  Best AUCPR score: {model.best_score:.6f}")
    return model


# ──────────────────────────────────────────────────────────────────────────────
# 12.  PER-RISK-TIER VALIDATION METRICS
# ──────────────────────────────────────────────────────────────────────────────
# TIER_BINS and TIER_LABELS imported from config.py — single source of truth.
# Do NOT redefine them here.

def evaluate_risk_tiers(y_true, y_prob, logger):
    """
    Break validation metrics down by risk tier.
    Reports: count, actual_fraud_rate (precision), recall per tier.
    This answers the payment-integrity question:
      'If I work the Critical tier first, what fraction is actually fraud?'
    """
    logger.info("\n  Risk-Tier Validation Breakdown (Holdout Set):")
    logger.info(f"  {'Tier':<12} {'N':>6} {'Fraud%':>8} {'Precision':>10} {'Recall':>9} {'Coverage':>10}")
    logger.info("  " + "-" * 62)

    tiers = pd.cut(y_prob, bins=TIER_BINS, labels=TIER_LABELS, right=True)
    tier_results = []
    total_fraud = y_true.sum()

    for tier in TIER_LABELS:
        mask = tiers == tier
        if mask.sum() == 0:
            logger.info(f"  {tier:<12} {'0':>6} {'—':>8} {'—':>10} {'—':>9} {'—':>10}")
            continue
        n          = mask.sum()
        n_fraud    = y_true[mask].sum()
        precision  = n_fraud / n  if n > 0 else 0.0
        recall     = n_fraud / total_fraud if total_fraud > 0 else 0.0
        coverage   = n / len(y_true)
        tier_results.append({"tier": tier, "count": n, "fraud_count": n_fraud,
                              "precision": precision, "recall": recall, "coverage": coverage})
        logger.info(f"  {tier:<12} {n:>6,} {precision*100:>7.1f}% {precision:>10.4f} {recall:>9.4f} {coverage*100:>9.1f}%")

    logger.info("  " + "-" * 62)
    logger.info("  Precision = fraction of flagged providers who are truly fraudulent.")
    logger.info("  Recall    = fraction of all fraudulent providers captured in tier.")
    return tier_results


# ──────────────────────────────────────────────────────────────────────────────
# 13.  EVALUATION + PLOTS
# ──────────────────────────────────────────────────────────────────────────────
def evaluate_and_plot(model, X_val, y_val, feature_cols, output_dir, logger):
    """Compute all metrics and save evaluation plots."""
    logger.info("\n" + "="*70)
    logger.info("  STEP 7 — MODEL EVALUATION")
    logger.info("="*70)

    plot_dir = os.path.join(output_dir, "model_plots")
    os.makedirs(plot_dir, exist_ok=True)

    y_prob = model.predict_proba(X_val)[:, 1]
    y_pred = (y_prob >= FRAUD_THRESHOLD).astype(int)

    auc = roc_auc_score(y_val, y_prob)
    ap  = average_precision_score(y_val, y_prob)
    f1  = f1_score(y_val, y_pred)
    mcc = matthews_corrcoef(y_val, y_pred)

    logger.info(f"\n  Threshold used  : {FRAUD_THRESHOLD}")
    logger.info(f"  ROC-AUC         : {auc:.4f}")
    logger.info(f"  Avg Precision   : {ap:.4f}")
    logger.info(f"  F1 Score        : {f1:.4f}")
    logger.info(f"  MCC             : {mcc:.4f}")
    logger.info(f"\n  Classification Report:\n")
    logger.info(classification_report(y_val, y_pred, target_names=["Not Fraud", "Fraud"]))

    def save_plot(fig, name):
        fig.savefig(os.path.join(plot_dir, name), dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info(f"    Saved: {name}")

    # ROC Curve
    fpr, tpr, _ = roc_curve(y_val, y_prob)
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(fpr, tpr, color="#1565C0", lw=2.5, label=f"XGBoost v2 AUC = {auc:.4f}")
    ax.fill_between(fpr, tpr, alpha=0.08, color="#1565C0")
    ax.plot([0,1],[0,1],"k--", lw=1, label="Random")
    ax.set_xlabel("False Positive Rate", fontsize=11)
    ax.set_ylabel("True Positive Rate", fontsize=11)
    ax.set_title("ROC Curve — Provider-Level Fraud Detection (v2)", fontsize=12)
    ax.legend(fontsize=10)
    ax.spines[["top","right"]].set_visible(False)
    save_plot(fig, "01_roc_curve.png")

    # Precision-Recall Curve
    prec, rec, thresholds = precision_recall_curve(y_val, y_prob)
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(rec, prec, color="#C62828", lw=2.5, label=f"AP = {ap:.4f}")
    ax.fill_between(rec, prec, alpha=0.08, color="#C62828")
    ax.set_xlabel("Recall", fontsize=11)
    ax.set_ylabel("Precision", fontsize=11)
    ax.set_title("Precision-Recall Curve — Provider-Level Fraud (v2)", fontsize=12)
    ax.legend(fontsize=10)
    ax.spines[["top","right"]].set_visible(False)
    save_plot(fig, "02_precision_recall_curve.png")

    # Confusion Matrix
    cm  = confusion_matrix(y_val, y_pred)
    fig, ax = plt.subplots(figsize=(5, 4))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=["Not Fraud","Fraud"],
                yticklabels=["Not Fraud","Fraud"],
                linewidths=0.5, ax=ax, annot_kws={"size": 14})
    ax.set_title("Confusion Matrix — Provider Level v2", fontsize=12)
    ax.set_xlabel("Predicted Label")
    ax.set_ylabel("True Label")
    save_plot(fig, "03_confusion_matrix.png")

    # Feature Importance (top 25)
    active_fnames = [f for f in feature_cols if f in feature_cols]
    imp_df = (pd.DataFrame({
                  "feature"   : feature_cols[:len(model.feature_importances_)],
                  "importance": model.feature_importances_,
              })
              .sort_values("importance", ascending=False)
              .head(25))
    fig, ax = plt.subplots(figsize=(9, 7))
    colors = ["#1565C0" if i < 5 else "#64B5F6" for i in range(len(imp_df))]
    ax.barh(imp_df["feature"][::-1], imp_df["importance"][::-1],
            color=colors[::-1], edgecolor="none")
    ax.set_title("XGBoost v2 — Top 25 Feature Importances\n(Provider-Level, gain)", fontsize=12)
    ax.set_xlabel("Importance (gain)")
    ax.spines[["top","right"]].set_visible(False)
    save_plot(fig, "04_feature_importance.png")

    logger.info(f"\n  Model plots saved to: {plot_dir}")

    # Per-risk-tier breakdown (the payment-integrity precision/recall requirement)
    tier_metrics = evaluate_risk_tiers(y_val, y_prob, logger)

    return {"roc_auc": auc, "avg_precision": ap, "f1": f1, "mcc": mcc,
            "tier_metrics": tier_metrics}


# ──────────────────────────────────────────────────────────────────────────────
# 13.  SAVE ARTIFACTS
# ──────────────────────────────────────────────────────────────────────────────
def save_artifacts(model, feature_cols, encoders, medians,
                    metrics, output_dir, logger) -> str:
    """Save everything needed for inference."""
    artifacts = {
        "model"        : model,
        "feature_cols" : feature_cols,
        "cat_cols"     : CAT_COLS,
        "encoders"     : encoders,
        "medians"      : medians,
        "threshold"    : FRAUD_THRESHOLD,
        "metrics"      : metrics,
        "trained_at"   : datetime.now().isoformat(),
        "chronic_cols" : CHRONIC_COLS,
        "model_version": "v2_provider_level",
    }
    pkl_path = os.path.join(output_dir, "xgboost_fraud_model_v2.pkl")
    with open(pkl_path, "wb") as f:
        pickle.dump(artifacts, f)
    logger.info(f"\n  Model artifacts saved → {pkl_path}")
    return pkl_path


# ──────────────────────────────────────────────────────────────────────────────
# 14.  SCORE PROVIDERS + RISK TIERS
# ──────────────────────────────────────────────────────────────────────────────
def score_providers_and_save(model, test_prov_df, feature_cols,
                               output_dir, logger) -> pd.DataFrame:
    """Score test providers and save CSV investigation queue."""
    logger.info("\n" + "="*70)
    logger.info("  STEP 8 — SCORING PROVIDER TEST SET")
    logger.info("="*70)

    active = [f for f in feature_cols if f in test_prov_df.columns]
    X_test  = test_prov_df[active].values

    fraud_proba = model.predict_proba(X_test)[:, 1]
    fraud_pred  = (fraud_proba >= FRAUD_THRESHOLD).astype(int)

    result = test_prov_df[["Provider"]].copy()
    if "total_claims" in test_prov_df.columns:
        result["total_claims"]         = test_prov_df["total_claims"]
    if "unique_beneficiaries" in test_prov_df.columns:
        result["unique_beneficiaries"] = test_prov_df["unique_beneficiaries"]
    if "total_reimbursement" in test_prov_df.columns:
        result["total_reimbursement"]  = test_prov_df["total_reimbursement"]

    result["fraud_score"]     = fraud_proba.round(4)
    result["fraud_predicted"] = fraud_pred
    result["risk_tier"]       = pd.cut(
        fraud_proba,
        bins   = TIER_BINS,    # from config.py — single source of truth
        labels = TIER_LABELS,
        right  = True,
    )

    result = result.sort_values("fraud_score", ascending=False)

    logger.info("\n  Risk Tier Distribution (test providers):")
    tier_counts = result["risk_tier"].value_counts().sort_index()
    for tier, cnt in tier_counts.items():
        logger.info(f"    {tier:<10}: {cnt:>6,}  ({cnt/len(result)*100:.1f}%)")

    out_path = os.path.join(output_dir, "fraud_predictions_providers.csv")
    result.to_csv(out_path, index=False)
    logger.info(f"\n  Provider predictions saved → {out_path}")

    # Risk tier bar chart
    fig, ax = plt.subplots(figsize=(7, 4))
    colors = ["#4CAF50","#FFC107","#FF5722","#B71C1C"]
    vals   = [tier_counts.get(t, 0) for t in ["Low","Medium","High","Critical"]]
    bars   = ax.bar(["Low","Medium","High","Critical"], vals,
                    color=colors, edgecolor="white")
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f"{v:,}\n({v/len(result)*100:.1f}%)",
                ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax.set_title("Provider Investigation Queue — Risk Tier Distribution (v2)", fontsize=11)
    ax.set_ylabel("Number of Providers")
    ax.spines[["top","right"]].set_visible(False)
    os.makedirs(os.path.join(output_dir, "model_plots"), exist_ok=True)
    fig.savefig(os.path.join(output_dir, "model_plots", "05_provider_risk_tiers.png"),
                dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("    Saved: 05_provider_risk_tiers.png")

    return result


# ──────────────────────────────────────────────────────────────────────────────
# 15.  MAIN ORCHESTRATOR
# ──────────────────────────────────────────────────────────────────────────────
def main():
    logger = setup_logger(OUTPUT_DIR)
    start  = datetime.now()

    logger.info("\n" + "="*70)
    logger.info("  Medicare Provider-Level Fraud Detection — XGBoost v2")
    logger.info(f"  Started: {start.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*70)

    # Step 1: Load data
    dfs = load_data(logger)

    # Step 2: Aggregate Kaggle train → provider rows
    train_prov = aggregate_to_provider(dfs["train"], has_label=True, logger=logger)
    test_prov  = aggregate_to_provider(dfs["test"],  has_label=False, logger=logger)

    # Step 4: Build and join CMS peer benchmarks
    peer_df    = build_cms_peer_benchmarks(dfs["cms"], logger)
    train_prov = join_cms_peer_features(train_prov, peer_df, logger)
    test_prov  = join_cms_peer_features(test_prov,  peer_df, logger)

    # Step 5: EDA
    run_eda(train_prov, OUTPUT_DIR, logger)

    # Step 6: Build final feature list
    all_feature_cols = BASE_PROVIDER_FEATURES + CC_RATE_COLS + PEER_FEATURE_COLS
    active_features  = [f for f in all_feature_cols if f in train_prov.columns]
    logger.info(f"\n  Active features: {len(active_features)}")
    logger.info(f"  Feature list: {active_features}")

    # Step 7: Train/val split + impute/encode
    y      = train_prov["fraud_label"].values
    X_df   = train_prov[active_features].copy()
    y_test  = test_prov["fraud_label"].values
    Xt_df  = test_prov[active_features].copy()

    X_df, Xt_df, encoders, medians = impute_and_encode(X_df, Xt_df,
                                                         active_features, logger)

    X_tr, X_val, y_tr, y_val = train_test_split(
        X_df.values, y, test_size=TEST_SIZE,
        random_state=RANDOM_STATE, stratify=y
    )

    logger.info(f"\n  Train set : {X_tr.shape[0]:,} providers")
    logger.info(f"  Val set   : {X_val.shape[0]:,} providers")

    # Step 7b: 5-Fold Stratified Cross-Validation
    cv_results = run_cross_validation(X_df.values, y, logger, n_splits=5)

    # Step 8: Train XGBoost
    logger.info("\n" + "="*70)
    logger.info("  STEP 6 — XGBOOST TRAINING")
    logger.info("="*70)
    model = train_xgboost(X_tr, y_tr, X_val, y_val, logger)

    # Step 9: Evaluate
    metrics = evaluate_and_plot(model, X_val, y_val, active_features, OUTPUT_DIR, logger)

    # Step 10: Save artifacts
    pkl_path = save_artifacts(model, active_features, encoders, medians,
                               metrics, OUTPUT_DIR, logger)

    # Step 11: Score test providers
    score_providers_and_save(model, Xt_df.assign(Provider=test_prov["Provider"].values),
                              active_features, OUTPUT_DIR, logger)

    elapsed = datetime.now() - start
    logger.info(f"\n{'='*70}")
    logger.info(f"  XGBoost v2 Training Complete — {elapsed}")
    logger.info(f"  Model saved to: {pkl_path}")
    logger.info(f"{'='*70}\n")


if __name__ == "__main__":
    main()
