import { useCallback, useEffect, useRef, useState } from 'react';
import { API_BASE } from '../../../lib/constants';

const REFRESH_MS = 5000;
const BASE = `${API_BASE}/labs/simulator`;

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed: ${url}`);
  return res.json();
}

export default function useDqaData() {
  const [status, setStatus] = useState(null);
  const [stageScores, setStageScores] = useState(null);
  const [funnel, setFunnel] = useState(null);
  const [errorDist, setErrorDist] = useState(null);
  const [timeseries, setTimeseries] = useState(null);
  const [criticalIssues, setCriticalIssues] = useState([]);
  const [logs, setLogs] = useState([]);
  const [schemas, setSchemas] = useState([]);
  const [errorConfig, setErrorConfig] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const mounted = useRef(true);

  const loadAll = useCallback(async () => {
    try {
      const [
        statusRes, stagesRes, funnelRes, errorsRes,
        tsRes, criticalRes, logsRes, schemasRes, configRes,
      ] = await Promise.all([
        fetchJson(`${BASE}/status`),
        fetchJson(`${BASE}/quality/stages`),
        fetchJson(`${BASE}/quality/funnel`),
        fetchJson(`${BASE}/quality/errors`),
        fetchJson(`${BASE}/quality/timeseries`),
        fetchJson(`${BASE}/quality/critical?limit=10`),
        fetchJson(`${BASE}/logs?limit=50`),
        fetchJson(`${BASE}/schemas`),
        fetchJson(`${BASE}/errors/config`),
      ]);
      if (!mounted.current) return;
      setStatus(statusRes);
      setStageScores(stagesRes);
      setFunnel(funnelRes);
      setErrorDist(errorsRes);
      setTimeseries(tsRes);
      setCriticalIssues(criticalRes);
      setLogs(logsRes);
      setSchemas(schemasRes);
      setErrorConfig(configRes);
      setError('');
    } catch (err) {
      if (mounted.current) setError(err.message || 'Failed to load DQA data');
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    loadAll();
    const id = setInterval(loadAll, REFRESH_MS);
    return () => {
      mounted.current = false;
      clearInterval(id);
    };
  }, [loadAll]);

  const runAction = useCallback(async (action, params = {}) => {
    try {
      setError('');
      let url = `${BASE}/${action}`;
      const qs = new URLSearchParams(params).toString();
      if (qs) url += `?${qs}`;
      const res = await fetch(url, { method: 'POST' });
      if (!res.ok) throw new Error(`Failed to ${action}`);
      await loadAll();
    } catch (err) {
      setError(err.message || 'Action failed');
    }
  }, [loadAll]);

  const updateErrorConfig = useCallback(async (rates) => {
    try {
      const res = await fetch(`${BASE}/errors/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rates }),
      });
      if (!res.ok) throw new Error('Failed to update error config');
      const data = await res.json();
      setErrorConfig(data.rates || {});
    } catch (err) {
      setError(err.message);
    }
  }, []);

  return {
    status, stageScores, funnel, errorDist, timeseries,
    criticalIssues, logs, schemas, errorConfig,
    loading, error,
    refresh: loadAll,
    runAction,
    updateErrorConfig,
  };
}
