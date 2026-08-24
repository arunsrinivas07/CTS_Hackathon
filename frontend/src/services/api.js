// ─── ClaimGuard AI – Centralised API Client ───────────────────────────────────
// All fetch calls go through /api which Vite proxies to http://15.207.248.42

const BASE = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : 'http://15.207.248.42/api/v1';

// ── Token helpers ────────────────────────────────────────────────────────────
function getToken() {
  return localStorage.getItem('cg_token') || sessionStorage.getItem('cg_token');
}

function saveToken(token, remember = true) {
  if (remember) {
    localStorage.setItem('cg_token', token);
  } else {
    sessionStorage.setItem('cg_token', token);
  }
}

function clearToken() {
  localStorage.removeItem('cg_token');
  sessionStorage.removeItem('cg_token');
}

// ── Base request ─────────────────────────────────────────────────────────────
async function request(path, options = {}) {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, { ...options, headers });

  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    if (typeof data.detail === 'string') {
      msg = data.detail;
    } else if (Array.isArray(data.detail)) {
      msg = data.detail.map(d => d.msg || JSON.stringify(d)).join(', ');
    } else if (data.message) {
      msg = data.message;
    }
    throw new Error(msg);
  }
  return data;
}

// ── Auth ─────────────────────────────────────────────────────────────────────
export const authAPI = {
  // POST /api/v1/auth/login/json  → { access_token }
  login: (email, password) =>
    request('/auth/login/json', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  // GET /api/v1/users/me → UserResponse (includes role string)
  getMe: () => request('/users/me'),
};

// ── Users ────────────────────────────────────────────────────────────────────
export const usersAPI = {
  getAll: () => request('/users/'),
  getById: (id) => request(`/users/${id}`),
  // POST /api/v1/users/ to register a new account
  create: (data) =>
    request('/users/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) =>
    request(`/users/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
};

// ── Claims ───────────────────────────────────────────────────────────────────
export const claimsAPI = {
  getAll: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/claims/${q ? '?' + q : ''}`);
  },
  getById: (id) => request(`/claims/${id}`),
  create: (data) =>
    request('/claims/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) =>
    request(`/claims/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id) =>
    request(`/claims/${id}`, { method: 'DELETE' }),
  getLineItems: (claimId) => request(`/claims/${claimId}/line-items`),
  addLineItem: (claimId, data) =>
    request(`/claims/${claimId}/line-items`, { method: 'POST', body: JSON.stringify(data) }),
  getStatusHistory: (claimId) => request(`/claims/${claimId}/status-history`),
  addStatus: (claimId, data) =>
    request(`/claims/${claimId}/status-history`, { method: 'POST', body: JSON.stringify(data) }),
  getPayments: (claimId) => request(`/claims/${claimId}/payments`),
  extractFromDocument: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const token = getToken();
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return fetch(`${BASE}/claims/extract_from_document`, {
      method: 'POST',
      headers,
      body: formData,
    }).then(async (res) => {
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      return data;
    });
  },
};

// ── Investigations ───────────────────────────────────────────────────────────
export const investigationsAPI = {
  getAll: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/investigations/${q ? '?' + q : ''}`);
  },
  getById: (id) => request(`/investigations/${id}`),
  create: (data) =>
    request('/investigations/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) =>
    request(`/investigations/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  getFindings: (id) => request(`/investigations/${id}/findings`),
  addFinding: (id, data) =>
    request(`/investigations/${id}/findings`, { method: 'POST', body: JSON.stringify(data) }),
  getEvidence: (id) => request(`/investigations/${id}/evidence`),
  addEvidence: (id, data) =>
    request(`/investigations/${id}/evidence`, { method: 'POST', body: JSON.stringify(data) }),
  getDecisions: (id) => request(`/investigations/${id}/decisions`),
  addDecision: (id, data) =>
    request(`/investigations/${id}/decisions`, { method: 'POST', body: JSON.stringify(data) }),
  // Agentic investigation endpoints (now unified under /api/v1)
  start: (data) => request('/agentic/investigations/start', { method: 'POST', body: JSON.stringify(data) }),
  run: (id) => request(`/agentic/investigations/${id}/run`, { method: 'POST' }),
  step: (id) => request(`/agentic/investigations/${id}/step`, { method: 'POST' }),
  getTrace: (id) => request(`/agentic/investigations/${id}/trace`),
  getAgenticState: (id) => request(`/agentic/investigations/${id}`),
};

// ── Evidence ─────────────────────────────────────────────────────────────────
export const evidenceAPI = {
  getAll: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/evidence/${q ? '?' + q : ''}`);
  },
  getById: (id) => request(`/evidence/${id}`),
  create: (data) => request('/evidence/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => request(`/evidence/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id) => request(`/evidence/${id}`, { method: 'DELETE' }),
};

// ── Findings ─────────────────────────────────────────────────────────────────
export const findingsAPI = {
  getAll: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/findings/${q ? '?' + q : ''}`);
  },
  getById: (id) => request(`/findings/${id}`),
  create: (data) => request('/findings/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => request(`/findings/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id) => request(`/findings/${id}`, { method: 'DELETE' }),
};

// ── Tasks ────────────────────────────────────────────────────────────────────
export const tasksAPI = {
  getAll: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/tasks/${q ? '?' + q : ''}`);
  },
  getById: (id) => request(`/tasks/${id}`),
  getMyTasks: (status = null) => {
    const q = status ? `?status=${status}` : '';
    return request(`/tasks/my-tasks${q}`);
  },
  create: (data) => request('/tasks/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => request(`/tasks/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  updateStatus: (id, status) => request(`/tasks/${id}/status?status=${status}`, { method: 'PATCH' }),
  delete: (id) => request(`/tasks/${id}`, { method: 'DELETE' }),
};

// ── Anomalies ────────────────────────────────────────────────────────────────
export const anomaliesAPI = {
  getAll: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/anomalies/${q ? '?' + q : ''}`);
  },
  getById: (id) => request(`/anomalies/${id}`),
  getByClaimId: (claimId) => request(`/anomalies/claims/${claimId}/anomalies`),
  create: (data) => request('/anomalies/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => request(`/anomalies/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id) => request(`/anomalies/${id}`, { method: 'DELETE' }),
};

// ── ML Outputs ──────────────────────────────────────────────────────────────
export const mlOutputsAPI = {
  getAll: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/ml-outputs/${q ? '?' + q : ''}`);
  },
  getById: (id) => request(`/ml-outputs/${id}`),
  create: (data) => request('/ml-outputs/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => request(`/ml-outputs/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id) => request(`/ml-outputs/${id}`, { method: 'DELETE' }),
};

// ── Documentation Requests ──────────────────────────────────────────────────
export const documentationRequestsAPI = {
  getAll: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/documentation-requests/${q ? '?' + q : ''}`);
  },
  getById: (id) => request(`/documentation-requests/${id}`),
  getByInvestigation: (invId) => request(`/documentation-requests/investigation/${invId}`),
  create: (data) => request('/documentation-requests/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => request(`/documentation-requests/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id) => request(`/documentation-requests/${id}`, { method: 'DELETE' }),
};

// ── Copilot ──────────────────────────────────────────────────────────────────
export const copilotAPI = {
  query: (data) => request('/agentic/copilot/query', { method: 'POST', body: JSON.stringify(data) }),
};

// ── Providers ────────────────────────────────────────────────────────────────
export const providersAPI = {
  getAll: () => request('/providers/'),
  getById: (id) => request(`/providers/${id}`),
  update: (id, data) =>
    request(`/providers/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
};

// ── Patients ─────────────────────────────────────────────────────────────────
export const patientsAPI = {
  getAll: () => request('/patients/'),
  getById: (id) => request(`/patients/${id}`),
};

// ── Risks ────────────────────────────────────────────────────────────────────
export const riskAPI = {
  getByClaim: (claimId) => request(`/risk/?claim_id=${claimId}`),
};

// ── Notifications ────────────────────────────────────────────────────────────
export const notificationsAPI = {
  getAll: () => request('/notifications/my'),           // GET /notifications/my
  markRead: (id) =>
    request(`/notifications/${id}/read`, { method: 'PATCH' }),  // PATCH /notifications/{id}/read
};

// ── Reports ──────────────────────────────────────────────────────────────────
export const reportsAPI = {
  getAll: () => request('/reports/'),
  getById: (id) => request(`/reports/${id}`),
};

// ── Decisions ────────────────────────────────────────────────────────────────
export const decisionsAPI = {
  getAll: () => request('/decisions/'),
};

// ── Roles ────────────────────────────────────────────────────────────────────
export const rolesAPI = {
  getAll: () => request('/roles/'),
};

// ── ML Risk Engine ───────────────────────────────────────────────────────────
export const mlAPI = {
  getHealth: () => request('/ml/health'),
  predictHybrid: (payload) =>
    request('/ml/predict_hybrid', { method: 'POST', body: JSON.stringify(payload) }),
  predict: (payload) =>
    request('/ml/predict', { method: 'POST', body: JSON.stringify(payload) }),
  scoreClaim: (claimId) =>
    request(`/ml/score_claim/${claimId}`, { method: 'POST' }),
};

// ── Token management (exported for AuthContext) ───────────────────────────────
export { getToken, saveToken, clearToken };
