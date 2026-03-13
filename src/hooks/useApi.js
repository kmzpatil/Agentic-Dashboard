import { useEffect, useState } from 'react';

export function useApi(url, dependencies = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(Boolean(url));
  const [error, setError] = useState('');

  useEffect(() => {
    let ignore = false;

    if (!url) {
      setLoading(false);
      setError('');
      return () => {
        ignore = true;
      };
    }

    const load = async () => {
      setLoading(true);
      setError('');
      try {
        const token = localStorage.getItem('frammer_auth_token');
        const response = await fetch(url, {
          headers: token
            ? {
              Authorization: `Bearer ${token}`,
            }
            : {},
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
          setData(payload);
        }
      } catch (err) {
        if (!ignore) {
          setError(err.message || 'Failed to load');
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    };

    load();
    return () => {
      ignore = true;
    };
  }, dependencies);

  return { data, loading, error };
}
