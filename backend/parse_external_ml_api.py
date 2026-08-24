"""
Parse external ML API structure
"""
import httpx
import json

resp = httpx.get('http://13.204.86.122:8000/openapi.json', timeout=10)
api_spec = resp.json()

print("=" * 60)
print("EXTERNAL ML SERVICE API STRUCTURE")
print("=" * 60)
print(f"\nTitle: {api_spec['info']['title']}")
print(f"Version: {api_spec['info']['version']}")
print(f"\nDescription:\n{api_spec['info']['description']}")

print("\n" + "=" * 60)
print("AVAILABLE ENDPOINTS:")
print("=" * 60)

for path, methods in api_spec['paths'].items():
    for method, details in methods.items():
        print(f"\n{method.upper():6} {path}")
        print(f"       Summary: {details.get('summary', 'N/A')}")
        if 'description' in details and details['description']:
            desc = details['description'][:150].replace('\n', ' ')
            print(f"       Description: {desc}...")

# Test the correct endpoint
print("\n" + "=" * 60)
print("TESTING CORRECT ENDPOINT:")
print("=" * 60)

sample_payload = {
    "transaction_type": "MEDICAL_CLAIM",
    "claim_id": "TEST-001",
    "bene_id": "BENE-001",
    "provider_id": "1234567890",
    "at_physn_npi": "1234567890",
    "claim_type": "inpatient",
    "claim_start_date": "2024-01-01",
    "clm_pmt_amt": 1500.0,
    "clm_tot_chrg_amt": 2000.0,
    "line_count": 3,
    "diag_count": 2,
    "proc_count": 3,
    "state": "OH",
}

print(f"\nPOST /api/v1/predict_hybrid")
try:
    resp = httpx.post(
        "http://13.204.86.122:8000/api/v1/predict_hybrid",
        json=sample_payload,
        timeout=30.0
    )
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        result = resp.json()
        print(f"\n✅ SUCCESS! Response:")
        print(json.dumps(result, indent=2))
    else:
        print(f"Response: {resp.text}")
except Exception as e:
    print(f"❌ Error: {e}")
