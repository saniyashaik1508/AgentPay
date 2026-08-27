/**
 * Thin client for the AgentPay FastAPI backend. Every function takes the
 * base URL explicitly (from useSettings) rather than relying on a build-time
 * env var, since the person may point this at any running backend.
 */

class ApiError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

async function request(baseUrl, path, options = {}) {
  const url = `${baseUrl.replace(/\/+$/, '')}${path}`;
  let res;
  try {
    res = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    });
  } catch (err) {
    throw new ApiError(
      `Couldn't reach the backend at ${baseUrl}. Is it running (uvicorn app.main:app --reload --port 8000) and is the URL correct?`,
      0,
      null
    );
  }

  let body = null;
  const text = await res.text();
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }

  if (!res.ok) {
    const detail = body && body.detail ? body.detail : res.statusText;
    throw new ApiError(detail || `Request failed (${res.status})`, res.status, body);
  }

  return body;
}

export const api = {
  health: (base) => request(base, '/health'),

  listAgents: (base, ownerId) =>
    request(base, `/api/agents${ownerId ? `?owner_id=${encodeURIComponent(ownerId)}` : ''}`),

  registerAgent: (base, payload) =>
    request(base, '/api/agents/register', { method: 'POST', body: JSON.stringify(payload) }),

  revokeAgent: (base, agentId) =>
    request(base, `/api/agents/${encodeURIComponent(agentId)}/revoke`, { method: 'POST' }),

  evaluateTransaction: (base, payload) =>
    request(base, '/api/transactions/evaluate', { method: 'POST', body: JSON.stringify(payload) }),

  runAgent: (base, payload) =>
    request(base, '/api/agents/run', { method: 'POST', body: JSON.stringify(payload) }),

  approveTransaction: (base, transactionId) =>
    request(base, '/api/transactions/approve', {
      method: 'POST',
      body: JSON.stringify({ transaction_id: transactionId }),
    }),

  rejectTransaction: (base, transactionId) =>
    request(base, `/api/transactions/${encodeURIComponent(transactionId)}/reject`, { method: 'POST' }),

  listTransactions: (base, { agentId, status } = {}) => {
    const params = new URLSearchParams();
    if (agentId) params.set('agent_id', agentId);
    if (status) params.set('status', status);
    const qs = params.toString();
    return request(base, `/api/transactions${qs ? `?${qs}` : ''}`);
  },

  transactionTrace: (base, transactionId) =>
    request(base, `/api/transactions/${encodeURIComponent(transactionId)}/trace`),

  riskEvents: (base, agentId) =>
    request(base, `/api/risk/events${agentId ? `?agent_id=${encodeURIComponent(agentId)}` : ''}`),

  auditLog: (base, { agentId, transactionId } = {}) => {
    const params = new URLSearchParams();
    if (agentId) params.set('agent_id', agentId);
    if (transactionId) params.set('transaction_id', transactionId);
    const qs = params.toString();
    return request(base, `/api/audit${qs ? `?${qs}` : ''}`);
  },

  listMerchants: (base) => request(base, '/api/merchant/list'),

  merchantAnalytics: (base, merchantId) =>
    request(base, `/api/merchant/analytics?merchant_id=${encodeURIComponent(merchantId)}`),

  merchantRecommendations: (base, merchantId) =>
    request(base, `/api/merchant/recommendations?merchant_id=${encodeURIComponent(merchantId)}`),
};

export { ApiError };
