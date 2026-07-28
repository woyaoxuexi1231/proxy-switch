import { useState, useCallback } from 'react';
import { sshConnect, sshDisconnect } from '../utils/invoke';

export function useSshConnection() {
  const [connected, setConnected] = useState(false);
  const [serverName, setServerName] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const connect = useCallback(async (name: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await sshConnect(name);
      if (result.success) {
        setConnected(true);
        setServerName(name);
      } else {
        setError(result.message);
        setConnected(false);
        setServerName(null);
      }
    } catch (e) {
      setError(String(e));
      setConnected(false);
      setServerName(null);
    }
    setLoading(false);
  }, []);

  const disconnect = useCallback(async () => {
    setLoading(true);
    try {
      await sshDisconnect();
    } catch {
      // ignore
    }
    setConnected(false);
    setServerName(null);
    setError(null);
    setLoading(false);
  }, []);

  return { connected, serverName, loading, error, connect, disconnect };
}
