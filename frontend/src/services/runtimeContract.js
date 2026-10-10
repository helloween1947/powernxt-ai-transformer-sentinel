// Discover only implemented route families from the connected FastAPI runtime.
// OpenAPI is already exposed by this checkout; proposed routes are never probed.
const methods = (paths, path, verbs) => verbs.every(verb => paths?.[path]?.[verb] && typeof paths[path][verb] === 'object');
export function inspectRuntimeContract(spec) {
  if (!/^3\./.test(spec?.openapi ?? '') || !spec.paths || typeof spec.paths !== 'object') throw new Error('Runtime API description is unsupported.');
  return {
    analytics: methods(spec.paths, '/api/v1/telemetry/{reading_id}/analytics', ['get']) && methods(spec.paths, '/api/v1/assets/{asset_id}/analytics/latest', ['get']),
    sampleMaintenance: methods(spec.paths, '/api/v1/maintenance/tasks', ['get', 'post']) && methods(spec.paths, '/api/v1/maintenance/tasks/{task_id}', ['get', 'patch']) && methods(spec.paths, '/api/v1/maintenance/tasks/{task_id}/history', ['get']),
    dataInputs: methods(spec.paths, '/api/v1/simulator/runs', ['post']) && methods(spec.paths, '/api/v1/assets/{asset_id}/datasets', ['post']) && methods(spec.paths, '/api/v1/assets/{asset_id}/datasets/preview', ['post']),
    version: spec.info?.version ?? 'Unspecified',
  };
}
export async function discoverRuntimeContract(baseUrl, signal, fetcher = globalThis.fetch) {
  const response = await fetcher(`${baseUrl.replace(/\/+$/, '')}/openapi.json`, { signal: AbortSignal.any([signal, AbortSignal.timeout(10000)]) });
  if (!response.ok) throw new Error(`Runtime contract unavailable (${response.status}).`);
  return inspectRuntimeContract(await response.json());
}
