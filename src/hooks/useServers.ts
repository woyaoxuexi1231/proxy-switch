import { useState, useCallback, useEffect } from 'react';
import { getServers, deleteServer } from '../utils/invoke';
import type { Server } from '../types';

export function useServers() {
  const [servers, setServers] = useState<Server[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadServers = useCallback(async () => {
    setError(null);
    try {
      const next = await getServers();
      setServers(next);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadServers();
  }, [loadServers]);

  const removeServer = useCallback(
    async (name: string) => {
      setError(null);
      try {
        const result = await deleteServer(name);
        if (!result.success) {
          setError(result.message);
          return false;
        }
        await loadServers();
        return true;
      } catch (e) {
        setError(String(e));
        return false;
      }
    },
    [loadServers],
  );

  return {
    servers,
    loading,
    error,
    loadServers,
    removeServer,
    setError,
  };
}
