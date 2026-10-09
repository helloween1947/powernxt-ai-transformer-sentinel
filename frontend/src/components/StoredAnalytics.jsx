export default function StoredAnalytics({ analytics, title = 'Analytics for the latest stored reading' }) {
  const result = analytics.result;
  const payload = result?.payload;
  return <section aria-label="Stored analytics">
    <h3>{title}</h3>
    <p>Reading {analytics.reading_id} / configuration {analytics.configuration_version}. Job: {analytics.status}; attempts: {analytics.attempts}.</p>
    <p>Measurement time (UTC): {analytics.measurement_time}. Source: {analytics.source} / run: {analytics.run_id ?? 'None'}.</p>
    {analytics.source !== 'device' && <p>Synthetic or replay evidence; these timestamps do not establish fresh device measurements.</p>}
    {analytics.error_code && <p role="alert">Processing error: {analytics.error_code}</p>}
    {!result && <p>No stored analytical result for this reading. Reload backend readings to check processing status; no sample result is substituted.</p>}
    {result && <>
      <p>Stored at (UTC): {result.created_at}. Model: {result.model_id} / {result.model_version}. Result status: {result.status}; outcome: {payload.execution_status?.outcome ?? 'Unavailable'}.</p>
      <p>Model-bound measured oil: {payload.thermal_assessment?.measured_top_oil_temperature_c ?? 'Unavailable'} °C.</p>
      <p>Parameter version: {result.parameter_version}</p>
      <div className="table-wrap"><table><thead><tr><th>Metric</th><th>Value</th><th>Unit</th><th>Availability / reasons</th></tr></thead><tbody>
        {analytics.metrics.map(metric => <tr key={metric.path}><td>{metric.label}</td><td>{metric.value ?? 'Unavailable'}</td><td>{metric.unit}</td><td>{metric.status} {metric.reasons.join(', ')}</td></tr>)}
      </tbody></table></div>
      <p>Elapsed measurement interval: {payload.thermal_assessment?.elapsed_s ?? 'Unavailable'} s. Prediction uses previous-sample hold; this simplified model is uncalibrated.</p>
      <details><summary>Parameter provenance</summary><ul>{Object.entries(payload.metadata?.parameter_provenance ?? {}).map(([key, value]) => <li key={key}>{key}: {value}</li>)}</ul></details>
    </>}
    <p>Health/risk score, numerical confidence, winding forecast, fault diagnosis, RUL and computed what-if results are unavailable under the current contract. Temperature residuals are not fault diagnoses or maintenance recommendations.</p>
  </section>;
}
