import { useEffect, useState } from 'react';

const cache = new Map(); // url -> { data, timestamp }
const CACHE_TTL = 10 * 60 * 1000; // 10 minutes

export function clearApiCache() {
  cache.clear();
}

export function useApi(url, dependencies = []) {
  const [data, setData] = useState(null);
  const [dataUrl, setDataUrl] = useState(null);
  const [loading, setLoading] = useState(Boolean(url));
  const [error, setError] = useState('');

  useEffect(() => {
    let ignore = false;

    if (!url) {
      setLoading(false);
      setError('');
      return () => { ignore = true; };
    }

    const load = async () => {
      const cached = cache.get(url);
      if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
        if (!ignore) {
          setData(cached.data);
          setDataUrl(url);
          setLoading(false);
        }
        return;
      }

      setLoading(true);
      setError('');
      try {
        const token = localStorage.getItem('frammer_auth_token');
        const response = await fetch(url, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });

        if (!response.ok) {
          if (response.status === 401) {
            cache.clear();
            localStorage.removeItem('frammer_auth_token');
            localStorage.removeItem('frammer_auth_user');
          }
          throw new Error(`Request failed: ${response.status}`);
        }

        const payload = await response.json();
        if (!ignore) {
          cache.set(url, { data: payload, timestamp: Date.now() });
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
  }, dependencies);

  return { data, loading, error, dataUrl };
}
