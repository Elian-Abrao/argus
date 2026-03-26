const API_BASE = '/dashboard-api';

let _authToken = null;
let _onUnauthorized = null;

export function setAuthToken(token) {
  _authToken = token;
}

export function registerOnUnauthorized(callback) {
  _onUnauthorized = callback;
}

function _authHeaders() {
  return _authToken ? { Authorization: `Bearer ${_authToken}` } : {};
}

export function getAuthHeaders() {
  return _authHeaders();
}

async function _tryRefresh() {
  try {
    const resp = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      credentials: 'same-origin',
    });
    if (!resp.ok) return false;
    const data = await resp.json();
    if (data?.access_token) {
      _authToken = data.access_token;
      return true;
    }
    return false;
  } catch {
    return false;
  }
}

class ApiError extends Error {
  constructor(payload) {
    super(payload.message);
    this.name = 'ApiError';
    this.status = payload.status;
    this.title = payload.title;
    this.retriable = payload.retriable;
  }
}

// Formata uma Date como "YYYY-MM-DDTHH:mm:ss" sem conversão de timezone.
// O backend armazena datetimes como naive local, então não devemos enviar UTC.
function toLocalIsoString(date) {
  const pad = (n) => String(n).padStart(2, '0');
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
  );
}

function getLastBusinessDayBoundsIso() {
  const now = new Date();
  const day = now.getDay(); // 0=Dom, 1=Seg, ..., 6=Sab
  // Recua para o dia útil anterior: seg recua 3 (sex), dom recua 2 (sex), demais recuam 1
  const daysBack = day === 1 ? 3 : day === 0 ? 2 : 1;

  const start = new Date(now);
  start.setDate(start.getDate() - daysBack);
  start.setHours(0, 0, 0, 0);

  const end = new Date(now);
  end.setHours(23, 59, 59, 0);

  return {
    startedAfter: toLocalIsoString(start),
    startedBefore: toLocalIsoString(end),
  };
}

function toQueryString(params) {
  const search = new URLSearchParams();
  if (!params) return search.toString();

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;
    if (Array.isArray(value)) {
      value.forEach((item) => {
        if (item !== undefined && item !== null && item !== '') {
          search.append(key, String(item));
        }
      });
      return;
    }
    search.append(key, String(value));
  });

  return search.toString();
}

function toMappedError(status, detail) {
  const generic = {
    status,
    retriable: status >= 500,
    title: 'Falha na requisicao',
    message: detail || 'Nao foi possivel concluir a operacao.',
  };

  if (status === 401) {
    return {
      ...generic,
      title: 'Sessao expirada',
      message: 'Autenticacao necessaria para continuar.',
      retriable: false,
    };
  }
  if (status === 403) {
    return {
      ...generic,
      title: 'Acesso negado',
      message: 'Voce nao possui permissao para esse recurso.',
      retriable: false,
    };
  }
  if (status === 404) {
    return {
      ...generic,
      title: 'Nao encontrado',
      message: detail || 'O recurso solicitado nao foi encontrado.',
      retriable: false,
    };
  }
  if (status === 409) {
    return {
      ...generic,
      title: 'Conflito de estado',
      message: detail || 'O recurso foi alterado e gerou conflito.',
      retriable: false,
    };
  }
  if (status === 422) {
    return {
      ...generic,
      title: 'Erro de validacao',
      message: detail || 'Os dados enviados nao sao validos.',
      retriable: false,
    };
  }
  if (status === 500) {
    return {
      ...generic,
      title: 'Erro interno',
      message: detail || 'O servidor encontrou um erro interno.',
      retriable: true,
    };
  }
  if (status === 502) {
    return {
      ...generic,
      title: 'Falha de conectividade',
      message: detail || 'Nao foi possivel conectar ao backend remoto.',
      retriable: true,
    };
  }
  return generic;
}

async function _doRequest(url, fetchOptions) {
  const response = await fetch(url, fetchOptions);
  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json')
    ? await response.json()
    : await response.text();
  return { response, payload };
}

async function request(path, options = {}) {
  const query = toQueryString(options.params);
  const url = `${API_BASE}${path}${query ? `?${query}` : ''}`;
  const fetchOptions = {
    method: options.method || 'GET',
    headers: { Accept: 'application/json', ..._authHeaders() },
    credentials: 'same-origin',
  };

  try {
    let { response, payload } = await _doRequest(url, fetchOptions);

    // On 401 try to refresh once and retry
    if (response.status === 401) {
      const refreshed = await _tryRefresh();
      if (refreshed) {
        fetchOptions.headers = { Accept: 'application/json', ..._authHeaders() };
        ({ response, payload } = await _doRequest(url, fetchOptions));
      }
    }

    if (!response.ok) {
      if (response.status === 401 && _onUnauthorized) _onUnauthorized();
      const detail =
        typeof payload === 'string'
          ? payload
          : payload?.detail || payload?.message || 'Erro na requisicao.';
      throw new ApiError(toMappedError(response.status, detail));
    }

    return payload;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(toMappedError(502, 'Falha de rede ao tentar acessar os dados do dashboard.'));
  }
}

export function getHosts(params = {}) {
  return request('/insights/hosts', { params });
}

export function getHostDetail(hostId) {
  return request(`/insights/hosts/${hostId}`);
}

export function getHostInstances(hostId) {
  return request(`/insights/hosts/${hostId}/instances`);
}

export function updateHost(hostId, data) {
  return requestWithBody(`/insights/hosts/${hostId}`, { method: 'PATCH', body: data });
}

export function getAutomations(params = {}) {
  return request('/insights/automations', { params });
}

export function getAutomationDetail(automationId) {
  return request(`/insights/automations/${automationId}`);
}

export function getAutomationInstances(automationId, params = {}) {
  return request(`/insights/automations/${automationId}/instances`, { params });
}

export function getAutomationRuns(automationId, params = {}) {
  return request(`/insights/automations/${automationId}/runs`, { params });
}

export function getInstanceRuns(instanceId, params = {}) {
  return request(`/insights/instances/${instanceId}/runs`, { params });
}

export function getRuns(params = {}) {
  return request('/insights/runs', { params });
}

export function getRunsOverview(params = {}) {
  return request('/insights/runs/overview', { params });
}

export function getClients(params = {}) {
  return request('/insights/clients', { params });
}

export function getClientDetail(clientId) {
  return request(`/insights/clients/${clientId}`);
}

export function getClientAutomations(clientId) {
  return request(`/insights/clients/${clientId}/automations`);
}

export function getRunDetail(runId) {
  return request(`/insights/runs/${runId}`);
}

export function getRunLogs(runId, params = {}) {
  const queryParams = { ...params };
  // The backend expects "order", but the component might send "sort"
  if (queryParams.sort) {
    queryParams.order = queryParams.sort;
    delete queryParams.sort;
  }

  return request(`/insights/runs/${runId}/logs`, {
    params: queryParams,
  });
}

export function getRunLogsMetrics(runId) {
  return request(`/insights/runs/${runId}/logs/metrics`);
}

export function getRunEmails(runId, params = {}) {
  return request(`/insights/runs/${runId}/emails`, { params });
}

export function getEmailAttachmentUrl(emailId, attachmentId, mode = 'download') {
  const target = mode === 'preview' ? 'preview' : 'download';
  return `${API_BASE}/insights/emails/${emailId}/attachments/${attachmentId}/${target}`;
}

export async function getDashboardOverviewData() {
  const { startedAfter, startedBefore } = getLastBusinessDayBoundsIso();

  const [hosts, automations, clients, timeline, calendar, commands] = await Promise.all([
    getHosts({ limit: 5 }),
    getAutomations({ limit: 5 }),
    getClients({ limit: 5 }),
    request('/insights/runs/timeline', {
      params: {
        started_after: startedAfter,
        started_before: startedBefore,
        limit: 200,
      },
    }),
    request('/schedules/calendar', {
      params: { start: startedAfter, end: startedBefore },
    }),
    request('/commands', {
      params: {
        created_after: startedAfter,
        created_before: startedBefore,
        limit: 500,
      },
    }),
  ]);

  return {
    hosts,
    automations,
    clients,
    timeline,
    calendar,
    commands,
  };
}

export function getHealth() {
  return request('/health');
}

// ---------------------------------------------------------------------------
// Remote control: Schedules
// ---------------------------------------------------------------------------

async function requestWithBody(path, { method = 'POST', body, params } = {}) {
  const query = toQueryString(params);
  const url = `${API_BASE}${path}${query ? `?${query}` : ''}`;
  const fetchOptions = {
    method,
    headers: { 'Content-Type': 'application/json', Accept: 'application/json', ..._authHeaders() },
    credentials: 'same-origin',
    body: body ? JSON.stringify(body) : undefined,
  };

  try {
    let response = await fetch(url, fetchOptions);

    // On 401 try to refresh once and retry
    if (response.status === 401) {
      const refreshed = await _tryRefresh();
      if (refreshed) {
        fetchOptions.headers = { 'Content-Type': 'application/json', Accept: 'application/json', ..._authHeaders() };
        response = await fetch(url, fetchOptions);
      }
    }

    const contentType = response.headers.get('content-type') || '';
    if (response.status === 204) return null;
    const payload = contentType.includes('application/json')
      ? await response.json()
      : await response.text();

    if (!response.ok) {
      if (response.status === 401 && _onUnauthorized) _onUnauthorized();
      const detail =
        typeof payload === 'string'
          ? payload
          : payload?.detail || payload?.message || 'Erro na requisicao.';
      throw new ApiError(toMappedError(response.status, detail));
    }

    return payload;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(toMappedError(502, 'Falha de rede ao tentar acessar os dados do dashboard.'));
  }
}

export function getSchedules(params = {}) {
  return request('/schedules', { params });
}

export function getCalendar(params = {}) {
  return request('/schedules/calendar', { params });
}

export function createSchedule(data) {
  return requestWithBody('/schedules', { body: data });
}

export function updateSchedule(id, data) {
  return requestWithBody(`/schedules/${id}`, { method: 'PATCH', body: data });
}

export function deleteSchedule(id) {
  return requestWithBody(`/schedules/${id}`, { method: 'DELETE' });
}

// ---------------------------------------------------------------------------
// Remote control: Commands
// ---------------------------------------------------------------------------

export function runNow(data) {
  return requestWithBody('/commands/run-now', { body: data });
}

export function updateInstanceArgs(instanceId, data) {
  return requestWithBody(`/instances/${instanceId}/args`, { method: 'PATCH', body: data });
}

// ---------------------------------------------------------------------------
// Agent status
// ---------------------------------------------------------------------------

export function getAgentStatus() {
  return request('/agent/status');
}

// ---------------------------------------------------------------------------
// Auth / User management
// ---------------------------------------------------------------------------

export function getMe() {
  return request('/auth/me');
}

export function changePassword(data) {
  return requestWithBody('/auth/change-password', { method: 'POST', body: data });
}

export function adminListUsers() {
  return request('/admin/users');
}

export function adminCreateUser(data) {
  return requestWithBody('/admin/users', { body: data });
}

export function adminUpdateUser(userId, data) {
  return requestWithBody(`/admin/users/${userId}`, { method: 'PATCH', body: data });
}

export function adminSetUserAccess(userId, data) {
  return requestWithBody(`/admin/users/${userId}/access`, { method: 'PUT', body: data });
}

export function adminResetPassword(userId) {
  return requestWithBody(`/admin/users/${userId}/reset-password`, { body: {} });
}

export function adminRevokeSessions(userId) {
  return requestWithBody(`/admin/users/${userId}/sessions`, { method: 'DELETE', body: {} });
}

export { ApiError };
