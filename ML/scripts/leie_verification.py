"""
LEIE Deterministic Verification Layer
=======================================
Post-model verification step for both Model B (medical claims) and
Model C (PDE prescriptions).

Architecture
------------
This module is a DETERMINISTIC RULE ENGINE, not a machine-learning model.
It is applied AFTER the anomaly models have scored each record.

  ML Score  ──►  LEIE Lookup  ──►  Final Adjusted Score
              (deterministic)

The original ML risk score is always preserved.
The LEIE check adds a documented risk adjustment when an active exclusion
is found.

IMPORTANT DISCLAIMER
---------------------
LEIE exclusion status is a compliance indicator, not proof of fraud.
An excluded provider appearing on a claim indicates a potential compliance
violation under 42 CFR Part 1001, but requires human review and verification
before any enforcement or adverse action.

The adjusted score is labelled as containing a compliance signal, not
a fraud determination.

NPI Normalisation
-----------------
Valid NPI = exactly 10 numeric digits.
Any NPI shorter than 10 digits is left-zero-padded.
Any NPI longer than 10 digits, non-numeric, or equal to 0 is treated as UNKNOWN.

LEIE Status Logic
-----------------
Active exclusion  = EXCLDATE <= service_date
                    AND (REINDATE == 0 OR REINDATE > service_date)
                    AND Record_Type == 'Exclusion'

Reinstated        = EXCLDATE <= service_date
                    AND REINDATE > 0
                    AND REINDATE <= service_date

No active exclusion = NPI not found OR exclusion date after service date

Risk Adjustment
---------------
If active exclusion found:
    adjusted_risk_score = min(100, ml_risk_score + LEIE_ADJUSTMENT)
    LEIE_ADJUSTMENT = 30 points (clearly documented additive penalty)
Otherwise:
    adjusted_risk_score = ml_risk_score

Outputs
-------
data/outputs/model_b_leie_verified.csv
data/outputs/model_c_leie_verified.csv
data/processed/reference/leie_summary.csv

Run from project root:
    python scripts/leie_verification.py
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── paths ─────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).resolve().parent.parent
LEIE_CSV   = ROOT / "data" / "raw" / "leie" / "LEIE_MASTER.csv"
HIST_CSV   = ROOT / "data" / "processed" / "medical" / "claims_with_beneficiary_history.csv"
PDE_CSV    = ROOT / "data" / "processed" / "pde" / "pde_features.csv"
MB_SCORES  = ROOT / "data" / "outputs" / "model_b_test_scores_calibrated.csv"
MC_SCORES  = ROOT / "data" / "outputs" / "model_c_pde_test_scores.csv"
OUT_DIR    = ROOT / "data" / "outputs"
REF_DIR    = ROOT / "data" / "processed" / "reference"
OUT_DIR.mkdir(parents=True, exist_ok=True)

MB_OUT      = OUT_DIR / "model_b_leie_verified.csv"
MC_OUT      = OUT_DIR / "model_c_leie_verified.csv"
SUMMARY_CSV = REF_DIR / "leie_summary.csv"

# ── constants ─────────────────────────────────────────────────────────────────
LEIE_RISK_ADJUSTMENT = 30      # additive score penalty for active exclusion
NPI_LENGTH           = 10      # standard NPI is exactly 10 digits

# EXCLTYPE descriptions (subset of common codes)
EXCLTYPE_LABELS = {
    "1128a1":  "Conviction related to Medicare/Medicaid (mandatory)",
    "1128a2":  "Patient abuse or neglect (mandatory)",
    "1128a3":  "Felony health-care related fraud (mandatory)",
    "1128a4":  "Felony controlled substance (mandatory)",
    "1128b1":  "Misdemeanor health-care fraud (permissive)",
    "1128b2":  "Licence revocation (permissive)",
    "1128b4":  "Exclusion of entities controlled by excluded persons (permissive)",
    "1128b5":  "Entity that had ownership/control relationship with sanctioned entity",
    "1128b7":  "Fraud, kickbacks, and other prohibited activities (permissive)",
    "1128b15": "Default on health education loan (permissive)",
    "1128Aa":  "Actions by licensing authorities",
}


# ── NPI normalisation ─────────────────────────────────────────────────────────

def _normalise_npi(raw) -> str | None:
    """
    Normalise any raw NPI value to a canonical 10-digit string.
    Returns None if the value cannot be a valid NPI.
    """
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return None
    s = str(raw).strip()
    # Remove trailing .0 from floats stored as strings
    if s.endswith(".0"):
        s = s[:-2]
    # Must be all digits after cleaning
    if not s.isdigit():
        return None
    val = int(s)
    if val == 0:
        return None
    # Pad to 10 digits if shorter
    s = s.zfill(NPI_LENGTH)
    if len(s) != NPI_LENGTH:
        return None
    return s


# ── LEIE index builder ────────────────────────────────────────────────────────

def _build_leie_index(leie_path: Path) -> dict:
    """
    Build a dict: {npi_string: [list of exclusion records]}.
    Each record is a dict with parsed date fields.
    Only rows with valid 10-digit NPIs are indexed.
    All records (Exclusion + Reinstatement) are kept; active-exclusion
    logic is applied at lookup time.
    """
    leie = pd.read_csv(leie_path, low_memory=False)
    print(f"  LEIE raw rows: {len(leie):,}")

    def _parse_date(val) -> int | None:
        """Parse YYYYMMDD integer date. Returns None if zero or missing."""
        try:
            v = int(val)
            return v if v > 0 else None
        except Exception:
            return None

    index: dict = {}
    valid_npi_count = 0
    for _, row in leie.iterrows():
        npi = _normalise_npi(row.get("NPI"))
        if npi is None:
            continue
        valid_npi_count += 1
        rec = {
            "npi":              npi,
            "lastname":         str(row.get("LASTNAME", "") or ""),
            "firstname":        str(row.get("FIRSTNAME", "") or ""),
            "busname":          str(row.get("BUSNAME",   "") or ""),
            "general":          str(row.get("GENERAL",   "") or ""),
            "specialty":        str(row.get("SPECIALTY", "") or ""),
            "excltype":         str(row.get("EXCLTYPE",  "") or ""),
            "excltype_label":   EXCLTYPE_LABELS.get(
                                    str(row.get("EXCLTYPE", "")), "Other exclusion"),
            "excldate":         _parse_date(row.get("EXCLDATE")),
            "reindate":         _parse_date(row.get("REINDATE")),
            "waiverdate":       _parse_date(row.get("WAIVERDATE")),
            "record_type":      str(row.get("Record_Type", "") or ""),
            "address":          str(row.get("ADDRESS",   "") or ""),
            "city":             str(row.get("CITY",      "") or ""),
            "state":            str(row.get("STATE",     "") or ""),
        }
        index.setdefault(npi, []).append(rec)

    print(f"  LEIE indexed NPIs: {len(index):,}  ({valid_npi_count:,} valid-NPI rows)")
    return index


# ── LEIE lookup ───────────────────────────────────────────────────────────────

def _leie_lookup(npi: str | None, service_date_int: int | None,
                 leie_index: dict) -> dict:
    """
    Look up a provider NPI in the LEIE index.
    Returns a structured result dict.

    service_date_int: date as YYYYMMDD integer (e.g. 20230315).
    """
    base = {
        "leie_match":            False,
        "leie_active_exclusion": False,
        "leie_status":           "NOT_FOUND",
        "leie_details":          "No LEIE record found for this NPI",
        "exclusion_type":        None,
        "exclusion_type_label":  None,
        "exclusion_date":        None,
        "reinstatement_date":    None,
        "npi_normalised":        npi,
    }

    if npi is None:
        base["leie_status"]  = "NPI_UNKNOWN"
        base["leie_details"] = "Provider NPI could not be normalised to a valid 10-digit identifier"
        return base

    records = leie_index.get(npi)
    if not records:
        return base

    base["leie_match"] = True

    # Find most recent exclusion record
    excl_recs = [r for r in records if r["record_type"] == "Exclusion"]
    if not excl_recs:
        base["leie_status"]  = "RECORD_FOUND_NO_EXCLUSION"
        base["leie_details"] = "LEIE record found but no exclusion entry"
        return base

    # Pick record with latest exclusion date
    excl_rec = max(excl_recs, key=lambda r: r["excldate"] or 0)

    excl_date = excl_rec["excldate"]
    rein_date = excl_rec["reindate"]

    base["exclusion_type"]       = excl_rec["excltype"]
    base["exclusion_type_label"] = excl_rec["excltype_label"]
    base["exclusion_date"]       = excl_date
    base["reinstatement_date"]   = rein_date

    # Build detail string
    name = (excl_rec["busname"] or
            f"{excl_rec['lastname']}, {excl_rec['firstname']}").strip(", ")
    base["leie_details"] = (
        f"Provider: {name} | "
        f"Type: {excl_rec['excltype']} ({excl_rec['excltype_label']}) | "
        f"Excluded: {excl_date} | "
        f"Reinstated: {rein_date or 'No'}"
    )

    # Active exclusion check
    if service_date_int is None:
        base["leie_status"] = "EXCLUDED_DATE_UNKNOWN"
        base["leie_details"] += " | Service date unknown — cannot verify active status"
        return base

    excl_active = (
        excl_date is not None
        and excl_date <= service_date_int
        and (rein_date is None or rein_date == 0 or rein_date > service_date_int)
    )
    reinstated = (
        excl_date is not None
        and excl_date <= service_date_int
        and rein_date is not None
        and rein_date > 0
        and rein_date <= service_date_int
    )
    future_excl = excl_date is not None and excl_date > service_date_int

    if excl_active:
        base["leie_active_exclusion"] = True
        base["leie_status"]  = "ACTIVE_EXCLUSION"
        base["leie_details"] += f" | STATUS: ACTIVE on service date {service_date_int}"
    elif reinstated:
        base["leie_status"]  = "REINSTATED"
        base["leie_details"] += f" | STATUS: Reinstated before service date {service_date_int}"
    elif future_excl:
        base["leie_status"]  = "EXCLUDED_AFTER_SERVICE"
        base["leie_details"] += f" | STATUS: Exclusion occurred after service date"
    else:
        base["leie_status"]  = "EXCLUDED_STATUS_UNCLEAR"

    return base


def _apply_risk_adjustment(ml_score: float,
                           leie_result: dict,
                           adjustment: float = LEIE_RISK_ADJUSTMENT) -> tuple[float, str]:
    """
    Apply documented risk adjustment.
    Returns (adjusted_score, adjustment_reason).
    """
    if leie_result["leie_active_exclusion"]:
        adj_score  = min(100.0, float(ml_score) + adjustment)
        adj_reason = (
            f"ML score {ml_score:.2f} + LEIE active exclusion adjustment "
            f"+{adjustment:.0f} = {adj_score:.2f}. "
            f"COMPLIANCE SIGNAL: Provider was actively excluded from Medicare/Medicaid "
            f"on the service date. This is NOT a fraud determination — "
            f"requires human review and verification."
        )
        return adj_score, adj_reason
    else:
        return float(ml_score), "No LEIE adjustment applied"


# ── date helper ───────────────────────────────────────────────────────────────

def _date_to_int(date_str: str | None) -> int | None:
    """Convert 'YYYY-MM-DD' string to YYYYMMDD integer."""
    if not date_str or pd.isna(date_str):
        return None
    try:
        return int(str(date_str).replace("-", "")[:8])
    except Exception:
        return None


# ── process medical claims ────────────────────────────────────────────────────

def process_model_b(leie_index: dict) -> pd.DataFrame:
    print("\n[Model B] Medical Claims LEIE Verification")
    print("-" * 50)

    # Load scored test set with calibrated risk scores
    if MB_SCORES.exists():
        scores = pd.read_csv(MB_SCORES, low_memory=False)
        risk_col = "CALIBRATED_RISK_SCORE"
    else:
        # Fall back to uncalibrated scores
        scores = pd.read_csv(
            ROOT / "data" / "outputs" / "model_b_test_scores.csv",
            low_memory=False
        )
        risk_col = "RISK_SCORE"

    print(f"  Loaded {len(scores):,} scored test rows (risk col: {risk_col})")

    # Load provider IDs and dates from history file (test year only)
    hist = pd.read_csv(
        HIST_CSV,
        usecols=["CLAIM_ID", "BENE_ID", "PROVIDER_ID", "AT_PHYSN_NPI",
                 "ORG_NPI_NUM", "CLAIM_START_DATE", "YEAR"],
        low_memory=False,
    )
    hist_test = hist[hist["YEAR"] == 2023].reset_index(drop=True)
    print(f"  History test rows (2023): {len(hist_test):,}")

    # We need CLAIM_ID to join — but the feature/score files stripped identifiers.
    # Use positional alignment: both files were split on YEAR==2023 in the same order.
    # Verify row counts match before aligning.
    if len(scores) != len(hist_test):
        print(f"  WARNING: score rows ({len(scores)}) != history rows ({len(hist_test)})")
        print("  Proceeding with available rows (min of both)")
        n = min(len(scores), len(hist_test))
        scores   = scores.iloc[:n].reset_index(drop=True)
        hist_test = hist_test.iloc[:n].reset_index(drop=True)

    # Build LEIE result for each row
    results = []
    for i in range(len(scores)):
        # Candidate NPIs: try PROVIDER_ID first, then AT_PHYSN_NPI, then ORG_NPI_NUM
        raw_ids = [
            hist_test.at[i, "PROVIDER_ID"],
            hist_test.at[i, "AT_PHYSN_NPI"],
            hist_test.at[i, "ORG_NPI_NUM"],
        ]
        svc_date_int = _date_to_int(hist_test.at[i, "CLAIM_START_DATE"])

        leie_result = {"leie_match": False, "leie_status": "NPI_UNKNOWN",
                       "leie_active_exclusion": False,
                       "leie_details": "No valid NPI found",
                       "exclusion_type": None, "exclusion_type_label": None,
                       "exclusion_date": None, "reinstatement_date": None,
                       "npi_normalised": None}

        for raw_id in raw_ids:
            npi = _normalise_npi(raw_id)
            if npi is None:
                continue
            res = _leie_lookup(npi, svc_date_int, leie_index)
            leie_result = res
            if res["leie_match"]:   # stop at first matched NPI
                break
            leie_result["npi_normalised"] = npi  # record last tried NPI

        ml_score = float(scores.at[i, risk_col]) if pd.notna(scores.at[i, risk_col]) else 0.0
        adj_score, adj_reason = _apply_risk_adjustment(ml_score, leie_result)

        results.append({
            "CLAIM_ID":                hist_test.at[i, "CLAIM_ID"],
            "BENE_ID":                 hist_test.at[i, "BENE_ID"],
            "YEAR":                    int(hist_test.at[i, "YEAR"]),
            "CLAIM_START_DATE":        hist_test.at[i, "CLAIM_START_DATE"],
            "NPI_USED":                leie_result["npi_normalised"],
            "ML_RISK_SCORE":           round(ml_score, 4),
            "ML_RISK_LEVEL":           scores.at[i, "CALIBRATED_RISK_LEVEL"]
                                        if "CALIBRATED_RISK_LEVEL" in scores.columns
                                        else scores.at[i, "RISK_LEVEL"],
            "ADJUSTED_RISK_SCORE":     round(adj_score, 4),
            "LEIE_MATCH":              leie_result["leie_match"],
            "LEIE_ACTIVE_EXCLUSION":   leie_result["leie_active_exclusion"],
            "LEIE_STATUS":             leie_result["leie_status"],
            "LEIE_DETAILS":            leie_result["leie_details"],
            "EXCLUSION_TYPE":          leie_result["exclusion_type"],
            "EXCLUSION_TYPE_LABEL":    leie_result["exclusion_type_label"],
            "EXCLUSION_DATE":          leie_result["exclusion_date"],
            "REINSTATEMENT_DATE":      leie_result["reinstatement_date"],
            "RISK_ADJUSTMENT_REASON":  adj_reason,
            "DISCLAIMER":              (
                "LEIE match is a compliance indicator requiring human review. "
                "It is not a determination of fraud or abuse."
            ),
        })

    out = pd.DataFrame(results)
    out.to_csv(MB_OUT, index=False)

    # Stats
    n_matched  = int(out["LEIE_MATCH"].sum())
    n_active   = int(out["LEIE_ACTIVE_EXCLUSION"].sum())
    n_adjusted = int((out["ADJUSTED_RISK_SCORE"] > out["ML_RISK_SCORE"]).sum())
    print(f"  LEIE matches         : {n_matched}")
    print(f"  Active exclusions    : {n_active}")
    print(f"  Risk-adjusted rows   : {n_adjusted}")
    print(f"  Status distribution  :")
    for status, cnt in out["LEIE_STATUS"].value_counts().items():
        print(f"    {status:<35}: {cnt:>7,}")
    print(f"  Saved → {MB_OUT.relative_to(ROOT)}")
    return out


# ── process PDE claims ────────────────────────────────────────────────────────

def process_model_c(leie_index: dict) -> pd.DataFrame:
    print("\n[Model C] PDE Prescriptions LEIE Verification")
    print("-" * 50)

    # Load scored test set
    scores = pd.read_csv(MC_SCORES, low_memory=False)
    risk_col = "RISK_SCORE" if "RISK_SCORE" in scores.columns else "RISK_SCORE_OVERALL"
    print(f"  Loaded {len(scores):,} scored test rows (risk col: {risk_col})")

    # Load PDE features for test year (prescriber IDs and service dates)
    pde = pd.read_csv(
        PDE_CSV,
        usecols=["PDE_ID", "BENE_ID", "PRSCRBR_ID", "SRVC_DT", "YEAR"],
        low_memory=False,
    )
    pde_test = pde[pde["YEAR"] == 2023].reset_index(drop=True)
    print(f"  PDE test rows (2023): {len(pde_test):,}")

    if len(scores) != len(pde_test):
        print(f"  WARNING: score rows ({len(scores)}) != PDE test rows ({len(pde_test)})")
        n = min(len(scores), len(pde_test))
        scores   = scores.iloc[:n].reset_index(drop=True)
        pde_test = pde_test.iloc[:n].reset_index(drop=True)

    results = []
    for i in range(len(scores)):
        raw_id       = pde_test.at[i, "PRSCRBR_ID"]
        npi          = _normalise_npi(raw_id)
        srvc_dt_str  = str(pde_test.at[i, "SRVC_DT"])
        # SRVC_DT format: '25-Mar-2015' → parse to YYYYMMDD
        try:
            svc_date_int = int(
                pd.to_datetime(srvc_dt_str, format="%d-%b-%Y")
                  .strftime("%Y%m%d")
            )
        except Exception:
            svc_date_int = _date_to_int(srvc_dt_str)

        leie_result = _leie_lookup(npi, svc_date_int, leie_index)

        ml_score  = float(scores.at[i, risk_col]) if pd.notna(scores.at[i, risk_col]) else 0.0
        adj_score, adj_reason = _apply_risk_adjustment(ml_score, leie_result)

        results.append({
            "PDE_ID":                  pde_test.at[i, "PDE_ID"],
            "BENE_ID":                 pde_test.at[i, "BENE_ID"],
            "PRSCRBR_ID":              raw_id,
            "YEAR":                    int(pde_test.at[i, "YEAR"]),
            "SRVC_DT":                 srvc_dt_str,
            "SRVC_DATE_INT":           svc_date_int,
            "NPI_USED":                leie_result["npi_normalised"],
            "ML_RISK_SCORE":           round(ml_score, 4),
            "ML_RISK_LEVEL":           scores.at[i, "RISK_LEVEL"] if "RISK_LEVEL" in scores.columns else None,
            "ADJUSTED_RISK_SCORE":     round(adj_score, 4),
            "LEIE_MATCH":              leie_result["leie_match"],
            "LEIE_ACTIVE_EXCLUSION":   leie_result["leie_active_exclusion"],
            "LEIE_STATUS":             leie_result["leie_status"],
            "LEIE_DETAILS":            leie_result["leie_details"],
            "EXCLUSION_TYPE":          leie_result["exclusion_type"],
            "EXCLUSION_TYPE_LABEL":    leie_result["exclusion_type_label"],
            "EXCLUSION_DATE":          leie_result["exclusion_date"],
            "REINSTATEMENT_DATE":      leie_result["reinstatement_date"],
            "RISK_ADJUSTMENT_REASON":  adj_reason,
            "DISCLAIMER":              (
                "LEIE match is a compliance indicator requiring human review. "
                "It is not a determination of fraud or abuse."
            ),
        })

    out = pd.DataFrame(results)
    out.to_csv(MC_OUT, index=False)

    n_matched  = int(out["LEIE_MATCH"].sum())
    n_active   = int(out["LEIE_ACTIVE_EXCLUSION"].sum())
    n_adjusted = int((out["ADJUSTED_RISK_SCORE"] > out["ML_RISK_SCORE"]).sum())
    print(f"  LEIE matches         : {n_matched}")
    print(f"  Active exclusions    : {n_active}")
    print(f"  Risk-adjusted rows   : {n_adjusted}")
    print(f"  Status distribution  :")
    for status, cnt in out["LEIE_STATUS"].value_counts().items():
        print(f"    {status:<35}: {cnt:>7,}")
    print(f"  Saved → {MC_OUT.relative_to(ROOT)}")
    return out


# ── summary report ────────────────────────────────────────────────────────────

def _build_summary(mb_out: pd.DataFrame, mc_out: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for model_label, df in [("Model B (Medical)", mb_out),
                              ("Model C (PDE)",     mc_out)]:
        n = len(df)
        for status, cnt in df["LEIE_STATUS"].value_counts().items():
            rows.append({
                "model":             model_label,
                "leie_status":       status,
                "count":             int(cnt),
                "pct_of_total":      round(cnt / n * 100, 3),
                "n_total":           n,
                "leie_adjustment_pts": LEIE_RISK_ADJUSTMENT,
                "note": (
                    "Active exclusion = EXCLDATE <= service_date AND "
                    "(REINDATE=0 OR REINDATE>service_date). "
                    "Risk adjustment = ML score + 30 points (capped at 100). "
                    "NOT a fraud determination."
                ),
            })
    return pd.DataFrame(rows)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 62)
    print("  LEIE DETERMINISTIC VERIFICATION LAYER")
    print("=" * 62)
    print("  Role: Post-model compliance check — NOT fraud detection")
    print(f"  Risk adjustment: +{LEIE_RISK_ADJUSTMENT} pts for active exclusion")
    print()

    # Build LEIE index
    print("Building LEIE index …")
    leie_index = _build_leie_index(LEIE_CSV)

    # Process both models
    mb_out = process_model_b(leie_index)
    mc_out = process_model_c(leie_index)

    # Summary
    summary = _build_summary(mb_out, mc_out)
    summary.to_csv(SUMMARY_CSV, index=False)
    print(f"\n  ✓ Summary saved → {SUMMARY_CSV.relative_to(ROOT)}")

    # Final console report
    print()
    print("=" * 62)
    print("  LEIE VERIFICATION COMPLETE")
    print("=" * 62)
    for model_label, df in [("Model B (Medical)", mb_out),
                              ("Model C (PDE)",     mc_out)]:
        print(f"\n  {model_label}:")
        print(f"    Total records          : {len(df):,}")
        print(f"    LEIE matches           : {df['LEIE_MATCH'].sum():,}")
        print(f"    Active exclusions found: {df['LEIE_ACTIVE_EXCLUSION'].sum():,}")
        n_adj = int((df['ADJUSTED_RISK_SCORE'] > df['ML_RISK_SCORE']).sum())
        print(f"    Scores adjusted        : {n_adj:,}")
        if df['LEIE_ACTIVE_EXCLUSION'].sum() > 0:
            active = df[df["LEIE_ACTIVE_EXCLUSION"]]
            print(f"    ML score range (adjusted): "
                  f"[{active['ML_RISK_SCORE'].min():.1f}, "
                  f"{active['ML_RISK_SCORE'].max():.1f}] → "
                  f"[{active['ADJUSTED_RISK_SCORE'].min():.1f}, "
                  f"{active['ADJUSTED_RISK_SCORE'].max():.1f}]")

    print()
    print("  NOTE: This synthetic dataset has 0 LEIE overlaps.")
    print("  In production with real NPI data, active exclusions will be")
    print("  detected and scores adjusted accordingly.")
    print()
    print("  DISCLAIMER: LEIE exclusion status is a compliance indicator.")
    print("  It does NOT constitute proof of fraud, abuse, or waste.")
    print("  All flagged records require human review and verification.")
    print("=" * 62)


if __name__ == "__main__":
    main()
