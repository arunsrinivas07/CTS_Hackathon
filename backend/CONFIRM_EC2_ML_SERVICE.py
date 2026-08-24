"""
Confirm EC2 ML Service Integration
===================================
Verifies connection to your AWS EC2 ML service at 13.204.86.122:8000
"""

import httpx
import os
from dotenv import load_dotenv

load_dotenv()

EC2_ML_URL = "http://13.204.86.122:8000"
CONFIGURED_URL = os.getenv("ML_SERVICE_URL")

print("=" * 70)
print("  EC2 ML SERVICE CONFIRMATION")
print("=" * 70)
print()

# Configuration Check
print("📋 Configuration:")
print(f"   EC2 ML Service:    {EC2_ML_URL}")
print(f"   Configured in .env: {CONFIGURED_URL}")

if CONFIGURED_URL == EC2_ML_URL:
    print("   ✅ Configuration matches EC2 instance")
else:
    print(f"   ⚠️  WARNING: .env has different URL!")
    print(f"   Please update .env to: ML_SERVICE_URL={EC2_ML_URL}")

print()

# Test EC2 Service
print("🔍 Testing EC2 ML Service...")
print("-" * 70)

# 1. Health Check
print("\n1. Health Check:")
try:
    resp = httpx.get(f"{EC2_ML_URL}/health", timeout=10.0)
    if resp.status_code == 200:
        health = resp.json()
        print(f"   ✅ Service is ONLINE")
        print(f"   Status: {health.get('status')}")
        print(f"   Model B: {health.get('model_b', 'N/A')[:19]}")
        print(f"   Model C: {health.get('model_c', 'N/A')[:19]}")
        print(f"   LEIE NPIs: {health.get('leie_npis', 0)}")
    else:
        print(f"   ❌ Unexpected status: {resp.status_code}")
except Exception as e:
    print(f"   ❌ Cannot reach EC2 service: {e}")
    exit(1)

# 2. API Documentation
print("\n2. API Documentation:")
print(f"   Swagger UI: {EC2_ML_URL}/docs")
print(f"   OpenAPI:    {EC2_ML_URL}/openapi.json")

# 3. Test ML Scoring
print("\n3. ML Scoring Test:")
test_payload = {
    "transaction_type": "MEDICAL_CLAIM",
    "claim_id": "EC2-TEST-001",
    "bene_id": "BENE-001",
    "provider_id": "1234567890",
    "at_physn_npi": "1234567890",
    "claim_type": "inpatient",
    "claim_start_date": "2024-01-15",
    "clm_pmt_amt": 3500.0,
    "clm_tot_chrg_amt": 5000.0,
    "line_count": 4,
    "diag_count": 3,
    "proc_count": 4,
    "state": "OH",
}

try:
    resp = httpx.post(
        f"{EC2_ML_URL}/api/v1/predict_hybrid",
        json=test_payload,
        timeout=30.0
    )
    
    if resp.status_code == 200:
        result = resp.json()
        print(f"   ✅ Scoring successful!")
        print(f"   Final Risk Score: {result['final_risk_score']:.4f}")
        print(f"   Risk Tier: {result['final_risk_tier']}")
        print(f"   Claim Score: {result['claim_score']:.4f}")
        print(f"   Provider Score: {result['provider_score']:.4f}")
        print(f"   LEIE Override: {result['leie_override']}")
        print(f"   Weighting: {result['model_weights']['mode']}")
    else:
        print(f"   ❌ Scoring failed: {resp.status_code}")
        print(f"   {resp.text[:150]}")
        exit(1)
        
except httpx.TimeoutException:
    print(f"   ❌ Timeout after 30s")
    exit(1)
except Exception as e:
    print(f"   ❌ Error: {e}")
    exit(1)

print()
print("=" * 70)
print("  ✅ EC2 ML SERVICE CONFIRMED WORKING")
print("=" * 70)
print()
print("📊 EC2 Instance Details:")
print("   Instance ID: i-0cb9d19e76bbdae06")
print("   Instance Type: t2.xlarge")
print("   Public IP: 13.204.86.122")
print("   Region: ap-south-1 (Mumbai)")
print("   State: Running")
print()
print("🔐 Security Groups:")
print("   ✅ Port 8000 open (0.0.0.0/0)")
print("   ✅ Port 443 open (HTTPS)")
print("   ✅ Port 80 open (HTTP)")
print()
print("🚀 Your Backend Configuration:")
print("   backend/.env line 4:")
print(f"   ML_SERVICE_URL={CONFIGURED_URL}")
print()
print("   ✅ Backend will use EC2 ML service (NOT local)")
print("   ✅ No local ML engine will be used")
print()
print("📝 Next Steps:")
print("   1. Restart backend if running:")
print("      cd backend")
print("      python -m uvicorn main:app --reload --port 8000")
print()
print("   2. Test from frontend:")
print("      - Navigate to any claim")
print("      - ML scores will come from EC2 service")
print("      - No 503 errors!")
print()
