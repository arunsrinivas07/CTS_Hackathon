"""
Feature Engineering Engine
============================
Converts raw transaction fields into the exact feature vectors expected by
Model B (medical claims) and Model C (PDE).

History is looked up from the pre-computed historical feature tables —
never re-computed from scratch at inference time.

Peer-comparison features use the frozen training-period reference statistics
loaded once at startup.
"""

from __future__ import annotations

import json
import pickle
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# ── paths ─────────────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
ROOT  = _HERE.parent

HIST_B_CSV  = ROOT / "data" / "processed" / "medical" / "claims_with_beneficiary_history.csv"
HIST_C_CSV  = ROOT / "data" / "processed" / "pde"     / "pde_features.csv"
STATS_JSON  = ROOT / "data" / "processed" / "reference" / "medical_claim_type_stats.json"
PDE_CAL_JSON= ROOT / "data" / "processed" / "reference" / "pde_calibration.json"

# ── constants ─────────────────────────────────────────────────────────────────
CLAIM_TYPES_B = ["carrier", "dme", "hha", "hospice", "inpatient", "outpatient", "snf"]

# PDE prescriber/bene tier boundaries (from calibration)
_PRESCRIBER_TIER_LO = 189
_PRESCRIBER_TIER_HI = 728
_BENE_TIER_LO       = 38
_BENE_TIER_HI       = 136

_C = 1.4826   # MAD → consistent std estimator

# ── lazy-loaded history caches ─────────────────────────────────────────────────
_hist_b: pd.DataFrame | None = None
_hist_c: pd.DataFrame | None = None
_stats_b: dict | None        = None


def _load_hist_b() -> pd.DataFrame:
    global _hist_b
    if _hist_b is None:
        cols = [
            "BENE_ID", "CLAIM_ID", "CLAIM_TYPE", "PROVIDER_ID",
            "CLAIM_START_DATE", "CLM_PMT_AMT",
            # bene history cols
            "HIST_PREV_CLAIM_CNT", "HIST_PREV_TOTAL_PAY", "HIST_PREV_AVG_PAY",
            "HIST_PREV_MAX_PAY", "HIST_PREV_PROVIDER_CNT", "HIST_PREV_TYPE_CNT",
            "HIST_DAYS_SINCE_PREV", "HIST_DAYS_SINCE_SAME_TYPE",
            "HIST_W30_CLAIM_CNT", "HIST_W30_TOTAL_PAY", "HIST_W30_PROVIDER_CNT",
            "HIST_W90_CLAIM_CNT", "HIST_W90_TOTAL_PAY", "HIST_W90_PROVIDER_CNT",
            # bene demographic cols
            "BENE_BIRTH_DT", "SEX_IDENT_CD", "BENE_RACE_CD",
            "STATE_CODE", "BENE_DEATH_DT",
        ]
        _hist_b = pd.read_csv(HIST_B_CSV, usecols=cols, low_memory=False)
        _hist_b["CLAIM_START_DATE"] = pd.to_datetime(
            _hist_b["CLAIM_START_DATE"], errors="coerce"
        )
    return _hist_b


def _load_hist_c() -> pd.DataFrame:
    global _hist_c
    if _hist_c is None:
        cols = [
            "BENE_ID", "PRSCRBR_ID", "SRVC_DT",
            "BENE_PREV_RX_COUNT", "BENE_PREV_RX_COST",
            "BENE_PREV_AVG_RX_COST", "BENE_PREV_MAX_RX_COST",
            "BENE_RX_30D", "BENE_RX_COST_30D",
            "BENE_RX_90D", "BENE_RX_COST_90D",
            "PRESCRIBER_RX_COUNT", "PRESCRIBER_AVG_RX_COST",
            "PRESCRIBER_MAX_RX_COST", "PRESCRIBER_UNIQUE_BENEFICIARIES",
        ]
        _hist_c = pd.read_csv(HIST_C_CSV, usecols=cols, low_memory=False)
        _hist_c["SRVC_DATE"] = pd.to_datetime(
            _hist_c["SRVC_DT"], format="%d-%b-%Y", errors="coerce"
        )
    return _hist_c


def _load_stats_b() -> dict:
    global _stats_b
    if _stats_b is None:
        with open(STATS_JSON, encoding="utf-8") as f:
            _stats_b = json.load(f)
    return _stats_b


# ── shared helpers ────────────────────────────────────────────────────────────

def _safe_div(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return a / b


def _pct_rank(value: float, ref: np.ndarray) -> float:
    """Vectorised-free percentile rank for a single value."""
    n = len(ref)
    n_below = float(np.searchsorted(ref, value, side="left"))
    n_right = float(np.searchsorted(ref, value, side="right"))
    n_equal = n_right - n_below
    return float(np.clip((n_below + n_equal / 2) / n * 100, 0, 100))


def _robust_z(value: float | None, median: float | None,
              mad_scaled: float | None) -> float | None:
    if value is None or median is None or mad_scaled is None:
        return None
    if mad_scaled == 0:
        return 0.0 if value == median else float(np.sign(value - median)) * 10.0
    z = (value - median) / mad_scaled
    return float(np.clip(z, -10, 10))


def _interp_pct_rank(value: float, stats_entry: dict) -> float | None:
    """Interpolate percentile rank from the 9-point anchor table in stats JSON."""
    pcts = stats_entry.get("percentiles")
    if pcts is None or value is None:
        return None
    points = sorted((int(k[1:]), float(v)) for k, v in pcts.items())
    ranks  = [p[0] for p in points]
    values = [p[1] for p in points]
    if value <= values[0]:
        return float(ranks[0])
    if value >= values[-1]:
        return float(ranks[-1])
    for i in range(len(values) - 1):
        if values[i] <= value <= values[i + 1]:
            if values[i + 1] == values[i]:
                return float(ranks[i])
            frac = (value - values[i]) / (values[i + 1] - values[i])
            return float(ranks[i] + frac * (ranks[i + 1] - ranks[i]))
    return None


# ── Model B feature builder ───────────────────────────────────────────────────

def build_model_b_features(raw: dict) -> tuple[dict[str, float | None], dict]:
    """
    Build the 59-feature vector for Model B from raw medical claim fields.

    Parameters
    ----------
    raw : dict with keys matching ClaimRequest fields

    Returns
    -------
    features : dict[feature_name -> value]   (None for missing)
    meta     : dict with bene demographics and other lookup metadata
    """
    stats    = _load_stats_b()
    hist     = _load_hist_b()

    claim_type = str(raw.get("claim_type", "")).lower()
    claim_date = pd.to_datetime(raw.get("claim_start_date"), errors="coerce")
    bene_id    = raw.get("bene_id")
    year       = claim_date.year if pd.notna(claim_date) else None

    pmt  = _to_f(raw.get("clm_pmt_amt"))
    chrg = _to_f(raw.get("clm_tot_chrg_amt"))
    lns  = _to_f(raw.get("line_count"))
    uts  = _to_f(raw.get("unit_count"))
    diag = _to_f(raw.get("diag_count"))
    proc = _to_f(raw.get("proc_count"))
    dur  = _to_f(raw.get("claim_duration_days"))

    # ── bene history lookup ────────────────────────────────────────────────
    bene_hist = _lookup_bene_hist_b(hist, bene_id, claim_type, claim_date)
    bene_demo = _lookup_bene_demo(hist, bene_id, claim_date)

    # ── peer-comparison features ───────────────────────────────────────────
    ct_stats_entry = stats.get(claim_type, {})

    def _peer(value, metric_key):
        entry = ct_stats_entry.get(metric_key, {})
        med   = entry.get("median")
        mad   = entry.get("mad_scaled")
        vs_med  = _safe_div(value, med) if med and med != 0 else None
        rob_z   = _robust_z(value, med, mad)
        pct_r   = _interp_pct_rank(value, entry) if value is not None else None
        return vs_med, rob_z, pct_r

    pm_vs, pm_z, pm_p = _peer(pmt,  "clm_pmt_amt")
    ch_vs, ch_z, ch_p = _peer(chrg, "clm_tot_chrg_amt")
    du_vs, du_z, du_p = _peer(dur,  "claim_duration_days")
    ln_vs, ln_z, ln_p = _peer(lns,  "line_count")
    dg_vs, dg_z, dg_p = _peer(diag, "diag_count")
    pr_vs, pr_z, pr_p = _peer(proc, "proc_count")

    # ── assemble 59-feature dict ───────────────────────────────────────────
    feat: dict[str, Any] = {
        "YEAR":                              year,
        "CLM_PMT_AMT":                       pmt,
        "CLM_TOT_CHRG_AMT":                  chrg,
        "UNPAID_CHARGE":                     _to_f(max(0, (chrg or 0) - (pmt or 0))),
        "CLAIM_DURATION_DAYS":               dur,
        "LINE_COUNT":                        lns,
        "UNIT_COUNT":                        uts,
        "DIAG_COUNT":                        diag,
        "PROC_COUNT":                        proc,
        "PAYMENT_PER_LINE":                  _safe_div(pmt, lns),
        "CHARGE_PER_LINE":                   _safe_div(chrg, lns),
        "PAYMENT_PER_UNIT":                  _safe_div(pmt, uts),
        "CHARGE_PER_UNIT":                   _safe_div(chrg, uts),
        "CLAIM_PAYMENT_VS_TYPE_MEDIAN":      pm_vs,
        "CLAIM_PAYMENT_TYPE_ROBUST_Z":       pm_z,
        "CLAIM_PAYMENT_TYPE_PERCENTILE":     pm_p,
        "CLAIM_CHARGE_VS_TYPE_MEDIAN":       ch_vs,
        "CLAIM_CHARGE_TYPE_ROBUST_Z":        ch_z,
        "CLAIM_CHARGE_TYPE_PERCENTILE":      ch_p,
        "CLAIM_DURATION_DAYS_VS_TYPE_MEDIAN":du_vs,
        "CLAIM_DURATION_DAYS_TYPE_ROBUST_Z": du_z,
        "CLAIM_DURATION_DAYS_TYPE_PERCENTILE":du_p,
        "NUM_LINES_VS_TYPE_MEDIAN":          ln_vs,
        "NUM_LINES_TYPE_ROBUST_Z":           ln_z,
        "NUM_LINES_TYPE_PERCENTILE":         ln_p,
        "NUM_DIAGNOSES_VS_TYPE_MEDIAN":      dg_vs,
        "NUM_DIAGNOSES_TYPE_ROBUST_Z":       dg_z,
        "NUM_DIAGNOSES_TYPE_PERCENTILE":     dg_p,
        "NUM_PROCEDURES_VS_TYPE_MEDIAN":     pr_vs,
        "NUM_PROCEDURES_TYPE_ROBUST_Z":      pr_z,
        "NUM_PROCEDURES_TYPE_PERCENTILE":    pr_p,
        "PAYMENT_VS_BENE_PREV_AVG":          _safe_div(pmt, bene_hist.get("HIST_PREV_AVG_PAY")),
        "PAYMENT_VS_BENE_PREV_MAX":          _safe_div(pmt, bene_hist.get("HIST_PREV_MAX_PAY")),
        "BENE_AGE_AT_CLAIM":                 bene_demo.get("age"),
        "BENE_IS_DECEASED":                  bene_demo.get("is_deceased"),
        "SEX_IDENT_CD":                      bene_demo.get("sex"),
        "BENE_RACE_CD":                      bene_demo.get("race"),
        "STATE_CODE":                        bene_demo.get("state"),
        # Bene history
        "HIST_PREV_CLAIM_CNT":               bene_hist.get("HIST_PREV_CLAIM_CNT"),
        "HIST_PREV_TOTAL_PAY":               bene_hist.get("HIST_PREV_TOTAL_PAY"),
        "HIST_PREV_AVG_PAY":                 bene_hist.get("HIST_PREV_AVG_PAY"),
        "HIST_PREV_MAX_PAY":                 bene_hist.get("HIST_PREV_MAX_PAY"),
        "HIST_PREV_PROVIDER_CNT":            bene_hist.get("HIST_PREV_PROVIDER_CNT"),
        "HIST_PREV_TYPE_CNT":                bene_hist.get("HIST_PREV_TYPE_CNT"),
        "HIST_DAYS_SINCE_PREV":              bene_hist.get("HIST_DAYS_SINCE_PREV"),
        "HIST_DAYS_SINCE_SAME_TYPE":         bene_hist.get("HIST_DAYS_SINCE_SAME_TYPE"),
        "HIST_W30_CLAIM_CNT":                bene_hist.get("HIST_W30_CLAIM_CNT", 0),
        "HIST_W30_TOTAL_PAY":                bene_hist.get("HIST_W30_TOTAL_PAY", 0),
        "HIST_W30_PROVIDER_CNT":             bene_hist.get("HIST_W30_PROVIDER_CNT", 0),
        "HIST_W90_CLAIM_CNT":                bene_hist.get("HIST_W90_CLAIM_CNT", 0),
        "HIST_W90_TOTAL_PAY":                bene_hist.get("HIST_W90_TOTAL_PAY", 0),
        "HIST_W90_PROVIDER_CNT":             bene_hist.get("HIST_W90_PROVIDER_CNT", 0),
    }

    # OHE claim type
    for ct in CLAIM_TYPES_B:
        feat[f"CLMTYPE_{ct}"] = 1 if claim_type == ct else 0

    meta = {
        "claim_type":   claim_type,
        "claim_date":   str(claim_date.date()) if pd.notna(claim_date) else None,
        "year":         year,
        "bene_history": bene_hist,
        "bene_demo":    bene_demo,
    }
    return feat, meta


# ── Model B history lookup ────────────────────────────────────────────────────

def _lookup_bene_hist_b(hist: pd.DataFrame, bene_id: Any,
                         claim_type: str, claim_date: pd.Timestamp) -> dict:
    """
    Find the most recent prior row for this beneficiary and claim type
    strictly before claim_date.  Returns the precomputed HIST_ columns
    from that row (which already represent strictly-prior history).
    """
    if bene_id is None or pd.isna(claim_date):
        return {}
    bh = hist[
        (hist["BENE_ID"] == bene_id) &
        (hist["CLAIM_START_DATE"] < claim_date)
    ].sort_values("CLAIM_START_DATE")

    if bh.empty:
        return {"HIST_W30_CLAIM_CNT": 0, "HIST_W30_TOTAL_PAY": 0,
                "HIST_W30_PROVIDER_CNT": 0,
                "HIST_W90_CLAIM_CNT": 0, "HIST_W90_TOTAL_PAY": 0,
                "HIST_W90_PROVIDER_CNT": 0}

    # Take the last (most recent) prior row — its HIST_ values represent
    # cumulative history up to (but not including) that row's own date.
    # For a new claim dated after the last known, this is the best proxy.
    last_row = bh.iloc[-1]
    hist_cols = [
        "HIST_PREV_CLAIM_CNT", "HIST_PREV_TOTAL_PAY", "HIST_PREV_AVG_PAY",
        "HIST_PREV_MAX_PAY", "HIST_PREV_PROVIDER_CNT", "HIST_PREV_TYPE_CNT",
        "HIST_DAYS_SINCE_PREV", "HIST_DAYS_SINCE_SAME_TYPE",
        "HIST_W30_CLAIM_CNT", "HIST_W30_TOTAL_PAY", "HIST_W30_PROVIDER_CNT",
        "HIST_W90_CLAIM_CNT", "HIST_W90_TOTAL_PAY", "HIST_W90_PROVIDER_CNT",
    ]
    result = {}
    for c in hist_cols:
        v = last_row.get(c)
        result[c] = float(v) if pd.notna(v) else None
    # Update count to include this new claim
    result["HIST_PREV_CLAIM_CNT"] = (result.get("HIST_PREV_CLAIM_CNT") or 0) + len(bh)
    return result


def _lookup_bene_demo(hist: pd.DataFrame, bene_id: Any,
                       claim_date: pd.Timestamp) -> dict:
    rows = hist[hist["BENE_ID"] == bene_id]
    if rows.empty:
        return {"age": None, "is_deceased": 0, "sex": None, "race": None, "state": None}
    row = rows.iloc[0]
    age = None
    try:
        dob = pd.to_datetime(row.get("BENE_BIRTH_DT"), format="%d-%b-%Y", errors="coerce")
        if pd.notna(dob) and pd.notna(claim_date):
            age = float((claim_date - dob).days / 365.25)
    except Exception:
        pass
    is_deceased = 1 if pd.notna(row.get("BENE_DEATH_DT")) else 0
    return {
        "age":        age,
        "is_deceased": is_deceased,
        "sex":        _to_f(row.get("SEX_IDENT_CD")),
        "race":       _to_f(row.get("BENE_RACE_CD")),
        "state":      _to_f(row.get("STATE_CODE")),
    }


# ── Model C feature builder ───────────────────────────────────────────────────

def build_model_c_features(raw: dict) -> tuple[dict[str, float | None], dict]:
    """
    Build the 32-feature vector for Model C from raw PDE fields.
    """
    hist = _load_hist_c()

    bene_id    = raw.get("bene_id")
    prscrbr_id = raw.get("prscrbr_id")
    srvc_dt    = pd.to_datetime(raw.get("srvc_dt"), errors="coerce")
    year       = srvc_dt.year if pd.notna(srvc_dt) else None

    qty  = _to_f(raw.get("qty_dspnsd_num"))
    days = _to_f(raw.get("days_suply_num"))
    fill = _to_f(raw.get("fill_num"))
    cost = _to_f(raw.get("tot_rx_cst_amt"))
    ppay = _to_f(raw.get("ptnt_pay_amt"))
    plan = _to_f(raw.get("cvrd_d_plan_pd_amt"))
    ncvr = _to_f(raw.get("ncvrd_plan_pd_amt"))
    gdc1 = _to_f(raw.get("gdc_blw_oopt_amt"))
    gdc2 = _to_f(raw.get("gdc_abv_oopt_amt"))
    trp  = _to_f(raw.get("othr_troop_amt"))
    lics = _to_f(raw.get("lics_amt"))
    plro = _to_f(raw.get("plro_amt"))

    # History lookup
    bene_h = _lookup_bene_hist_c(hist, bene_id, srvc_dt)
    prsc_h = _lookup_prscrbr_hist(hist, prscrbr_id, srvc_dt)

    feat: dict[str, Any] = {
        "YEAR":                         year,
        "QTY_DSPNSD_NUM":               qty,
        "DAYS_SUPLY_NUM":               days,
        "FILL_NUM":                     fill,
        "TOT_RX_CST_AMT":               cost,
        "PTNT_PAY_AMT":                 ppay,
        "CVRD_D_PLAN_PD_AMT":           plan,
        "NCVRD_PLAN_PD_AMT":            ncvr,
        "GDC_BLW_OOPT_AMT":             gdc1,
        "GDC_ABV_OOPT_AMT":             gdc2,
        "OTHR_TROOP_AMT":               trp,
        "LICS_AMT":                     lics,
        "PLRO_AMT":                     plro,
        "COST_PER_UNIT":                _safe_div(cost, qty),
        "COST_PER_DAY":                 _safe_div(cost, days),
        "PATIENT_PAYMENT_RATIO":        _safe_div(ppay, cost),
        "PLAN_PAYMENT_RATIO":           _safe_div(plan, cost),
        "QUANTITY_PER_DAY":             _safe_div(qty, days),
        "DAYS_SUPPLY":                  days,
        "REFILL_FREQUENCY":             fill,
        # Bene history
        "BENE_PREV_RX_COUNT":           bene_h.get("BENE_PREV_RX_COUNT"),
        "BENE_PREV_RX_COST":            bene_h.get("BENE_PREV_RX_COST"),
        "BENE_PREV_AVG_RX_COST":        bene_h.get("BENE_PREV_AVG_RX_COST"),
        "BENE_PREV_MAX_RX_COST":        bene_h.get("BENE_PREV_MAX_RX_COST"),
        "BENE_RX_30D":                  bene_h.get("BENE_RX_30D", 0),
        "BENE_RX_COST_30D":             bene_h.get("BENE_RX_COST_30D", 0),
        "BENE_RX_90D":                  bene_h.get("BENE_RX_90D", 0),
        "BENE_RX_COST_90D":             bene_h.get("BENE_RX_COST_90D", 0),
        # Prescriber history
        "PRESCRIBER_RX_COUNT":          prsc_h.get("PRESCRIBER_RX_COUNT"),
        "PRESCRIBER_AVG_RX_COST":       prsc_h.get("PRESCRIBER_AVG_RX_COST"),
        "PRESCRIBER_MAX_RX_COST":       prsc_h.get("PRESCRIBER_MAX_RX_COST"),
        "PRESCRIBER_UNIQUE_BENEFICIARIES": prsc_h.get("PRESCRIBER_UNIQUE_BENEFICIARIES"),
    }

    meta = {
        "srvc_dt":       str(srvc_dt.date()) if pd.notna(srvc_dt) else None,
        "year":          year,
        "bene_history":  bene_h,
        "prscrbr_hist":  prsc_h,
    }
    return feat, meta


def _lookup_bene_hist_c(hist: pd.DataFrame, bene_id: Any,
                         srvc_dt: pd.Timestamp) -> dict:
    if bene_id is None or pd.isna(srvc_dt):
        return {"BENE_RX_30D": 0, "BENE_RX_COST_30D": 0,
                "BENE_RX_90D": 0, "BENE_RX_COST_90D": 0}
    bh = hist[
        (hist["BENE_ID"] == bene_id) &
        (hist["SRVC_DATE"] < srvc_dt)
    ].sort_values("SRVC_DATE")
    if bh.empty:
        return {"BENE_RX_30D": 0, "BENE_RX_COST_30D": 0,
                "BENE_RX_90D": 0, "BENE_RX_COST_90D": 0}
    last = bh.iloc[-1]
    cols = ["BENE_PREV_RX_COUNT","BENE_PREV_RX_COST","BENE_PREV_AVG_RX_COST",
            "BENE_PREV_MAX_RX_COST","BENE_RX_30D","BENE_RX_COST_30D",
            "BENE_RX_90D","BENE_RX_COST_90D"]
    return {c: (float(last[c]) if pd.notna(last.get(c)) else None) for c in cols}


def _lookup_prscrbr_hist(hist: pd.DataFrame, prscrbr_id: Any,
                          srvc_dt: pd.Timestamp) -> dict:
    if prscrbr_id is None or pd.isna(srvc_dt):
        return {}
    ph = hist[
        (hist["PRSCRBR_ID"] == prscrbr_id) &
        (hist["SRVC_DATE"] < srvc_dt)
    ].sort_values("SRVC_DATE")
    if ph.empty:
        return {}
    last = ph.iloc[-1]
    cols = ["PRESCRIBER_RX_COUNT","PRESCRIBER_AVG_RX_COST",
            "PRESCRIBER_MAX_RX_COST","PRESCRIBER_UNIQUE_BENEFICIARIES"]
    return {c: (float(last[c]) if pd.notna(last.get(c)) else None) for c in cols}


# ── utility ───────────────────────────────────────────────────────────────────

def _to_f(v: Any) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
        return None if np.isnan(f) else f
    except (TypeError, ValueError):
        return None


def features_to_array(feat: dict, ordered_cols: list[str]) -> np.ndarray:
    """Convert feature dict to numpy array in the exact column order."""
    return np.array(
        [feat.get(c) for c in ordered_cols],
        dtype=object
    ).reshape(1, -1).astype(float)
