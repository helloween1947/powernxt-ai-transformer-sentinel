export default function ReadingCard({ label, value, unit, source = 'simulated' }) {
  return <article className="metric">
    <span>{label}</span>
    <strong>{value === null || value === undefined ? 'Unavailable' : value}<small>{value === null || value === undefined ? '' : unit}</small></strong>
    <span className="source">{source}</span>
  </article>;
}
