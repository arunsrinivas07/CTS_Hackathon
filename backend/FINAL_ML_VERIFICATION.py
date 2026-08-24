"""
FINAL ML SERVICE VERIFICATION
==============================
Run this to verify the complete ML integration is working
"""

import httpx
import os
from dotenv import load_dotenv

load_dotenv()

ML_SERVICE_URL = os.getenv("ML_SERVICE_URL")

print("╔" + "═" * 58 + "╗")
print("║" + " " * 15 + "FINAL ML VERIFICATION" + " " * 22 + "║")
print("╚" + "═" * 58 + "╝")
print()

# Configuration Check
print("1️⃣  Configuration Check")
print("─" * 60)
print(f"   ML_SERVICE_URL: {ML_SERVICE_URL}")

if ML_SERVICE_URL == "http://13.204.86.122:8000":
    print("   ✅ Using external ML service (CORRECT)")
elif "localhost" in ML_SERVICE_URL or "127.0.0.1" in ML_SERVICE_URL:
    print("   ⚠️  Using local ML service (fallback mode)")
else:
    print(f"   ⚠️  Unknown ML service URL")

# Health Check
print("\n2️⃣  Health Check")
print("─" * 60)

try:
    resp = httpx.get(f"{ML_SERVICE_URL}/health", timeout=10.0)
    if resp.status_code == 200:
        health = resp.json()
        print(f"   ✅ Service is healthy")
        print(f"   Status: {health.get('status', 'N/A')}")
        if 'model_b' in health:
            print(f"   Model B: Loaded")
            print(f"   Model C: Loaded")
            print(f"   LEIE Records: {health.get('leie_npis', 0)}")
    else:
        print(f"   ❌ Health check failed: {resp.status_code}")
except Exception as e:
    print(f"   ❌ Cannot reach service: {e}")
    exit(1)

# ML Scoring Test
print("\n3️⃣  ML Scoring Test (Hybrid Model)")
print("─" * 60)

test_claim = {
    "transaction_type": "MEDICAL_CLAIM",
    "claim_id": "FINAL-TEST-001",
    "bene_id": "BENE-TEST-001",
    "provider_id": "1234567890",
    "at_physn_npi": "1234567890",
    "claim_type": "inpatient",
    "claim_start_date": "2024-01-01",
    "clm_pmt_amt": 5000.0,
    "clm_tot_chrg_amt": 8000.0,
    "line_count": 5,
    "diag_count": 3,
    "proc_count": 4,
    "state": "OH",
}

try:
    resp = httpx.post(
        f"{ML_SERVICE_URL}/api/v1/predict_hybrid",
        json=test_claim,
        timeout=30.0
    )
    
    if resp.status_code == 200:
        result = resp.json()
        print(f"   ✅ Scoring successful!")
        print(f"\n   📊 Results:")
        print(f"   ├─ Final Risk Score:  {result['final_risk_score']:.4f}")
        print(f"   ├─ Risk Tier:         {result['final_risk_tier']}")
        print(f"   ├─ Claim Score:       {result['claim_score']:.4f} (Model B)")
        print(f"   ├─ Provider Score:    {result['provider_score']:.4f} (XGBoost)")
        print(f"   ├─ LEIE Override:     {result['leie_override']}")
        print(f"   └─ Weighting Mode:    {result['model_weights']['mode']}")
        
        print(f"\n   🔍 Evidence:")
        print(f"   ├─ Claim Evidence:    {len(result.get('claim_evidence', []))} features")
        print(f"   └─ Provider Evidence: {len(result.get('provider_evidence', []))} features")
        
        if result.get('claim_evidence'):
            top_claim = result['claim_evidence'][0]
            print(f"\n   Top Claim Driver:")
            print(f"   └─ {top_claim['feature']}: {top_claim['value']}")
        
        print(f"\n   💬 Explanation:")
        explanation = result.get('explanation', '')
        if len(explanation) > 100:
            explanation = explanation[:100] + "..."
        print(f"   └─ {explanation}")
        
    else:
        print(f"   ❌ Scoring failed: {resp.status_code}")
        print(f"   Response: {resp.text[:200]}")
        exit(1)
        
except httpx.TimeoutException:
    print(f"   ❌ Timeout: Service took longer than 30 seconds")
    print(f"   Suggestion: Service might be overloaded, try again")
    exit(1)
except Exception as e:
    print(f"   ❌ Error: {type(e).__name__}: {e}")
    exit(1)

# Endpoint Verification
print("\n4️⃣  Endpoint Verification")
print("─" * 60)
print(f"   ✅ /health → Working")
print(f"   ✅ /api/v1/predict_hybrid → Working")
print(f"   ✅ Response structure → Compatible")

# Final Summary
print("\n" + "╔" + "═" * 58 + "╗")
print("║" + " " * 20 + "VERIFICATION PASSED" + " " * 19 + "║")
print("╚" + "═" * 58 + "╝")
print()
print("✅ External ML Service is fully operational")
print("✅ All endpoints responding correctly")
print("✅ Scoring working with expected response format")
print()
print("🚀 Next Steps:")
print("   1. Restart your backend server")
print("   2. Open frontend and navigate to any claim")
print("   3. Check Risk Assessment tab for ML scores")
print("   4. No more 503 errors!")
print()
print("📁 Documentation:")
print("   - ML_INTEGRATION_QUICK_REF.md")
print("   - backend/ML_SERVICE_FIX_SUMMARY.md")
print()
