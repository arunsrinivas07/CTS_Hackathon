"""
LEIE Deterministic Checker — FastAPI Module
============================================
Shared NPI normalisation and LEIE lookup used by the API at request time.
Index is built once at startup from the raw LEIE CSV.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
ROOT  = _HERE.parent
LEIE_CSV = ROOT / "data" / "raw" / "leie" / "LEIE_MASTER.csv"

LEIE_RISK_ADJUSTMENT = 30

EXCLTYPE_LABELS = {
    "1128a1":  "Conviction related to Medicare/Medicaid (mandatory)",
    "1128a2":  "Patient abuse or neglect (mandatory)",
    "1128a3":  "Felony health-care related fraud (mandatory)",
    "1128a4":  "Felony controlled substance (mandatory)",
    "1128b1":  "Misdemeanor health-care fraud (permissive)",
    "1128b2":  "License revocation (permissive)",
    "1128b4":  "Exclusion — entities controlled by sanctioned person (permissive)",
    "1128b5":  "Entity with ownership/control relationship with sanctioned entity",
    "1128b7":  "Fraud, kickbacks, and other prohibited activities (permissive)",
    "1128b15": "Default on health education loan (permissive)",
    "1128Aa":  "Actions by licensing authorities",
}

_leie_index: dict[str, list[dict]] | None = None


def normalise_npi(raw: Any) -> str | None:
    """Normalise any value to a canonical 10-digit NPI string or None."""
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return None
    s = str(raw).strip()
    if s.endswith(".0"):
        s = s[:-2]
    if not s.isdigit():
        return None
    if int(s) == 0:
        return None
    s = s.zfill(10)
    return s if len(s) == 10 else None


def _parse_date_int(val: Any) -> int | None:
    try:
        v = int(val)
        return v if v > 0 else None
    except Exception:
        return None


def get_leie_index() -> dict[str, list[dict]]:
    """Return the in-memory LEIE index, building it on first call."""
    global _leie_index
    if _leie_index is None:
        _leie_index = _build_index()
    return _leie_index


def _build_index() -> dict[str, list[dict]]:
    leie = pd.read_csv(LEIE_CSV, low_memory=False)
    index: dict = {}
    for _, row in leie.iterrows():
        npi = normalise_npi(row.get("NPI"))
        if npi is None:
            continue
        exc_type = str(row.get("EXCLTYPE", "") or "")
        rec = {
            "npi":             npi,
            "lastname":        str(row.get("LASTNAME",  "") or ""),
            "firstname":       str(row.get("FIRSTNAME", "") or ""),
            "busname":         str(row.get("BUSNAME",   "") or ""),
            "general":         str(row.get("GENERAL",   "") or ""),
            "specialty":       str(row.get("SPECIALTY", "") or ""),
            "excltype":        exc_type,
            "excltype_label":  EXCLTYPE_LABELS.get(exc_type, "Other exclusion"),
            "excldate":        _parse_date_int(row.get("EXCLDATE")),
            "reindate":        _parse_date_int(row.get("REINDATE")),
            "record_type":     str(row.get("Record_Type", "") or ""),
            "address":         str(row.get("ADDRESS", "") or ""),
            "city":            str(row.get("CITY",    "") or ""),
            "state":           str(row.get("STATE",   "") or ""),
        }
        index.setdefault(npi, []).append(rec)
    return index


def lookup(npi: str | None, service_date_int: int | None) -> dict:
    """
    Look up a provider NPI and return structured LEIE result.

    Returns fields:
        leie_match, leie_active_exclusion, leie_status, leie_details,
        exclusion_type, exclusion_type_label, exclusion_date,
        reinstatement_date, npi_normalised
    """
    index = get_leie_index()
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

    records = index.get(npi)
    if not records:
        return base

    base["leie_match"] = True
    excl_recs = [r for r in records if r["record_type"] == "Exclusion"]
    if not excl_recs:
        base["leie_status"]  = "RECORD_FOUND_NO_EXCLUSION"
        base["leie_details"] = "LEIE record found but no exclusion entry"
        return base

    excl_rec   = max(excl_recs, key=lambda r: r["excldate"] or 0)
    excl_date  = excl_rec["excldate"]
    rein_date  = excl_rec["reindate"]
    name = (excl_rec["busname"] or
            f"{excl_rec['lastname']}, {excl_rec['firstname']}").strip(", ")

    base["exclusion_type"]       = excl_rec["excltype"]
    base["exclusion_type_label"] = excl_rec["excltype_label"]
    base["exclusion_date"]       = excl_date
    base["reinstatement_date"]   = rein_date
    base["leie_details"] = (
        f"Provider: {name} | "
        f"Type: {excl_rec['excltype']} ({excl_rec['excltype_label']}) | "
        f"Excluded: {excl_date} | Reinstated: {rein_date or 'No'}"
    )

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
        excl_date is not None and excl_date <= service_date_int
        and rein_date is not None and rein_date > 0
        and rein_date <= service_date_int
    )
    future_excl = excl_date is not None and excl_date > service_date_int

    if excl_active:
        base["leie_active_exclusion"] = True
        base["leie_status"]  = "ACTIVE_EXCLUSION"
        base["leie_details"] += f" | STATUS: ACTIVE on service date {service_date_int}"
    elif reinstated:
        base["leie_status"]  = "REINSTATED"
        base["leie_details"] += " | STATUS: Reinstated before service date"
    elif future_excl:
        base["leie_status"]  = "EXCLUDED_AFTER_SERVICE"
        base["leie_details"] += " | STATUS: Exclusion occurred after service date"
    else:
        base["leie_status"]  = "EXCLUDED_STATUS_UNCLEAR"
    return base


def apply_adjustment(ml_score: float, leie_result: dict,
                     adjustment: float = LEIE_RISK_ADJUSTMENT) -> tuple[float, str]:
    if leie_result["leie_active_exclusion"]:
        adj = min(100.0, float(ml_score) + adjustment)
        reason = (
            f"ML score {ml_score:.2f} + LEIE active exclusion adjustment "
            f"+{adjustment:.0f} = {adj:.2f}. "
            "COMPLIANCE SIGNAL: Provider was actively excluded from "
            "Medicare/Medicaid on the service date. "
            "This is NOT a fraud determination — requires human review."
        )
        return adj, reason
    return float(ml_score), "No LEIE adjustment applied"
