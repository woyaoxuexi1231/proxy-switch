import { useState, useCallback, useEffect } from 'react';
import { detectProxy, enableProxy, disableProxy } from '../utils/invoke';
import type { ComponentId, OpResult, ProxyConfig, ProxyStatus } from '../types';

export function useProxyStatus(
  component: ComponentId,
  isRemote: boolean,
  seedStatus?: ProxyStatus | null,
) {
  const [status, setStatus] = useState<ProxyStatus | null>(seedStatus ?? null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<OpResult | null>(null);

  useEffect(() => {
    if (seedStatus) {
      setStatus(seedStatus);
    } else if (isRemote && seedStatus === null) {
      // Disconnect clears remote seed — drop stale status
      setStatus(null);
      setMessage(null);
      setLastResult(null);
    }
  }, [seedStatus, isRemote]);

  const refresh = useCallback(async () => {
    setLoading(true);
    setMessage(null);
    setLastResult(null);
    try {
      const next = await detectProxy(component, isRemote);
      setStatus(next);
    } catch (e) {
      setMessage(String(e));
      setLastResult({ success: false, message: String(e) });
    }
    setLoading(false);
  }, [component, isRemote]);

  const enable = useCallback(
    async (config: ProxyConfig) => {
      setLoading(true);
      setMessage(null);
      setLastResult(null);
      try {
        const result = await enableProxy(component, config, isRemote);
        setLastResult(result);
        setMessage(result.message);
        const next = await detectProxy(component, isRemote);
        setStatus(next);
        return result;
      } catch (e) {
        const fail: OpResult = { success: false, message: String(e) };
        setLastResult(fail);
        setMessage(fail.message);
        return fail;
      } finally {
        setLoading(false);
      }
    },
    [component, isRemote],
  );

  const disable = useCallback(async () => {
    setLoading(true);
    setMessage(null);
    setLastResult(null);
    try {
      const result = await disableProxy(component, isRemote);
      setLastResult(result);
      setMessage(result.message);
      const next = await detectProxy(component, isRemote);
      setStatus(next);
      return result;
    } catch (e) {
      const fail: OpResult = { success: false, message: String(e) };
      setLastResult(fail);
      setMessage(fail.message);
      return fail;
    } finally {
      setLoading(false);
    }
  }, [component, isRemote]);

  return {
    status,
    loading,
    message,
    lastResult,
    refresh,
    enable,
    disable,
    setMessage,
    setLastResult,
  };
}
