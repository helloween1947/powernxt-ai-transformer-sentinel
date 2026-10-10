import { adaptWhatIf, validateWhatIfRequest } from './whatIfAdapter.js';

export class WhatIfApiError extends Error {
  constructor(status, message, code = 'what_if_error', reasons = []) {
    super(message);
    this.name = 'WhatIfApiError';
    this.status = status;
    this.code = code;
    this.reasons = reasons;
  }
}

export function createWhatIfClient({ baseUrl, fetchImpl = globalThis.fetch }) {
  const base = (baseUrl ?? '').trim().replace(/\/+$/, '');

  async function compare(assetId, params, signal) {
    if (!base) {
      throw new Error('Set VITE_API_BASE_URL to a reachable backend and restart Vite.');
    }
    const cleanAsset = String(assetId ?? '').trim();
    if (!cleanAsset) {
      throw new Error('Asset ID is required.');
    }

    const payload = params.schema_version === 'what-if-request-1.0.0'
      ? params
      : validateWhatIfRequest(params);

    const url = `${base}/api/v1/assets/${encodeURIComponent(cleanAsset)}/what-if`;

    let response;
    try {
      response = await fetchImpl(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: signal || AbortSignal.timeout(12000),
      });
    } catch (err) {
      if (err.name === 'AbortError') throw err;
      throw new WhatIfApiError(0, 'Cannot reach What-if backend service.', 'network_error');
    }

    let result;
    try {
      result = await response.json();
    } catch {
      throw new WhatIfApiError(response.status, 'Backend returned an unreadable response.', 'invalid_json');
    }

    if (!response.ok) {
      const detail = result.detail || {};
      const code = detail.code || 'what_if_error';
      const message = detail.message || `What-if request failed (${response.status}).`;
      const reasons = Array.isArray(detail.reasons) ? detail.reasons : [];
      throw new WhatIfApiError(response.status, message, code, reasons);
    }

    return {
      raw: result,
      adapted: adaptWhatIf(result),
    };
  }

  return { compare };
}
