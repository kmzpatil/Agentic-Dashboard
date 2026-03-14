function createAgentError(status, message, details) {
  const error = new Error(message);
  error.status = status;
  error.details = details;
  return error;
}

function buildAgentUrl(baseUrl, pathname, query = {}) {
  const normalizedBase = baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`;
  const url = new URL(pathname.replace(/^\//, ''), normalizedBase);

  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.set(key, value);
    }
  });

  return url;
}

async function parseAgentResponse(response) {
  const text = await response.text();

  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text);
  } catch (_error) {
    return { raw: text };
  }
}

async function requestAgentJson(agentConfig, pathname, options = {}) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), agentConfig.timeoutMs);
  const url = buildAgentUrl(agentConfig.baseUrl, pathname, options.query);

  try {
    const response = await fetch(url, {
      method: options.method || 'GET',
      headers: {
        Accept: 'application/json',
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...(options.headers || {}),
      },
      body: options.body ? JSON.stringify(options.body) : undefined,
      signal: controller.signal,
    });

    const payload = await parseAgentResponse(response);

    if (!response.ok) {
      const message = payload?.detail || payload?.error || response.statusText || 'Agent request failed';
      throw createAgentError(response.status, message, payload);
    }

    return payload;
  } catch (error) {
    if (error.name === 'AbortError') {
      throw createAgentError(504, 'Timed out while waiting for the agent service.', null);
    }

    if (typeof error.status === 'number') {
      throw error;
    }

    throw createAgentError(503, `Agent service unavailable: ${error.message}`, null);
  } finally {
    clearTimeout(timeoutId);
  }
}

async function getAgentHealth(agentConfig) {
  try {
    const payload = await requestAgentJson(agentConfig, '/healthz');
    return {
      ok: Boolean(payload?.ok),
      ...payload,
    };
  } catch (error) {
    return {
      ok: false,
      error: error.message,
      status: error.status || 503,
      service: 'agent',
    };
  }
}

module.exports = {
  getAgentHealth,
  requestAgentJson,
};
