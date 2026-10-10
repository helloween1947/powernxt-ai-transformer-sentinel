export const datasetChannels = [
  ['timestamp', 'Measurement time'],
  ['voltage_r_v', 'R-phase voltage (V)'], ['voltage_y_v', 'Y-phase voltage (V)'], ['voltage_b_v', 'B-phase voltage (V)'],
  ['current_r_a', 'R-phase current (A)'], ['current_y_a', 'Y-phase current (A)'], ['current_b_a', 'B-phase current (A)'],
  ['oil_temperature_c', 'Oil temperature (°C)'], ['ambient_temperature_c', 'Ambient temperature (°C)'], ['oil_level_pct', 'Oil level (%)'],
];
export function createDataInputsClient(baseUrl, signal) {
  async function request(path, method = 'GET', body) {
    const multipart = body instanceof FormData;
    const response = await fetch(`${baseUrl.replace(/\/+$/, '')}${path}`, {
      method, signal: AbortSignal.any([signal, AbortSignal.timeout(60000)]),
      headers: body && !multipart ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? multipart ? body : JSON.stringify(body) : undefined,
    });
    const result = await response.json();
    if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : Array.isArray(result.detail) ? result.detail.map(item => item.msg).join('; ') : `Request failed (${response.status}).`);
    return result;
  }
  const assetPath = id => `/api/v1/assets/${encodeURIComponent(id)}`;
  return {
    assets: body => request('/api/v1/assets', 'POST', body),
    configure: (id, body) => request(`${assetPath(id)}/configuration`, 'PUT', body),
    runs: id => request(`/api/v1/runs?asset_id=${encodeURIComponent(id)}`),
    start: body => request('/api/v1/simulator/runs', 'POST', body),
    update: (id, body) => request(`/api/v1/simulator/runs/${encodeURIComponent(id)}`, 'PATCH', body),
    preview: (id, form) => request(`${assetPath(id)}/datasets/preview`, 'POST', form),
    report: (id, runId) => request(`${assetPath(id)}/faults?source=file_replay&run_id=${encodeURIComponent(runId)}&summary=true`),
    upload: (id, form) => request(`${assetPath(id)}/datasets`, 'POST', form),
  };
}
