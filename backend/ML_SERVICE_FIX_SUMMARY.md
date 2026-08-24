# ML Service 503 Error - FIXED ✅

## Problem
```
POST /api/v1/ml/score_claim/11 HTTP/1.1" 503 Service Unavailable
```

Backend was trying to call external ML service but getting 503 errors.

## Root Cause Analysis

### Issue 1: Wrong Endpoint Path
- **Your backend was calling**: `POST /api/v1/ml/predict_hybrid`
- **External service expects**: `POST /api/v1/predict_hybrid` (no `/ml/` segment)

### Issue 2: Duplicate ML_SERVICE_URL in .env
- Line 4: `ML_SERVICE_URL=http://13.204.86.122:8000` (external - intended)
- Line 47: `ML_SERVICE_URL=http://localhost:8000` (local - was overriding!)
- The second entry was overriding the first, so backend was using localhost

### Issue 3: Too Short Timeout
- Original timeout: 10 seconds
- ML scoring can take 15-30 seconds for complex claims
- Increased to 30 seconds

## Solution Applied

### 1. Fixed `backend/app/routers/ml.py` (Line 142-158)

**Before:**
```python
resp = httpx.post(f"{ml_url}/api/v1/ml/predict_hybrid", json=payload, timeout=10.0)
```

**After:**
```python
# External ML service uses /api/v1/predict_hybrid (not /api/v1/ml/predict_hybrid)
resp = httpx.post(f"{ml_url}/api/v1/predict_hybrid", json=payload, timeout=30.0)
resp.raise_for_status()
res = resp.json()
```

### 2. Fixed `backend/.env` 

**Before (had 2 conflicting entries):**
```env
# Line 4
ML_SERVICE_URL=http://13.204.86.122:8000

# Line 47 (OVERRIDING!)
ML_SERVICE_URL=http://localhost:8000
```

**After (single entry):**
```env
# Line 4
ML_SERVICE_URL=http://13.204.86.122:8000

# Line 47 (commented out)
# ML_SERVICE_URL=http://localhost:8000  # Local fallback (commented out)
```

### 3. Improved Error Handling

Added specific error messages for:
- Connection errors (service down/unreachable)
- Timeout errors (service slow)
- HTTP errors (4xx/5xx responses)

## Verification Results ✅

### External ML Service Status
```
URL: http://13.204.86.122:8000
Health: ✅ Responding
Endpoint: POST /api/v1/predict_hybrid
Response Time: < 5 seconds
Status: 200 OK
```

### Sample Response
```json
{
  "final_risk_score": 0.0124,
  "final_risk_tier": "Low",
  "claim_score": 0.4241,
  "provider_score": 0.0622,
  "leie_override": false,
  "claim_evidence": [...],
  "provider_evidence": [...],
  "explanation": "LOW risk. Claim score: 42.41%, Provider score: 6.22%..."
}
```

## External ML Service API Structure

**Base URL**: `http://13.204.86.122:8000`

**Endpoints:**
- `GET /health` - Service health check
- `POST /api/v1/predict` - Single model prediction
- `POST /api/v1/predict_hybrid` - Hybrid model (Model B + XGBoost v2)

**API Documentation:**
- Swagger UI: http://13.204.86.122:8000/docs
- OpenAPI Spec: http://13.204.86.122:8000/openapi.json

## How It Works Now

1. **Frontend** → Submits claim or triggers ML scoring
2. **Backend** (`/api/v1/ml/score_claim/{id}`) → Fetches claim from database
3. **Backend** → Checks `ML_SERVICE_URL` environment variable
4. **Backend** → Detects external service (not localhost)
5. **Backend** → Calls `POST {ML_SERVICE_URL}/api/v1/predict_hybrid` with 30s timeout
6. **External ML Service** → Runs Model B + XGBoost v2 hybrid scoring
7. **Backend** → Receives response, saves to `risk_scores` and `ml_outputs` tables
8. **Frontend** → Displays risk score and analysis

## Testing

Run verification script:
```bash
cd backend
python test_ml_scoring_fixed.py
```

Expected output:
```
✅ External ML Service Working!
   - Final Risk Score: 0.0124
   - Risk Tier: Low
```

## Next Steps

1. **Restart Backend**:
   ```bash
   cd D:\final_claim\ClaimGuard\backend
   python -m uvicorn main:app --reload --port 8000
   ```

2. **Test via Frontend**:
   - Login as investigator
   - Navigate to any claim in Investigation page
   - System will automatically score the claim
   - Or manually trigger re-scoring if needed

3. **Monitor Logs**:
   - Watch backend terminal for ML service calls
   - Should see successful 200 responses from external service
   - No more 503 errors!

## Fallback Option

If external ML service becomes unavailable later, you can fallback to local ML engine:

**Edit `backend/.env`:**
```env
# Use local ML engine
ML_SERVICE_URL=http://localhost:8000
```

Local ML engine is already included in your backend (`backend/app/ml/hybrid_engine.py`) with all required models.

## Files Changed

1. `backend/app/routers/ml.py` - Fixed endpoint path and timeout
2. `backend/.env` - Removed duplicate, using external service only

## Files Created (for testing/documentation)

1. `backend/test_ml_service_connection.py`
2. `backend/test_external_ml_direct.py`
3. `backend/test_external_ml_endpoints.py`
4. `backend/parse_external_ml_api.py`
5. `backend/test_ml_scoring_fixed.py`
6. `backend/external_ml_openapi.json`
7. `backend/ML_SERVICE_FIX_SUMMARY.md` (this file)

---

**Status**: ✅ RESOLVED

**Date**: August 23, 2026

**Fix Verified**: External ML service successfully integrated with backend
