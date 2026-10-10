import { useEffect, useState } from 'react';
import { discoverRuntimeContract } from '../services/runtimeContract.js';
export function useRuntimeContract(mode, baseUrl, refresh) {
  const [state, setState] = useState({});
  const key = `${baseUrl}:${refresh}`;
  useEffect(() => {
    if (mode !== 'live') return;
    const controller = new AbortController();
    discoverRuntimeContract(baseUrl, controller.signal).then(value => {
      if (!controller.signal.aborted) setState({ ...value, baseUrl, key, phase: 'ready' });
    }).catch(error => {
      if (!controller.signal.aborted) setState({ key, baseUrl, phase: 'unavailable', message: error.message });
    });
    return () => controller.abort();
  }, [mode, baseUrl, key]);
  return mode === 'sample' ? { phase: 'sample', analytics: false, sampleMaintenance: false } : state.key === key ? state : state.baseUrl === baseUrl ? { ...state, phase: 'loading' } : { phase: 'loading', analytics: false, sampleMaintenance: false };
}
