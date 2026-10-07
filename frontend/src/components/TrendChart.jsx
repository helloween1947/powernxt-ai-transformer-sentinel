export default function TrendChart({ title, points, series }) {
  const values = points.flatMap(point => series.map(line => point[line.key])).filter(Number.isFinite);
  if (!points.length || !values.length) return <p>No chart data available.</p>;
  const minimum = Math.floor(Math.min(...values) / 10) * 10 - 10;
  const maximum = Math.ceil(Math.max(...values) / 10) * 10 + 10;
  const x = index => 55 + index * 630 / Math.max(points.length - 1, 1);
  const y = value => 215 - (value - minimum) * 180 / (maximum - minimum);
  return <div className="chart">
    <h3>{title}</h3>
    <svg viewBox="0 0 740 270" role="img" aria-label={`${title}; temperature in degrees Celsius. Exact readings follow the chart.`}>
      {[0, 1, 2, 3, 4].map(index => {
        const value = minimum + index * (maximum - minimum) / 4;
        return <g key={index}><line x1="55" x2="685" y1={y(value)} y2={y(value)} className="grid" /><text x="5" y={y(value) + 4}>{Math.round(value)} C</text></g>;
      })}
      {series.map(line => {
        let segment = '';
        const path = points.map((point, index) => {
          if (!Number.isFinite(point[line.key])) { segment = ''; return ''; }
          const instruction = `${segment ? 'L' : 'M'}${x(index)},${y(point[line.key])}`;
          segment = instruction;
          return instruction;
        }).join(' ');
        return <path key={line.key} d={path} fill="none" stroke={line.color} strokeWidth="3" strokeDasharray={line.dashed ? '7 5' : undefined} />;
      })}
      <text x="55" y="250">{new Date(points[0].timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</text>
      <text x="630" y="250">{new Date(points.at(-1).timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</text>
    </svg>
    <div className="legend">{series.map(line => <span key={line.key}><i style={{ background: line.color }} />{line.label}</span>)}</div>
    <details><summary>View exact chart values</summary><div className="table-wrap"><table><thead><tr><th>Time</th>{series.map(line => <th key={line.key}>{line.label} (C)</th>)}</tr></thead><tbody>{points.map(point => <tr key={point.timestamp}><td>{new Date(point.timestamp).toLocaleTimeString()}</td>{series.map(line => <td key={line.key}>{point[line.key] ?? 'Unavailable'}</td>)}</tr>)}</tbody></table></div></details>
  </div>;
}
