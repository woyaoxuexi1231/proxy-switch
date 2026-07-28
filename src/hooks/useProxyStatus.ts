import { useState, useCallback } from 'react';
import { detectProxy, enableProxy, disableProxy } from '../utils/invoke';
import type { ComponentId, ProxyConfig, ProxyStatus } from '../types';

export function useProxyStatus(component: ComponentId, isRemote: boolean) {
  const [status, setStatus] = useState<ProxyStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setMessage(null);
    try {
      const s = await detectProxy(component, isRemote);
      setStatus(s);
    } catch (e) {
      setMessage(String(e));
    }
    setLoading(false);
  }, [component, isRemote]);

  const enable = useCallback(
    async (config: ProxyConfig) => {
      setLoading(true);
      setMessage(null);
      try {
        const result = await enableProxy(component, config, isRemote);
        setMessage(result.message);
        // Refresh after enable
        const s = await detectProxy(component, isRemote);
        setStatus(s);
      } catch (e) {
        setMessage(String(e));
      }
      setLoading(false);
    },
    [component, isRemote],
  );

  const disable = useCallback(async () => {
    setLoading(true);
    setMessage(null);
    try {
      const result = await disableProxy(component, isRemote);
      setMessage(result.message);
      const s = await detectProxy(component, isRemote);
      setStatus(s);
    } catch (e) {
      setMessage(String(e));
    }
    setLoading(false);
  }, [component, isRemote]);

  return { status, loading, message, refresh, enable, disable, setMessage };
}
