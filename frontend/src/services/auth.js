const TOKEN_STORAGE_KEY = 'sentinel_operator_token_v1';

export function getStoredToken() {
  try {
    return sessionStorage.getItem(TOKEN_STORAGE_KEY) || '';
  } catch {
    return '';
  }
}

export function saveToken(token) {
  try {
    if (token) {
      sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
    } else {
      sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  } catch {
    // Ignore storage restrictions
  }
}

export function clearStoredToken() {
  saveToken('');
}

export class AuthError extends Error {
  constructor(status, message, code = 'auth_error') {
    super(message);
    this.name = 'AuthError';
    this.status = status;
    this.code = code;
  }
}

export async function fetchOperatorMe(baseUrl, token) {
  const cleanBase = (baseUrl ?? '').trim().replace(/\/+$/, '');
  if (!cleanBase) {
    throw new AuthError(0, 'API base URL is not configured.', 'invalid_config');
  }
  const cleanToken = (token ?? '').trim();
  if (!cleanToken) {
    throw new AuthError(401, 'Bearer token is required.', 'unauthenticated');
  }

  let response;
  try {
    response = await fetch(`${cleanBase}/api/v1/operators/me`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${cleanToken}`,
      },
      signal: AbortSignal.timeout(8000),
    });
  } catch {
    throw new AuthError(0, 'Cannot reach operator service. Check backend connection.', 'network_error');
  }

  let data;
  try {
    data = await response.json();
  } catch {
    throw new AuthError(response.status, 'Backend returned an unreadable response.', 'invalid_response');
  }

  if (!response.ok) {
    const message = data.message || data.detail || `Authentication failed (${response.status}).`;
    const code = data.code || 'unauthenticated';
    throw new AuthError(response.status, message, code);
  }

  if (data.schema_version !== 'incident-operator-1.0.0') {
    throw new AuthError(response.status, 'Unsupported operator contract version.', 'contract_mismatch');
  }

  return {
    actorRef: data.actor_ref,
    name: data.name,
    role: data.role,
    expiresAt: data.expires_at,
    token: cleanToken,
  };
}
