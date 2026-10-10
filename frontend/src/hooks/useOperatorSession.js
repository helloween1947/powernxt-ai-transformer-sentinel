import { useEffect, useState } from 'react';
import { clearStoredToken, fetchOperatorMe, getStoredToken, saveToken } from '../services/auth.js';

const originKey = 'powernxt-operator-origin';
export function useOperatorSession(baseUrl, enabled) {
  const [session, setSession] = useState({ origin: '', operator: null, busy: false, error: '', notice: '' });
  const origin = baseUrl.replace(/\/+$/, '');
  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    let savedOrigin;
    try { savedOrigin = sessionStorage.getItem(originKey); } catch { /* Restricted storage. */ }
    const token = savedOrigin === origin ? getStoredToken() : '';
    if (token) fetchOperatorMe(origin, token).then(operator => {
      if (!cancelled) setSession({ origin, operator, busy: false, error: '', notice: '' });
    }).catch(error => {
      if (!cancelled) { clearStoredToken(); setSession({ origin, operator: null, busy: false, error: error.message, notice: '' }); }
    });
    return () => { cancelled = true; };
  }, [origin, enabled]);
  useEffect(() => {
    function invalidate() {
      clearStoredToken();
      setSession({ origin, operator: null, busy: false, error: 'Credential expired or was revoked. Authenticate again.', notice: '' });
    }
    const timer = setInterval(() => {
      if (session.origin === origin && session.operator && Date.now() >= Date.parse(session.operator.expiresAt)) invalidate();
    }, 1000);
    window.addEventListener('powernxt-credential-invalid', invalidate);
    return () => { clearInterval(timer); window.removeEventListener('powernxt-credential-invalid', invalidate); };
  }, [origin, session]);
  async function login(token) {
    setSession({ origin, operator: null, busy: true, error: '', notice: '' });
    try {
      const operator = await fetchOperatorMe(origin, token);
      saveToken(token);
      try { sessionStorage.setItem(originKey, origin); } catch { /* Session remains memory-only. */ }
      setSession({ origin, operator, busy: false, error: '', notice: 'Local prototype credential verified by the server.' });
    } catch (error) {
      clearStoredToken();
      setSession({ origin, operator: null, busy: false, error: error.message, notice: '' });
    }
  }
  function logout() {
    clearStoredToken();
    setSession({ origin, operator: null, busy: false, error: '', notice: 'Operator session ended.' });
  }
  return { ...(enabled && session.origin === origin ? session : { operator: null, busy: false, error: '', notice: '' }), onLogin: login, onLogout: logout };
}
