"""
backend/provider_feature_engine.py
==================================
Provider-Level Feature Engineering & CMS Peer Benchmark Integration
-------------------------------------------------------------------
Builds the 59 provider-level behavioral features and joins CMS state/specialty
peer benchmarks used by the XGBoost v2 Fraud Model.
"""

from __future__ import annotations

import logging
from typing import Any
import numpy as np
import pandas as pd

# ── Thresholds & Configuration ────────────────────────────────────────────────
FRAUD_THRESHOLD = 0.40

TIER_BINS   = [-np.inf, 0.40, 0.55, 0.75, np.inf]
TIER_LABELS = ["Low", "Medium", "High", "Critical"]

DATE_COLS = [
    "ClaimStartDt", "ClaimEndDt", "AdmissionDt", "DischargeDt", "DOB", "DOD"
]

CAT_COLS = [
    "primary_state",
]

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

CMS_USECOLS = [
    "Rndrng_Prvdr_State_Abrvtn",
    "Rndrng_Prvdr_Type",
    "Tot_Benes",
    "Tot_Sbmtd_Chrg",
    "Tot_Mdcr_Alowd_Amt",
    "Tot_Mdcr_Pymt_Amt",
    "Tot_Mdcr_Stdzd_Amt",
    "Drug_Tot_Benes",
    "Drug_Tot_Srvcs",
    "Drug_Sbmtd_Chrg",
    "Drug_Mdcr_Pymt_Amt",
    "Med_Sprsn_Ind",
    "Med_Tot_HCPCS_Cds",
    "Med_Tot_Benes",
    "Med_Sbmtd_Chrg",
    "Med_Mdcr_Pymt_Amt",
    "Bene_Avg_Age",
    "Bene_Avg_Risk_Scre",
    "Bene_Dual_Cnt",
    "Bene_Age_LT_65_Cnt",
    "Bene_Age_GT_84_Cnt",
    "Bene_CC_BH_Alcohol_Drug_V1_Pct",
    "Bene_CC_BH_Anxiety_V1_Pct",
    "Bene_CC_BH_Bipolar_V1_Pct",
    "Bene_CC_BH_Depress_V1_Pct",
    "Bene_CC_BH_PTSD_V1_Pct",
    "Bene_CC_BH_Schizo_OthPsy_V1_Pct",
    "Bene_CC_BH_Alz_NonAlzdem_V2_Pct",
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


def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    for col in DATE_COLS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def recode_chronic(df: pd.DataFrame) -> pd.DataFrame:
    """CMS encodes 1=Yes, 2=No -> recode to 1=Yes, 0=No."""
    for col in CHRONIC_COLS:
        if col in df.columns:
            df[col] = df[col].map({1: 1, 2: 0}).fillna(0).astype(int)
    return df


def preprocess_claims(df: pd.DataFrame) -> pd.DataFrame:
    """Apply date parsing and chronic condition recoding at claim level."""
    df = df.copy()

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

    df["HasAttending"]   = df["AttendingPhysician"].notna().astype(int)
    df["HasOperating"]   = df["OperatingPhysician"].notna().astype(int)
    df["HasOther"]       = df["OtherPhysician"].notna().astype(int)
    df["PhysicianCount"] = df["HasAttending"] + df["HasOperating"] + df["HasOther"]

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


def aggregate_to_provider(df: pd.DataFrame, has_label: bool = False, logger: Any = None) -> pd.DataFrame:
    """Aggregate claim-level rows to one row per Provider."""
    df = preprocess_claims(df)

    agg_dict = {
        "ClaimID"                 : "count",
        "BeneID"                  : "nunique",
        "InscClaimAmtReimbursed"  : ["sum", "mean", "max", "std"],
        "DeductibleAmtPaid"       : "mean",
        "ClaimDurationDays"       : "mean",
        "AdmissionToDischarge"    : "mean",
        "AgeAtClaim"              : "mean",
        "ClaimAfterDeath"         : "mean",
        "PhysicianCount"          : "mean",
        "DiagnosisCodeCount"      : "mean",
        "ProcedureCodeCount"      : "mean",
        "ChronicCondCount"        : "mean",
        "ClaimTypeIP"             : "mean",
        "TotalAnnualReimbursement": "mean",
        "IPAnnualReimbursementAmt": "mean",
        "OPAnnualReimbursementAmt": "mean",
        "IPAnnualDeductibleAmt"   : "mean",
        "OPAnnualDeductibleAmt"   : "mean",
        "IsDead"                  : "max",
        "RenalDiseaseIndicator"   : lambda x: (x.astype(str) == "1").mean(),
        "State"                   : lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else "UNKNOWN",
    }

    for cc in CHRONIC_COLS:
        if cc in df.columns:
            agg_dict[cc] = "mean"

    prov_df = df.groupby("Provider").agg(agg_dict)

    # Flatten MultiIndex columns
    cols = []
    for c in prov_df.columns:
        if isinstance(c, tuple):
            base, stat = c[0], c[1]
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

    for cc in CHRONIC_COLS:
        old = f"{cc}_mean"
        if old in prov_df.columns:
            rename_map[old] = f"cc_{cc.replace('ChronicCond_', '').lower()}_rate"

    prov_df = prov_df.rename(columns=rename_map)

    # Derived ratio features
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

    return prov_df


def build_cms_peer_benchmarks(cms_df: pd.DataFrame, logger: Any = None) -> pd.DataFrame:
    """Aggregate CMS Provider Master by (State x ProviderType) to build peer group benchmarks."""
    cms = cms_df.copy()
    cms["Rndrng_Prvdr_State_Abrvtn"] = cms["Rndrng_Prvdr_State_Abrvtn"].astype(str).str.strip().str.upper()
    cms["Rndrng_Prvdr_Type"]         = cms["Rndrng_Prvdr_Type"].astype(str).str.strip().str.lower()

    for c in ["Drug_Mdcr_Pymt_Amt", "Med_Mdcr_Pymt_Amt", "Tot_Sbmtd_Chrg",
              "Tot_Mdcr_Pymt_Amt", "Tot_Mdcr_Stdzd_Amt", "Tot_Mdcr_Alowd_Amt",
              "Drug_Tot_Benes", "Med_Tot_Benes", "Tot_Benes",
              "Drug_Sbmtd_Chrg", "Med_Sbmtd_Chrg", "Rndrng_Prvdr_RUCA"]:
        if c in cms.columns:
            cms[c] = pd.to_numeric(cms[c], errors="coerce")

    if "Drug_Mdcr_Pymt_Amt" in cms.columns and "Med_Mdcr_Pymt_Amt" in cms.columns:
        cms["drug_to_medical_ratio"] = (
            cms["Drug_Mdcr_Pymt_Amt"] /
            (cms["Drug_Mdcr_Pymt_Amt"] + cms["Med_Mdcr_Pymt_Amt"]).replace(0, np.nan)
        )

    numeric_cols = [c for c in cms.columns if c not in ("Rndrng_Prvdr_State_Abrvtn", "Rndrng_Prvdr_Type")]
    for c in numeric_cols:
        if cms[c].dtype == object:
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

    peer = cms.groupby(group_key).apply(peer_agg, include_groups=False).reset_index()
    return peer


def join_cms_peer_features(prov_df: pd.DataFrame, peer_df: pd.DataFrame, logger: Any = None) -> pd.DataFrame:
    """Statistical join: State x 'Internal Medicine' baseline."""
    if peer_df is None or len(peer_df) == 0:
        return prov_df

    state_col = "Rndrng_Prvdr_State_Abrvtn" if "Rndrng_Prvdr_State_Abrvtn" in peer_df.columns else "primary_state"
    if state_col not in peer_df.columns:
        return prov_df

    DEFAULT_SPECIALTY = "internal medicine"
    type_col = "Rndrng_Prvdr_Type" if "Rndrng_Prvdr_Type" in peer_df.columns else None

    if type_col is not None:
        peer_specialty = peer_df[peer_df[type_col].str.lower().str.strip() == DEFAULT_SPECIALTY].copy()
        if len(peer_specialty) == 0:
            peer_specialty = peer_df.copy()
    else:
        peer_specialty = peer_df.copy()

    peer_by_state = peer_specialty.groupby(state_col).mean(numeric_only=True).reset_index()
    peer_by_state = peer_by_state.rename(columns={state_col: "primary_state"})

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

    if "peer_median_Bene_Avg_Risk_Scre" in prov_df.columns:
        prov_df["chronic_burden_vs_peer_risk_proxy"] = (
            prov_df["avg_chronic_burden"] /
            prov_df["peer_median_Bene_Avg_Risk_Scre"].replace(0, np.nan)
        )

    return prov_df
