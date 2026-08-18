import { useState, useCallback, useEffect } from 'react';
import {
  sshConnect,
  sshDisconnect,
  sshState,
  remoteDetectAll,
  localDetectAll,
} from '../utils/invoke';
import type { ProxyStatus } from '../types';

export function useSshConnection() {
  const [connected, setConnected] = useState(false);
  const [serverName, setServerName] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [remoteStatuses, setRemoteStatuses] = useState<ProxyStatus[] | null>(
    null,
  );
  const [localStatuses, setLocalStatuses] = useState<ProxyStatus[] | null>(null);
  const [bulkDetecting, setBulkDetecting] = useState(false);

  const refreshLocalStatuses = useCallback(async () => {
    try {
      const statuses = await localDetectAll();
      setLocalStatuses(statuses);
    } catch (e) {
      setError(String(e));
    }
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        const state = await sshState();
        setConnected(state.connected);
        setServerName(state.server_name);
        if (state.error) setError(state.error);
      } catch {
        // Best-effort restore on cold start
      }
      setBulkDetecting(true);
      try {
        await refreshLocalStatuses();
      } finally {
        setBulkDetecting(false);
      }
    })();
  }, [refreshLocalStatuses]);

  const connect = useCallback(async (name: string) => {
    setLoading(true);
    setError(null);
    setRemoteStatuses(null);
    try {
      const result = await sshConnect(name);
      if (result.success) {
        setConnected(true);
        setServerName(name);
        setBulkDetecting(true);
        try {
          const statuses = await remoteDetectAll();
          setRemoteStatuses(statuses);
        } catch (e) {
          setError(String(e));
        } finally {
          setBulkDetecting(false);
        }
      } else {
        setError(result.message);
        setConnected(false);
        setServerName(null);
        setRemoteStatuses(null);
      }
    } catch (e) {
      setError(String(e));
      setConnected(false);
      setServerName(null);
      setRemoteStatuses(null);
    }
    setLoading(false);
  }, []);

  const disconnect = useCallback(async () => {
    setLoading(true);
    try {
      const result = await sshDisconnect();
      if (!result.success) {
        setError(result.message);
      }
    } catch (e) {
      setError(String(e));
    }
    setConnected(false);
    setServerName(null);
    setRemoteStatuses(null);
    setLoading(false);
  }, []);

  return {
    connected,
    serverName,
    loading,
    error,
    connect,
    disconnect,
    remoteStatuses,
    localStatuses,
    bulkDetecting,
    refreshLocalStatuses,
    setError,
  };
}
