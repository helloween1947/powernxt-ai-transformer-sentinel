import TrendChart from './TrendChart.jsx';

const series = [
  { key: 'measured', label: 'Measured oil', color: '#0e7490' },
  { key: 'predicted', label: 'Estimated top-oil', color: '#a16207', dashed: true },
];
const signed = value => value == null ? 'Unavailable' : `${value >= 0 ? '+' : ''}${value}`;

export default function ThermalComparison({ points, latestEnvelope, completedAnalytics }) {
  return <section aria-label="Stored thermal comparison">
    <h3>Latest telemetry and completed analytics</h3>
    {latestEnvelope ? <>
      <p>Latest telemetry reading: {latestEnvelope.latest_telemetry_reading_id ?? 'None'}; job: {latestEnvelope.latest_telemetry_status ?? 'None'}. Measurement time (UTC): {latestEnvelope.latest_telemetry_measurement_time ?? 'None'}.</p>
      <p>Latest completed analytics reading: {latestEnvelope.latest_completed_reading_id ?? 'None'}. Measurement time (UTC): {latestEnvelope.latest_completed_measurement_time ?? 'None'}.</p>
      {latestEnvelope.lagging && <p role="status">Processing lag or unavailable newest result: latest completed analytics is separate from latest telemetry.</p>}
      {latestEnvelope.result && <p>Completed model: {latestEnvelope.result.model_id} / {latestEnvelope.result.model_version}. Stored at (UTC): {latestEnvelope.result.created_at}. Configuration: {completedAnalytics?.configuration_version ?? latestEnvelope.result.payload?.metadata?.configuration_version ?? 'Unavailable'}.</p>}
    </> : <p>Latest completed analytics could not be retrieved; see the request error.</p>}
    <p>Thermal comparison covers this 20-reading history page, ordered by measurement time and joined by reading ID. Unavailable predictions remain gaps. Bootstrap initializes from observed oil and is not an independent prediction.</p>
    <TrendChart title="Stored measured and estimated oil temperature" points={points} series={series} />
    <TrendChart title="Stored oil residual — observed minus predicted" points={points} step={0.1} decimals={2} series={[{key:'residual',label:'Observed minus predicted residual',color:'#7c3aed'}]} />
    <div className="table-wrap"><table aria-label="Thermal history values"><thead><tr><th>Reading / config</th><th>Measurement time (UTC)</th><th>Stored at (UTC)</th><th>Measured oil (°C)</th><th>Estimated top-oil (°C)</th><th>Residual: observed − predicted (°C)</th><th>Elapsed (s)</th><th>Job / availability reasons</th></tr></thead><tbody>
      {points.map(point => <tr key={point.readingId}><td>{point.readingId} / {point.configurationVersion}</td><td>{point.timestamp}</td><td>{point.processedAt ?? 'Unavailable'}</td><td>{point.measured ?? 'Unavailable'}</td><td>{point.predicted ?? 'Unavailable'}</td><td>{signed(point.residual)}</td><td>{point.elapsed ?? 'Unavailable'}</td><td>{point.status}; {point.reasons.join(', ')}</td></tr>)}
    </tbody></table></div>
    <p>Simulator/predictor equations and time constants differ. Nonzero or negative residuals can reflect model mismatch; they are not confirmed faults or automatic maintenance recommendations.</p>
  </section>;
}
