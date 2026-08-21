import os
import sys
import pickle
import io
import json
import re
import numpy as np
import pandas as pd

from typing import List, Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR    = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    from backend2.train_xgboost_fraud_v2 import (
        preprocess_claims, aggregate_to_provider,
        BASE_PROVIDER_FEATURES, CC_RATE_COLS, PEER_FEATURE_COLS,
        CAT_COLS, CHRONIC_COLS, build_cms_peer_benchmarks, join_cms_peer_features,
        CMS_USECOLS
    )
    from backend2.config import FRAUD_THRESHOLD, TIER_BINS, TIER_LABELS, MIN_CLAIMS_FOR_PROVIDER_ML
except ImportError:
    from train_xgboost_fraud_v2 import (
        preprocess_claims, aggregate_to_provider,
        BASE_PROVIDER_FEATURES, CC_RATE_COLS, PEER_FEATURE_COLS,
        CAT_COLS, CHRONIC_COLS, build_cms_peer_benchmarks, join_cms_peer_features,
        CMS_USECOLS
    )
    from config import FRAUD_THRESHOLD, TIER_BINS, TIER_LABELS, MIN_CLAIMS_FOR_PROVIDER_ML

MODEL_DIR       = os.path.join(CURRENT_DIR, "models", "xgboost_fraud_v2")
PKL_PATH        = os.path.join(MODEL_DIR, "xgboost_fraud_model_v2.pkl")
LEIE_PATH       = os.path.join(ROOT_DIR, "processed_data", "LEIE_MASTER.csv")
CMS_PATH        = os.path.join(ROOT_DIR, "processed_data", "CMS_PROVIDER_MASTER.csv")
SAMPLE_DIR      = os.path.join(ROOT_DIR, "sample_test_files")
FRONTEND2_DIR   = os.path.join(ROOT_DIR, "frontend2")

# ──────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title   = "CareGuard AI — Provider Intelligence Dashboard v2",
    version = "2.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

plots_dir = os.path.join(MODEL_DIR, "model_plots")
os.makedirs(plots_dir, exist_ok=True)
app.mount("/plots", StaticFiles(directory=plots_dir), name="plots")

sample_files_dir = os.path.join(CURRENT_DIR, "sample_files")
os.makedirs(sample_files_dir, exist_ok=True)
app.mount("/sample_files", StaticFiles(directory=sample_files_dir), name="sample_files")

if os.path.exists(FRONTEND2_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND2_DIR), name="static")

model_artifacts  = None
leie_risk_states = set()
leie_active_df   = None    # DataFrame of active LEIE exclusions for Layer 1 direct checks
peer_lookup      = None    # Pre-built CMS peer benchmark table (state-level means)


# ──────────────────────────────────────────────────────────────────────────────
# Startup — load model + LEIE + CMS peer table
# ──────────────────────────────────────────────────────────────────────────────
def load_pipeline_artifacts():
    global model_artifacts, leie_risk_states, leie_active_df, peer_lookup

    if os.path.exists(PKL_PATH):
        with open(PKL_PATH, "rb") as f:
            model_artifacts = pickle.load(f)
        print(f"Loaded XGBoost v2 Model from {PKL_PATH}")
    else:
        print(f"WARNING: Model not found at {PKL_PATH}. Train it first with train_xgboost_fraud_v2.py")

    if os.path.exists(LEIE_PATH):
        try:
            leie = pd.read_csv(LEIE_PATH, low_memory=False)
            # Filter active exclusions (REINDATE is null or empty or 00000000)
            reindate_str = leie["REINDATE"].astype(str).str.strip()
            active_mask  = (
                (leie["Record_Type"].astype(str).str.upper().str.contains("EXCL")) &
                (leie["REINDATE"].isna() | reindate_str.isin(["", "nan", "0", "00000000"]))
            )
            leie_active_df = leie[active_mask].copy()
            leie_risk_states = set(
                leie_active_df["STATE"].dropna().astype(str).str.strip().str.upper().unique()
            )
            print(f"Loaded LEIE: {len(leie_active_df):,} active exclusions across {len(leie_risk_states)} states")
        except Exception as e:
            print(f"LEIE Notice: {e}")

    # ── CMS peer benchmarks ────────────────────────────────────────────────────
    # We store the FULL specialty-level peer table (not pre-collapsed to state).
    # join_cms_peer_features() handles the internal medicine specialty filtering
    # and state-level collapse at inference time — same path as the training script.
    # This ensures train and API use identical peer baselines.
    peer_cache_path = os.path.join(MODEL_DIR, "cms_peer_benchmarks.csv")

    # Determine data path: check datasets/ then processed_data/
    cms_candidate_paths = [
        os.path.join(ROOT_DIR, "datasets", "CMS_PROVIDER_MASTER.csv"),
        os.path.join(ROOT_DIR, "processed_data", "CMS_PROVIDER_MASTER.csv"),
        CMS_PATH,
    ]
    cms_data_path = next((p for p in cms_candidate_paths if os.path.exists(p)), None)

    if os.path.exists(peer_cache_path):
        peer_lookup = pd.read_csv(peer_cache_path)
        print(f"Loaded CMS peer benchmarks from cache: {peer_cache_path}")
        print(f"  Peer table shape: {peer_lookup.shape}")
    elif cms_data_path:
        try:
            print(f"Building CMS peer benchmarks from {cms_data_path} (first-time startup)...")
            import logging
            _lg = logging.getLogger("peer_startup")
            _lg.addHandler(logging.StreamHandler(sys.stdout))
            _lg.setLevel(logging.INFO)
            chunks = []
            for chunk in pd.read_csv(cms_data_path, usecols=CMS_USECOLS,
                                      low_memory=False, chunksize=500_000):
                chunks.append(chunk)
            cms_df = pd.concat(chunks, ignore_index=True)
            # Save full specialty-level table — do NOT pre-collapse here.
            # join_cms_peer_features does the internal medicine filter + state collapse.
            peer_lookup = build_cms_peer_benchmarks(cms_df, _lg)
            os.makedirs(MODEL_DIR, exist_ok=True)
            peer_lookup.to_csv(peer_cache_path, index=False)
            print(f"CMS peer benchmarks built and cached ({peer_lookup.shape}): {peer_cache_path}")
        except Exception as e:
            print(f"CMS peer benchmark build failed: {e}")
            peer_lookup = pd.DataFrame()
    else:
        print("CMS Provider Master not found. Running without peer benchmarks.")
        peer_lookup = pd.DataFrame()


def check_leie_direct_exclusion(provider_id: str) -> dict:
    """
    Layer 1: Deterministic LEIE Compliance Gatekeeper.
    Checks if a Provider NPI or Name is listed in active HHS OIG LEIE exclusions.
    """
    global leie_active_df
    if leie_active_df is None or leie_active_df.empty:
        return None

    prov_clean = str(provider_id).strip()
    if not prov_clean:
        return None

    # Check NPI numeric match
    if prov_clean.isdigit():
        npi_val = int(prov_clean)
        if "NPI" in leie_active_df.columns:
            matched = leie_active_df[leie_active_df["NPI"] == npi_val]
            if not matched.empty:
                row = matched.iloc[0]
                return {
                    "is_excluded": True,
                    "reason": f"Active HHS OIG Exclusion Match (NPI: {prov_clean})",
                    "excl_type": str(row.get("EXCLTYPE", "OIG_EXCLUSION")),
                    "excl_date": str(row.get("EXCLDATE", "N/A"))
                }

    # Check Name match (BUSNAME / LASTNAME)
    name_clean = prov_clean.upper()
    if len(name_clean) > 2:
        if "BUSNAME" in leie_active_df.columns and "LASTNAME" in leie_active_df.columns:
            matched = leie_active_df[
                (leie_active_df["BUSNAME"].astype(str).str.upper() == name_clean) |
                (leie_active_df["LASTNAME"].astype(str).str.upper() == name_clean)
            ]
            if not matched.empty:
                row = matched.iloc[0]
                return {
                    "is_excluded": True,
                    "reason": f"Active HHS OIG Exclusion Match (Name: {name_clean})",
                    "excl_type": str(row.get("EXCLTYPE", "OIG_EXCLUSION")),
                    "excl_date": str(row.get("EXCLDATE", "N/A"))
                }

    return None


@app.on_event("startup")
def startup_event():
    load_pipeline_artifacts()


# ──────────────────────────────────────────────────────────────────────────────
# Core inference: claim rows → provider row → model score
# ──────────────────────────────────────────────────────────────────────────────
def run_inference_on_df(raw_df: pd.DataFrame) -> pd.DataFrame:
    """
    Accept raw claim-level DataFrame (same schema as v1 PDF extraction).
    Aggregate to provider level → join CMS peer → score with v2 model.
    Returns provider-level DataFrame with fraud_score, risk_tier.
    """
    global model_artifacts, leie_risk_states, peer_lookup

    if model_artifacts is None:
        load_pipeline_artifacts()

    if model_artifacts is None:
        raise HTTPException(status_code=500, detail="v2 Model not found. Run train_xgboost_fraud_v2.py first.")

    model        = model_artifacts["model"]
    feature_cols = model_artifacts["feature_cols"]
    encoders     = model_artifacts["encoders"]
    medians      = model_artifacts["medians"]
    threshold    = model_artifacts.get("threshold", FRAUD_THRESHOLD)

    import logging
    _lg = logging.getLogger("inference_v2")
    _lg.setLevel(logging.WARNING)

    # Aggregate claims to provider level
    prov_df = aggregate_to_provider(raw_df, has_label=False, logger=_lg)

    # Join CMS peer benchmarks if available
    if peer_lookup is not None and len(peer_lookup) > 0:
        from train_xgboost_fraud_v2 import join_cms_peer_features
        prov_df = join_cms_peer_features(prov_df, peer_lookup, _lg)

    # Ensure ALL feature_cols exist in prov_df (fill missing features with median)
    for col in feature_cols:
        if col not in prov_df.columns:
            prov_df[col] = medians.get(col, 0.0)

    # Encode categoricals — map unseen states to dedicated UNKNOWN class
    for col in CAT_COLS:
        if col in prov_df.columns and col in encoders:
            le    = encoders[col]
            known = set(le.classes_)
            prov_df[col] = prov_df[col].astype(str).apply(
                lambda x: x if x in known else "UNKNOWN"
            )
            prov_df[col] = le.transform(prov_df[col])

    # Impute numerics
    for col in feature_cols:
        if col not in CAT_COLS:
            prov_df[col] = prov_df[col].fillna(medians.get(col, 0.0))

    X = prov_df[feature_cols].values
    fraud_proba = model.predict_proba(X)[:, 1]
    fraud_pred  = (fraud_proba >= threshold).astype(int)

    out_df = prov_df.copy()
    out_df["fraud_score"]     = fraud_proba.round(4)
    out_df["fraud_predicted"] = fraud_pred
    out_df["risk_tier"]       = pd.cut(
        fraud_proba,
        bins   = TIER_BINS,      # from config.py — single source of truth
        labels = TIER_LABELS,
        right  = True,
    ).astype(str)

    # Layer 1 Compliance Check Override, Human Review Flags & Low-Volume Claim Safeguards
    compliance_alerts = []
    scoring_statuses = []

    for idx, row in out_df.iterrows():
        prov_id = str(row.get("Provider", ""))
        tot_claims = int(row.get("total_claims", 1))
        ghost_rate = float(row.get("ghost_billing_rate", 0.0))
        reimb = float(row.get("avg_claim_reimbursed", 0.0))
        peer_ratio = float(row.get("charge_vs_peer_ratio", 0.0)) if ("charge_vs_peer_ratio" in row and row["charge_vs_peer_ratio"] is not None) else 0.0
        diag_density = float(row.get("avg_diagnosis_density", 0.0))
        proc_density = float(row.get("avg_procedure_density", 0.0))
        leie_check = check_leie_direct_exclusion(prov_id)

        # 1. Direct LEIE Exclusion Override (Deterministic Layer 1 Compliance Gatekeeper)
        if leie_check and leie_check.get("is_excluded"):
            out_df.at[idx, "fraud_score"]     = 1.00
            out_df.at[idx, "fraud_predicted"] = 1
            out_df.at[idx, "risk_tier"]       = "Critical"
            compliance_alerts.append(leie_check["reason"])
            scoring_statuses.append("DIRECT_LEIE_EXCLUSION_MATCH")

        # 2. Post-Death Service Date Check (Human-in-the-Loop Review Flag)
        elif ghost_rate > 0:
            current_tier = str(out_df.at[idx, "risk_tier"])
            if current_tier in ("Low", "Medium"):
                out_df.at[idx, "risk_tier"] = "High (Pending Review)"
            compliance_alerts.append("FLAG_FOR_HUMAN_REVIEW: Post-death service date detected (ClaimStartDt > DOD)")
            scoring_statuses.append("FLAGGED_FOR_HUMAN_REVIEW")

        # 3. Single Claim / Low-Volume History Safeguard (n < MIN_CLAIMS_FOR_PROVIDER_ML)
        elif tot_claims < MIN_CLAIMS_FOR_PROVIDER_ML:
            # Single-claim rule & anomaly check (extreme reimbursement, peer upcoding, procedure density)
            is_anomaly = (reimb > 25000) or (peer_ratio > 3.0) or (diag_density > 8) or (proc_density > 5)
            
            # Explicitly clear ML fraud_score to prevent misleading numerical display on low volume
            out_df.at[idx, "fraud_score"]     = None
            out_df.at[idx, "fraud_predicted"] = 1 if is_anomaly else 0

            if is_anomaly:
                out_df.at[idx, "risk_tier"] = "Single Claim (Anomaly Flagged)"
                compliance_alerts.append(f"Notice: Single-claim anomaly detected (Reimb: ${reimb:,.2f}, Peer Ratio: {peer_ratio:.2f}). Minimum {MIN_CLAIMS_FOR_PROVIDER_ML} claims required for full provider ML.")
            else:
                out_df.at[idx, "risk_tier"] = "Unrated (Insufficient History)"
                compliance_alerts.append(f"Notice: Low claim volume (n={tot_claims}). Minimum {MIN_CLAIMS_FOR_PROVIDER_ML} claims required for full provider ML profiling.")

            scoring_statuses.append("INSUFFICIENT_HISTORY_FOR_PROVIDER_ML")

        # 4. Full Provider ML Behavioral Profiling (n >= MIN_CLAIMS_FOR_PROVIDER_ML)
        else:
            compliance_alerts.append("NO_DIRECT_EXCLUSION")
            scoring_statuses.append("SCORED_BY_HYBRID_ML")

    out_df["compliance_alert"]        = compliance_alerts
    out_df["provider_scoring_status"] = scoring_statuses

    return out_df


# ──────────────────────────────────────────────────────────────────────────────
# API Endpoints
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/api/model_info")
def get_model_info():
    if model_artifacts is None:
        raise HTTPException(status_code=500, detail="v2 Model not loaded")
    return {
        "model_version"  : model_artifacts.get("model_version", "v2_provider_level"),
        "metrics"        : model_artifacts.get("metrics", {}),
        "trained_at"     : model_artifacts.get("trained_at", "N/A"),
        "threshold"      : model_artifacts.get("threshold", FRAUD_THRESHOLD),
        "features_count" : len(model_artifacts.get("feature_cols", [])),
        "leie_states_count": len(leie_risk_states),
        "cms_peer_loaded": peer_lookup is not None and len(peer_lookup) > 0,
    }


@app.get("/sample_files/{filename}")
def get_sample_file(filename: str):
    path = os.path.join(SAMPLE_DIR, filename)
    if os.path.exists(path):
        media_type = "application/pdf" if filename.endswith(".pdf") else "text/plain"
        return FileResponse(path, media_type=media_type, filename=filename)
    raise HTTPException(status_code=404, detail="Sample file not found")


@app.post("/api/predict_provider")
def predict_single_provider(claim: dict):
    """Score a single claim payload — aggregated to a single provider row."""
    df_raw = pd.DataFrame([claim])
    scored = run_inference_on_df(df_raw)
    row    = scored.iloc[0].to_dict()
    s = row.get("fraud_score")
    return {
        "provider_id"    : str(row.get("Provider", "UNKNOWN")),
        "fraud_score"    : round(float(s), 4) if s is not None and not (isinstance(s, float) and np.isnan(s)) else None,
        "fraud_predicted": int(row["fraud_predicted"]),
        "risk_tier"      : str(row["risk_tier"]),
        "total_claims"   : int(row.get("total_claims", 1)),
        "compliance_alert"       : str(row.get("compliance_alert", "")),
        "provider_scoring_status": str(row.get("provider_scoring_status", "")),
        "ghost_billing_rate"     : float(row.get("ghost_billing_rate", 0.0)),
        "avg_physician_count"    : float(row.get("avg_physician_count", 0.0)),
        "avg_chronic_burden"     : float(row.get("avg_chronic_burden", 0.0)),
        "charge_vs_peer_ratio"   : float(row["charge_vs_peer_ratio"]) if "charge_vs_peer_ratio" in row and row["charge_vs_peer_ratio"] is not None else None,
    }


@app.post("/api/predict_batch")
def predict_batch(
    claims: List[Dict[str, Any]] = Body(
        ...,
        description="Array of claim JSON objects. Multiple claims with the same Provider ID will be aggregated together.",
        example=[
            {
                "BeneID": "BENE16640", "ClaimID": "CLM72529",
                "ClaimStartDt": "2009-10-19", "ClaimEndDt": "2009-10-20",
                "Provider": "PRV57494", "InscClaimAmtReimbursed": 13000,
                "AttendingPhysician": "PHY378358", "OperatingPhysician": "PHY347733",
                "State": 52, "ClaimType": "Inpatient"
            }
        ]
    )
):
    """
    Score multiple claims for one or more providers.
    Accepts a JSON array of claim dicts. Claims with the same Provider ID are
    aggregated as a single provider profile before scoring.

    This is the endpoint to use when testing via Swagger UI with multi-claim JSON arrays.
    Minimum 5 claims per provider recommended for full provider-level ML profiling.
    """
    if not claims:
        raise HTTPException(status_code=400, detail="No claims provided.")

    df_raw = pd.DataFrame(claims)
    scored = run_inference_on_df(df_raw)

    results = []
    for _, row in scored.iterrows():
        s = row.get("fraud_score")
        cv = row.get("charge_vs_peer_ratio")
        results.append({
            "provider_id"    : str(row.get("Provider", "UNKNOWN")),
            "fraud_score"    : round(float(s), 4) if s is not None and not (isinstance(s, float) and np.isnan(s)) else None,
            "fraud_predicted": int(row["fraud_predicted"]),
            "risk_tier"      : str(row["risk_tier"]),
            "total_claims"   : int(row.get("total_claims", 1)),
            "compliance_alert"       : str(row.get("compliance_alert", "")),
            "provider_scoring_status": str(row.get("provider_scoring_status", "")),
            "ghost_billing_rate"     : float(row.get("ghost_billing_rate", 0.0)),
            "avg_physician_count"    : float(row.get("avg_physician_count", 0.0)),
            "avg_chronic_burden"     : float(row.get("avg_chronic_burden", 0.0)),
            "charge_vs_peer_ratio"   : round(float(cv), 4) if cv is not None and not (isinstance(cv, float) and np.isnan(cv)) else None,
        })

    return {
        "total_claims_submitted": len(claims),
        "total_providers_scored": len(results),
        "providers": results,
    }


@app.post("/api/predict_file")
async def predict_file(file: UploadFile = File(...)):
    """Upload a PDF, TXT, or CSV to score all claims at the provider level."""
    contents = await file.read()
    filename = file.filename.lower()

    try:
        if filename.endswith(".pdf"):
            df_raw = extract_claims_from_pdf_bytes(contents)
        elif filename.endswith(".txt"):
            text_str = contents.decode("utf-8", errors="ignore")
            claims_list = extract_multi_claims_from_text(text_str)
            if claims_list:
                df_raw = pd.DataFrame(claims_list)
            else:
                try:
                    df_raw = pd.read_csv(io.StringIO(text_str))
                except Exception:
                    single = extract_claims_via_regex_fallback(text_str)
                    df_raw = pd.DataFrame([single])
        elif filename.endswith(".csv"):
            text_str = contents.decode("utf-8", errors="ignore")
            df_raw = pd.read_csv(io.StringIO(text_str))
        else:
            df_raw = pd.read_csv(io.BytesIO(contents))

        if df_raw.empty:
            raise HTTPException(status_code=400, detail="No claim data could be extracted from the file.")

        # Save extracted JSON claims for debugging and verification
        debug_json_path = os.path.join(ROOT_DIR, "extracted_claims_debug.json")
        logs_dir = os.path.join(ROOT_DIR, "extracted_claims_logs")
        os.makedirs(logs_dir, exist_ok=True)
        filename_clean = re.sub(r"[^\w\.-]", "_", file.filename)
        history_json_path = os.path.join(logs_dir, f"extracted_{filename_clean}.json")

        try:
            records = json.loads(df_raw.to_json(orient="records", date_format="iso"))
            # 1. Update latest debug file
            with open(debug_json_path, "w", encoding="utf-8") as jf:
                json.dump(records, jf, indent=2)
                jf.flush()
            # 2. Save historic log for this specific file
            with open(history_json_path, "w", encoding="utf-8") as hf:
                json.dump(records, hf, indent=2)
                hf.flush()
            print(f"Successfully saved {len(records)} extracted claims to {debug_json_path} and {history_json_path}")
        except Exception as je:
            print(f"Notice: Could not save extracted_claims_debug.json ({je})")

        scored_df = run_inference_on_df(df_raw)

        results = []
        for _, row in scored_df.iterrows():
            r = {}
            for k, v in row.items():
                try:
                    if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
                        r[k] = None
                    elif isinstance(v, (np.integer,)):
                        r[k] = int(v)
                    elif isinstance(v, (np.floating,)):
                        r[k] = round(float(v), 4)
                    else:
                        r[k] = v
                except Exception:
                    r[k] = str(v)
            results.append(r)

        tier_counts = scored_df["risk_tier"].value_counts().to_dict()

        return {
            "filename"        : file.filename,
            "total_providers" : len(scored_df),
            "tier_counts"     : tier_counts,
            "providers"       : results,
            "model_version"   : "v2_provider_level",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse or score file: {str(e)}")


@app.get("/", response_class=HTMLResponse)
def get_dashboard():
    index_path = os.path.join(FRONTEND2_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    raise HTTPException(status_code=404, detail="Frontend2 index.html not found")


if __name__ == "__main__":
    uvicorn.run("backend2.main:app", host="127.0.0.1", port=8002, reload=True)
