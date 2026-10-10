import { useState } from 'react';

export default function OperatorAuthBar({ operator, onLogin, onLogout, busy = false, error = '', notice = '' }) {
  const [tokenInput, setTokenInput] = useState('');

  function handleSubmit(e) {
    e.preventDefault();
    if (!tokenInput.trim()) return;
    onLogin(tokenInput.trim());
  }

  return (
    <div className="panel" style={{ background: '#f8fafc', border: '1px solid #cbd5e1', marginBottom: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <span className="eyebrow" style={{ textTransform: 'uppercase', letterSpacing: '1px' }}>Operator Authentication</span>
          <h3 style={{ margin: '4px 0 0' }}>
            {operator ? `Active Session: ${operator.name}` : 'No Active Operator Session'}
          </h3>
        </div>

        {operator ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '15px', flexWrap: 'wrap' }}>
            <span
              className="badge"
              style={{
                background: operator.role === 'admin' ? '#fef3c7' : operator.role === 'operator' ? '#dcfce7' : '#e0f2fe',
                color: operator.role === 'admin' ? '#92400e' : operator.role === 'operator' ? '#166534' : '#0369a1',
                fontWeight: 600,
              }}
            >
              Role: {operator.role}
            </span>
            <small style={{ color: '#64748b' }}>
              Expires: {new Date(operator.expiresAt).toLocaleTimeString()}
            </small>
            <button disabled={busy} type="button" onClick={onLogout}>
              Disconnect
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '10px', alignItems: 'center', maxWidth: 'none', margin: 0 }}>
            <input
              type="password"
              placeholder="Enter Bearer Token"
              value={tokenInput}
              disabled={busy}
              onChange={e => setTokenInput(e.target.value)}
              style={{ width: '280px', padding: '8px 12px' }}
              aria-label="Operator Bearer Token"
            />
            <button disabled={busy || !tokenInput.trim()} type="submit" style={{ whiteSpace: 'nowrap' }}>
              {busy ? 'Verifying…' : 'Authenticate'}
            </button>
          </form>
        )}
      </div>

      {!operator && (
        <p style={{ margin: '8px 0 0', fontSize: '12px', color: '#64748b' }}>
          Incident investigations, acknowledgements, and genuine maintenance tasks require a valid Bearer token.
        </p>
      )}

      {error && <p role="alert" className="error" style={{ margin: '10px 0 0', padding: '8px 12px' }}>{error}</p>}
      {notice && <p role="status" className="success" style={{ margin: '10px 0 0', padding: '8px 12px' }}>{notice}</p>}
    </div>
  );
}
