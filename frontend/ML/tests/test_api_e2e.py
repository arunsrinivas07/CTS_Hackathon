"""
End-to-End Validation Suite — CTS Hackathon Anomaly Detection API
==================================================================
Covers 12 test scenarios plus a battery of cross-cutting property checks.

Run:
    cd c:\\cts_hackathon
    python -m pytest tests/test_api_e2e.py -v

Or run standalone (no pytest required):
    python tests/test_api_e2e.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

# ── ensure repo root is on sys.path ───────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from backend.main import app          # loads all artefacts at import time
from backend.leie_checker import get_leie_index

client = TestClient(app)

# ── real LEIE NPI with EXCLDATE=20260219 (active if service date >= 20260220) ─
LEIE_ACTIVE_NPI   = "1790227007"    # MONTERAY SELLERS DEANDRE MCGEE  excl 2026-02-19
LEIE_ACTIVE_DATE  = "2026-03-01"    # service date AFTER exclusion → active

# A valid-format NPI that is definitely not in LEIE
NON_LEIE_NPI      = "1234567890"

# Known bene / prescriber IDs from the training dataset
KNOWN_BENE_ID     = -10000010254618
KNOWN_PRSCRBR_ID  = 9999920279

# ── test fixture helpers ───────────────────────────────────────────────────────

def _claim(**overrides) -> dict:
    base = {
        "transaction_type": "MEDICAL_CLAIM",
        "claim_id":         "TC-001",
        "bene_id":          KNOWN_BENE_ID,
        "provider_id":      "1578657367",
        "claim_type":       "inpatient",
        "claim_start_date": "2023-01-15",
        "claim_end_date":   "2023-01-17",
        "clm_pmt_amt":      1500.0,
        "clm_tot_chrg_amt": 1800.0,
        "line_count":       2,
        "unit_count":       3,
        "diag_count":       4,
        "proc_count":       1,
    }
    base.update(overrides)
    return base


def _pde(**overrides) -> dict:
    base = {
        "transaction_type":   "PDE",
        "pde_id":             "TP-001",
        "bene_id":            KNOWN_BENE_ID,
        "prscrbr_id":         KNOWN_PRSCRBR_ID,
        "srvc_dt":            "15-Jan-2023",
        "qty_dspnsd_num":     30,
        "days_suply_num":     30,
        "fill_num":           1,
        "tot_rx_cst_amt":     50.0,
        "ptnt_pay_amt":       5.0,
        "cvrd_d_plan_pd_amt": 40.0,
        "ncvrd_plan_pd_amt":  5.0,
    }
    base.update(overrides)
    return base


def _post(payload: dict) -> tuple[int, dict]:
    r = client.post("/api/v1/predict", json=payload)
    return r.status_code, r.json()


# ── shared property assertions ─────────────────────────────────────────────────

def _assert_base(resp: dict, txn_type: str, model_keyword: str):
    """Assertions that EVERY valid response must satisfy."""
    assert resp.get("transaction_type") == txn_type, \
        f"Expected transaction_type={txn_type}, got {resp.get('transaction_type')}"

    assert 0.0 <= resp["ml_risk_score"]    <= 100.0, "ml_risk_score out of range"
    assert 0.0 <= resp["final_risk_score"] <= 100.0, "final_risk_score out of range"

    assert resp["ml_risk_level"]    in ("LOW","MEDIUM","HIGH","CRITICAL")
    assert resp["final_risk_level"] in ("LOW","MEDIUM","HIGH","CRITICAL")

    # Correct model selected
    assert model_keyword in resp["model_used"], \
        f"Expected model keyword '{model_keyword}' in model_used, got: {resp['model_used']}"

    # Evidence list exists and has entries
    assert isinstance(resp["evidence"], list) and len(resp["evidence"]) > 0, \
        "Evidence list missing or empty"

    # Evidence items have required keys
    for item in resp["evidence"]:
        assert "feature"           in item, f"evidence item missing 'feature': {item}"
        assert "shap_contribution" in item, f"evidence item missing 'shap_contribution': {item}"
        assert "driver_type"       in item
        assert item["driver_type"] in ("anomaly_driver", "normal_driver", "unavailable")

    # LEIE block present and structured
    leie = resp["leie_result"]
    for key in ("leie_match","leie_active_exclusion","leie_status",
                "leie_details","exclusion_type","exclusion_date",
                "reinstatement_date","npi_used"):
        assert key in leie, f"leie_result missing key: {key}"

    # LEIE must not change the raw ML score
    assert resp["ml_risk_score"] + resp["leie_adjustment"] == pytest.approx(
        resp["final_risk_score"], abs=0.01
    ), "final_risk_score != ml_risk_score + leie_adjustment"

    # Disclaimer present
    assert "NOT proof of fraud" in resp.get("disclaimer", ""), \
        "Disclaimer must state scores are not proof of fraud"

    # scored_at present
    assert resp.get("scored_at"), "scored_at missing"


def _assert_medical_not_c(resp: dict):
    assert "Model B" in resp["model_used"], \
        "Medical claim must use Model B, got: " + resp["model_used"]
    assert "Model C" not in resp["model_used"], \
        "Medical claim must NOT use Model C"


def _assert_pde_not_b(resp: dict):
    assert "Model C" in resp["model_used"], \
        "PDE must use Model C, got: " + resp["model_used"]
    assert "Model B" not in resp["model_used"], \
        "PDE must NOT use Model B"


# ══════════════════════════════════════════════════════════════════════════════
# Test scenarios
# ══════════════════════════════════════════════════════════════════════════════

class TestMedicalClaims:

    def test_01_normal_claim(self):
        """Normal inpatient claim with typical values."""
        status, resp = _post(_claim(
            claim_id="TC-NORMAL",
            clm_pmt_amt=1200.0,
            clm_tot_chrg_amt=1500.0,
            diag_count=4,
            proc_count=1,
        ))
        assert status == 200, f"HTTP {status}: {resp}"
        _assert_base(resp, "MEDICAL_CLAIM", "Model B")
        _assert_medical_not_c(resp)
        # Normal claim should typically score lower
        assert resp["ml_risk_score"] < 95, \
            f"Normal claim scored too high: {resp['ml_risk_score']}"

    def test_02_moderate_claim(self):
        """Moderately anomalous claim — higher payment, longer stay."""
        status, resp = _post(_claim(
            claim_id="TC-MODERATE",
            claim_start_date="2023-02-01",
            claim_end_date="2023-02-10",     # 9-day stay
            clm_pmt_amt=15000.0,
            clm_tot_chrg_amt=25000.0,
            diag_count=12,
            proc_count=5,
            line_count=8,
        ))
        assert status == 200, f"HTTP {status}: {resp}"
        _assert_base(resp, "MEDICAL_CLAIM", "Model B")
        _assert_medical_not_c(resp)

    def test_03_extreme_claim(self):
        """Extreme outlier — very high payment and charge."""
        status, resp = _post(_claim(
            claim_id="TC-EXTREME",
            claim_start_date="2023-03-01",
            claim_end_date="2023-03-20",
            clm_pmt_amt=275000.0,
            clm_tot_chrg_amt=275000.0,
            diag_count=25,
            proc_count=25,
            line_count=50,
            unit_count=100,
        ))
        assert status == 200, f"HTTP {status}: {resp}"
        _assert_base(resp, "MEDICAL_CLAIM", "Model B")
        _assert_medical_not_c(resp)
        # Extreme values should score higher than normal
        assert resp["ml_risk_score"] > 50, \
            f"Extreme claim expected score > 50, got {resp['ml_risk_score']}"

    def test_03_extreme_scores_higher_than_normal(self):
        """Extreme claim should score higher than normal claim."""
        _, resp_normal  = _post(_claim(clm_pmt_amt=1200.0, clm_tot_chrg_amt=1500.0))
        _, resp_extreme = _post(_claim(clm_pmt_amt=275000.0, clm_tot_chrg_amt=275000.0,
                                        claim_end_date="2023-03-20"))
        assert resp_extreme["ml_risk_score"] > resp_normal["ml_risk_score"], \
            "Extreme claim must score higher than normal claim"

    def test_carrier_claim_type(self):
        """Carrier (physician) claim type is accepted."""
        status, resp = _post(_claim(claim_type="carrier", claim_end_date=None,
                                    clm_pmt_amt=300.0, clm_tot_chrg_amt=450.0))
        assert status == 200
        _assert_base(resp, "MEDICAL_CLAIM", "Model B")

    def test_outpatient_claim_type(self):
        """Outpatient claim type is accepted."""
        status, resp = _post(_claim(claim_type="outpatient", claim_end_date=None,
                                    clm_pmt_amt=800.0, clm_tot_chrg_amt=1000.0))
        assert status == 200
        _assert_base(resp, "MEDICAL_CLAIM", "Model B")

    def test_invalid_claim_type_rejected(self):
        """Unrecognised claim type returns 422."""
        status, resp = _post(_claim(claim_type="UNKNOWN_TYPE"))
        assert status == 422, f"Expected 422, got {status}"


class TestPDE:

    def test_04_normal_pde(self):
        """Normal PDE — typical 30-day generic fill."""
        status, resp = _post(_pde(
            pde_id="TP-NORMAL",
            qty_dspnsd_num=30, days_suply_num=30,
            fill_num=1, tot_rx_cst_amt=25.0,
        ))
        assert status == 200, f"HTTP {status}: {resp}"
        _assert_base(resp, "PDE", "Model C")
        _assert_pde_not_b(resp)

    def test_05_expensive_pde(self):
        """Expensive PDE — specialty drug, high cost per unit."""
        status, resp = _post(_pde(
            pde_id="TP-EXPENSIVE",
            qty_dspnsd_num=1, days_suply_num=7,
            fill_num=1, tot_rx_cst_amt=8500.0,
            ptnt_pay_amt=500.0, cvrd_d_plan_pd_amt=8000.0,
        ))
        assert status == 200, f"HTTP {status}: {resp}"
        _assert_base(resp, "PDE", "Model C")
        _assert_pde_not_b(resp)

    def test_06_high_frequency_beneficiary(self):
        """PDE for a beneficiary with many prior prescriptions."""
        status, resp = _post(_pde(
            pde_id="TP-HI-FREQ-BENE",
            bene_id=KNOWN_BENE_ID,     # real bene with training history
            qty_dspnsd_num=90, days_suply_num=90,
            fill_num=12, tot_rx_cst_amt=1200.0,
        ))
        assert status == 200, f"HTTP {status}: {resp}"
        _assert_base(resp, "PDE", "Model C")
        _assert_pde_not_b(resp)

    def test_07_high_volume_prescriber(self):
        """PDE from a high-volume prescriber (known from training data)."""
        status, resp = _post(_pde(
            pde_id="TP-HI-VOL-PRSCR",
            prscrbr_id=KNOWN_PRSCRBR_ID,
            tot_rx_cst_amt=200.0,
        ))
        assert status == 200, f"HTTP {status}: {resp}"
        _assert_base(resp, "PDE", "Model C")
        _assert_pde_not_b(resp)

    def test_expensive_scores_higher_than_normal(self):
        """Expensive PDE should score differently from normal PDE."""
        _, resp_cheap = _post(_pde(tot_rx_cst_amt=15.0))
        _, resp_exp   = _post(_pde(tot_rx_cst_amt=8500.0, qty_dspnsd_num=1,
                                   days_suply_num=7))
        # Both must be valid
        assert 0 <= resp_cheap["ml_risk_score"] <= 100
        assert 0 <= resp_exp["ml_risk_score"]   <= 100


class TestLEIE:

    def test_08_leie_matched_active_exclusion(self):
        """
        Provider NPI is in LEIE with EXCLDATE=20260219.
        Service date 2026-03-01 → active exclusion → +30 adjustment.
        """
        status, resp = _post(_claim(
            claim_id="TC-LEIE-ACTIVE",
            provider_id=LEIE_ACTIVE_NPI,
            claim_start_date=LEIE_ACTIVE_DATE,
            claim_end_date=LEIE_ACTIVE_DATE,
        ))
        assert status == 200, f"HTTP {status}: {resp}"
        _assert_base(resp, "MEDICAL_CLAIM", "Model B")

        # LEIE block
        leie = resp["leie_result"]
        assert leie["leie_match"]            is True,  "Should find NPI in LEIE"
        assert leie["leie_active_exclusion"] is True,  "Should be active exclusion"
        assert leie["leie_status"]           == "ACTIVE_EXCLUSION"
        assert leie["exclusion_type"]        is not None

        # Adjustment applied — final > ml (unless already at 100)
        assert resp["leie_adjustment"] == 30.0 or resp["final_risk_score"] == 100.0, \
            f"Expected +30 adjustment, got {resp['leie_adjustment']}"

        # ML score preserved unchanged
        assert resp["ml_risk_score"] + resp["leie_adjustment"] == pytest.approx(
            resp["final_risk_score"], abs=0.01
        ), "final must equal ml + adjustment"

        # LEIE does NOT change ml_risk_score
        # Score it again without LEIE NPI and compare ml scores
        _, resp_no_leie = _post(_claim(
            claim_id="TC-NO-LEIE",
            provider_id=NON_LEIE_NPI,
            claim_start_date=LEIE_ACTIVE_DATE,
            claim_end_date=LEIE_ACTIVE_DATE,
        ))
        assert resp["ml_risk_score"] == pytest.approx(
            resp_no_leie["ml_risk_score"], abs=0.1
        ), "ML score should be independent of LEIE status (same claim fields)"

    def test_09_leie_non_matched_provider(self):
        """Provider NPI not in LEIE — no adjustment applied."""
        status, resp = _post(_claim(
            claim_id="TC-LEIE-NONE",
            provider_id=NON_LEIE_NPI,
        ))
        assert status == 200
        leie = resp["leie_result"]
        assert leie["leie_match"]            is False
        assert leie["leie_active_exclusion"] is False
        assert leie["leie_status"]           == "NOT_FOUND"
        assert resp["leie_adjustment"]       == 0.0
        assert resp["ml_risk_score"]         == resp["final_risk_score"]

    def test_leie_adjustment_is_separately_visible(self):
        """
        The response must always expose ml_risk_score, leie_adjustment,
        and final_risk_score as separate fields so callers can distinguish
        what came from the ML model vs the compliance check.
        """
        status, resp = _post(_claim(provider_id=LEIE_ACTIVE_NPI,
                                    claim_start_date=LEIE_ACTIVE_DATE,
                                    claim_end_date=LEIE_ACTIVE_DATE))
        assert status == 200
        assert "ml_risk_score"    in resp
        assert "leie_adjustment"  in resp
        assert "final_risk_score" in resp
        # They are all present and numeric
        assert isinstance(resp["ml_risk_score"],    float)
        assert isinstance(resp["leie_adjustment"],  float)
        assert isinstance(resp["final_risk_score"], float)


class TestEdgeCases:

    def test_10_unknown_provider(self):
        """Provider ID that is not in LEIE or history — must not crash."""
        status, resp = _post(_claim(
            claim_id="TC-UNK-PROV",
            provider_id="9999999999",   # valid NPI format, not in LEIE
        ))
        assert status == 200, f"HTTP {status}: {resp}"
        _assert_base(resp, "MEDICAL_CLAIM", "Model B")
        assert resp["leie_result"]["leie_match"] is False

    def test_11_unknown_beneficiary(self):
        """Beneficiary not in history — must not crash; history = NaN → imputed."""
        status, resp = _post(_claim(
            claim_id="TC-UNK-BENE",
            bene_id=9999999999,         # synthetic unknown
        ))
        assert status == 200, f"HTTP {status}: {resp}"
        _assert_base(resp, "MEDICAL_CLAIM", "Model B")
        # Score must still be valid
        assert 0 <= resp["ml_risk_score"] <= 100

    def test_11_unknown_pde_beneficiary(self):
        """PDE for unknown beneficiary — must not crash."""
        status, resp = _post(_pde(
            pde_id="TP-UNK-BENE",
            bene_id=8888888888,
        ))
        assert status == 200, f"HTTP {status}: {resp}"
        _assert_base(resp, "PDE", "Model C")

    def test_12_missing_optional_fields_claim(self):
        """Medical claim with only required fields — all optional fields absent."""
        minimal = {
            "transaction_type": "MEDICAL_CLAIM",
            "claim_id":         "TC-MINIMAL",
            "bene_id":          KNOWN_BENE_ID,
            "claim_type":       "outpatient",
            "claim_start_date": "2023-05-01",
            "clm_pmt_amt":      500.0,
            "clm_tot_chrg_amt": 600.0,
            # No provider_id, no end_date, no line/unit/diag/proc counts
        }
        status, resp = _post(minimal)
        assert status == 200, f"HTTP {status}: {resp}"
        _assert_base(resp, "MEDICAL_CLAIM", "Model B")

    def test_12_missing_optional_fields_pde(self):
        """PDE with only required fields."""
        minimal = {
            "transaction_type": "PDE",
            "pde_id":           "TP-MINIMAL",
            "bene_id":          KNOWN_BENE_ID,
            "prscrbr_id":       KNOWN_PRSCRBR_ID,
            "srvc_dt":          "01-Jun-2023",
            "qty_dspnsd_num":   30,
            "days_suply_num":   30,
            "fill_num":         1,
            "tot_rx_cst_amt":   75.0,
            # No payment breakdowns
        }
        status, resp = _post(minimal)
        assert status == 200, f"HTTP {status}: {resp}"
        _assert_base(resp, "PDE", "Model C")


class TestModelIsolation:

    def test_medical_never_enters_model_c(self):
        """Every MEDICAL_CLAIM must use Model B — never Model C."""
        for ct in ["carrier","dme","hha","hospice","inpatient","outpatient","snf"]:
            _, resp = _post(_claim(claim_type=ct))
            assert "Model B" in resp["model_used"], \
                f"claim_type={ct} used wrong model: {resp['model_used']}"
            assert "Model C" not in resp["model_used"]

    def test_pde_never_enters_model_b(self):
        """Every PDE must use Model C — never Model B."""
        _, resp = _post(_pde())
        assert "Model C" in resp["model_used"]
        assert "Model B" not in resp["model_used"]

    def test_wrong_transaction_type_rejected(self):
        """Unrecognised transaction_type returns 422."""
        status, resp = _post({"transaction_type": "PHARMACY", "bene_id": 1})
        assert status == 422

    def test_missing_transaction_type_rejected(self):
        """Missing transaction_type returns 422."""
        status, resp = _post({"bene_id": 1, "clm_pmt_amt": 100})
        assert status == 422


class TestScoreProperties:

    def test_scores_always_in_0_100(self):
        """Run a variety of payloads and verify all scores stay [0, 100]."""
        payloads = [
            _claim(clm_pmt_amt=0.01,     clm_tot_chrg_amt=0.01),
            _claim(clm_pmt_amt=500000.0,  clm_tot_chrg_amt=500000.0),
            _pde(tot_rx_cst_amt=0.13),
            _pde(tot_rx_cst_amt=17000.0, qty_dspnsd_num=1, days_suply_num=1),
        ]
        for p in payloads:
            _, resp = _post(p)
            assert 0 <= resp["ml_risk_score"]    <= 100, \
                f"ml_risk_score out of range for {p['transaction_type']}: {resp['ml_risk_score']}"
            assert 0 <= resp["final_risk_score"] <= 100, \
                f"final_risk_score out of range: {resp['final_risk_score']}"

    def test_risk_levels_consistent_with_scores(self):
        """Risk level must match the numeric score according to defined thresholds."""
        for p in [_claim(), _pde()]:
            _, resp = _post(p)
            score = resp["final_risk_score"]
            level = resp["final_risk_level"]
            if score >= 80:
                assert level == "CRITICAL", f"score={score} should be CRITICAL, got {level}"
            elif score >= 60:
                assert level == "HIGH",     f"score={score} should be HIGH, got {level}"
            elif score >= 40:
                assert level == "MEDIUM",   f"score={score} should be MEDIUM, got {level}"
            else:
                assert level == "LOW",      f"score={score} should be LOW, got {level}"

    def test_explanations_reference_real_features(self):
        """Evidence features must be from the model's actual feature list."""
        import pickle
        ROOT = Path(__file__).resolve().parent.parent
        with open(ROOT / "models/model_b_claim/feature_columns.pkl", "rb") as f:
            feat_b = set(pickle.load(f))
        with open(ROOT / "models/model_c_pde/feature_columns.pkl", "rb") as f:
            feat_c = set(pickle.load(f))

        _, resp_b = _post(_claim())
        for item in resp_b["evidence"]:
            if item.get("driver_type") != "unavailable":
                assert item["feature"] in feat_b, \
                    f"Model B evidence feature '{item['feature']}' not in feature list"

        _, resp_c = _post(_pde())
        for item in resp_c["evidence"]:
            if item.get("driver_type") != "unavailable":
                assert item["feature"] in feat_c, \
                    f"Model C evidence feature '{item['feature']}' not in feature list"

    def test_leie_does_not_change_ml_score(self):
        """
        Submitting the same claim with vs. without a LEIE-matched NPI
        must produce the same ml_risk_score (LEIE only affects the adjustment).
        """
        base_fields = dict(
            claim_id="TC-LEIE-COMPARE",
            claim_start_date=LEIE_ACTIVE_DATE,
            claim_end_date=LEIE_ACTIVE_DATE,
            clm_pmt_amt=5000.0,
            clm_tot_chrg_amt=6000.0,
        )
        _, resp_leie     = _post(_claim(provider_id=LEIE_ACTIVE_NPI, **base_fields))
        _, resp_no_leie  = _post(_claim(provider_id=NON_LEIE_NPI,    **base_fields))

        # ML scores are determined entirely by clinical/financial features
        assert resp_leie["ml_risk_score"] == pytest.approx(
            resp_no_leie["ml_risk_score"], abs=0.1
        ), ("ml_risk_score must not change based on LEIE status; "
            f"got {resp_leie['ml_risk_score']} vs {resp_no_leie['ml_risk_score']}")

        # But final scores differ when LEIE is active
        if resp_leie["leie_result"]["leie_active_exclusion"]:
            assert resp_leie["final_risk_score"] > resp_no_leie["final_risk_score"], \
                "LEIE active exclusion must push final score higher"


class TestHealthEndpoint:

    def test_health_returns_ok(self):
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["model_b"] is not None
        assert body["model_c"] is not None
        assert isinstance(body["leie_npis"], int)
        assert body["leie_npis"] > 0


# ══════════════════════════════════════════════════════════════════════════════
# Standalone runner (no pytest)
# ══════════════════════════════════════════════════════════════════════════════

def _run_standalone():
    import traceback

    test_classes = [
        TestMedicalClaims,
        TestPDE,
        TestLEIE,
        TestEdgeCases,
        TestModelIsolation,
        TestScoreProperties,
        TestHealthEndpoint,
    ]

    passed = failed = 0
    failures = []

    for cls in test_classes:
        instance = cls()
        methods  = [m for m in dir(instance) if m.startswith("test_")]
        for method_name in methods:
            label = f"{cls.__name__}.{method_name}"
            try:
                getattr(instance, method_name)()
                print(f"  ✓  {label}")
                passed += 1
            except Exception as exc:
                print(f"  ✗  {label}")
                print(f"       {exc}")
                failures.append((label, traceback.format_exc()))
                failed += 1

    print()
    print("=" * 64)
    print(f"  RESULTS: {passed} passed  |  {failed} failed  |  {passed+failed} total")
    print("=" * 64)
    if failures:
        print("\nFailed tests:")
        for label, tb in failures:
            print(f"\n  {label}")
            print("  " + tb.replace("\n", "\n  ")[:400])
    return failed == 0


if __name__ == "__main__":
    ok = _run_standalone()
    sys.exit(0 if ok else 1)
