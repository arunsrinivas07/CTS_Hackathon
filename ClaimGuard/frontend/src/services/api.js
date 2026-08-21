// ─── ClaimGuard AI – Centralised API Client ───────────────────────────────────
// All fetch calls go through /api which Vite proxies to http://127.0.0.1:8000

const BASE = '/api/v1';

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

// ── Anomalies ────────────────────────────────────────────────────────────────
export const anomaliesAPI = {
  getAll: () => request('/anomalies/'),
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

// ── Token management (exported for AuthContext) ───────────────────────────────
export { getToken, saveToken, clearToken };
