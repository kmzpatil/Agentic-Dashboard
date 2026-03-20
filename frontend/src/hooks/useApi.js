import { useEffect, useState } from 'react';

// Module-level in-memory cache — survives tab switches, cleared on hard refresh (F5)
const _cache = new Map(); // url -> { data: any, ts: number }
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

function getCached(url) {
  const hit = _cache.get(url);
  if (!hit) return null;
  if (Date.now() - hit.ts > CACHE_TTL) { _cache.delete(url); return null; }
  return hit.data;
}

function setCached(url, data) {
  _cache.set(url, { data, ts: Date.now() });
}

// Call with a specific url to invalidate one entry, or no args to clear all
export function invalidateApiCache(url) {
  if (url) _cache.delete(url);
  else _cache.clear();
}

export function useApi(url, dependencies = []) {
  const cached = url ? getCached(url) : null;

  const [data, setData] = useState(cached ?? null);
  const [dataUrl, setDataUrl] = useState(cached ? url : null);
  const [loading, setLoading] = useState(Boolean(url) && !cached);
  const [error, setError] = useState('');

  useEffect(() => {
    let ignore = false;

    if (!url) {
      setLoading(false);
      setError('');
      return () => { ignore = true; };
    }

    // Cache hit — serve immediately, skip network
    const hit = getCached(url);
    if (hit) {
      setData(hit);
      setDataUrl(url);
      setLoading(false);
      setError('');
      return () => { ignore = true; };
    }

    const load = async () => {
      setLoading(true);
      setError('');
      try {
        const token = localStorage.getItem('frammer_auth_token');
        const response = await fetch(url, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });

        if (!response.ok) {
          if (response.status === 401) {
            localStorage.removeItem('frammer_auth_token');
            localStorage.removeItem('frammer_auth_user');
          }
          throw new Error(`Request failed: ${response.status}`);
        }

        const payload = await response.json();
        if (!ignore) {
          setCached(url, payload);
          setData(payload);
          setDataUrl(url);
        }
      } catch (err) {
        if (!ignore) setError(err.message || 'Failed to load');
      } finally {
        if (!ignore) setLoading(false);
      }
    };

    load();
    return () => { ignore = true; };
  }, dependencies); // eslint-disable-line react-hooks/exhaustive-deps

  return { data, loading, error, dataUrl };
}
