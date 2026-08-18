import { useState, useEffect, useCallback } from 'react';
import { useProxyStatus } from '../hooks/useProxyStatus';
import { StatusIndicator } from './StatusIndicator';
import { ManualGuide } from './ManualGuide';
import {
  ALIYUN_MAVEN,
  getProxyState,
  isGuideOnly,
  isMavenComponent,
  needsSudo,
  supportsMirror,
} from '../types';
import type { ComponentId, ProxyConfig, ProxyStatus } from '../types';
import { cn } from '../lib/cn';
import { ChevronDown, RefreshCw } from 'lucide-react';

interface Props {
  component: ComponentId;
  label: string;
  isRemote: boolean;
  connected: boolean;
  seedStatus?: ProxyStatus | null;
}

export function ProxyCard({
  component,
  label,
  isRemote,
  connected,
  seedStatus,
}: Props) {
  const {
    status,
    loading,
    message,
    lastResult,
    refresh,
    enable,
    disable,
    setMessage,
    setLastResult,
  } = useProxyStatus(component, isRemote, seedStatus);
  const [expanded, setExpanded] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  const [httpProxy, setHttpProxy] = useState('');
  const [httpsProxy, setHttpsProxy] = useState('');
  const [noProxy, setNoProxy] = useState('');
  const [mirror, setMirror] = useState('');

  const guideOnly = isGuideOnly(component);
  const sudo = needsSudo(component);
  const mirrorOk = supportsMirror(component);
  const maven = isMavenComponent(component);

  useEffect(() => {
    setHydrated(false);
  }, [component]);

  useEffect(() => {
    if (!status || hydrated) return;
    setHttpProxy(status.current_http_proxy ?? '');
    setHttpsProxy(status.current_https_proxy ?? '');
    setNoProxy(status.current_no_proxy ?? '');
    setMirror(status.current_mirror ?? '');
    setHydrated(true);
  }, [status, hydrated]);

  const handleRefresh = useCallback(() => {
    setMessage(null);
    setLastResult(null);
    void refresh();
  }, [refresh, setMessage, setLastResult]);

  const handleEnable = useCallback(async () => {
    if (!httpProxy && !httpsProxy && !(mirrorOk && mirror)) {
      const msg = mirrorOk
        ? 'Enter a proxy URL or a mirror URL.'
        : 'At least one proxy URL is required.';
      setMessage(msg);
      setLastResult({ success: false, message: msg });
      return;
    }
    setMessage(null);
    setLastResult(null);
    const config: ProxyConfig = {
      http_proxy: httpProxy.trim(),
      https_proxy: httpsProxy.trim(),
      no_proxy: noProxy.trim(),
      mirror: mirror.trim(),
    };
    await enable(config);
  }, [
    httpProxy,
    httpsProxy,
    noProxy,
    mirror,
    enable,
    setMessage,
    setLastResult,
    mirrorOk,
  ]);

  const handleAliyunMirror = useCallback(async () => {
    setMirror(ALIYUN_MAVEN);
    setMessage(null);
    setLastResult(null);
    await enable({
      http_proxy: '',
      https_proxy: '',
      no_proxy: '',
      mirror: ALIYUN_MAVEN,
    });
  }, [enable, setMessage, setLastResult]);

  const handleDisable = useCallback(async () => {
    setMessage(null);
    setLastResult(null);
    await disable();
  }, [disable, setMessage, setLastResult]);

  const proxyDisplay =
    status?.current_https_proxy ||
    status?.current_http_proxy ||
    status?.current_mirror ||
    null;

  const messageTone =
    lastResult != null
      ? lastResult.success
        ? 'ok'
        : 'error'
      : message
        ? 'error'
        : null;

  return (
    <div
      className={cn(
        'rounded-[12px] bg-[#f9fafb] transition-colors',
        expanded && 'bg-[#f3f5f8]',
      )}
    >
      <div className="flex items-center justify-between gap-2 px-4 py-2.5">
        <button
          type="button"
          className="flex min-w-0 flex-1 items-center gap-3 text-left disabled:cursor-default disabled:opacity-60"
          onClick={() => {
            if (connected) setExpanded(!expanded);
          }}
          disabled={!connected}
          title={connected ? 'Click to expand' : 'Not connected'}
        >
          <StatusIndicator status={status} loading={loading} />
          <span className="truncate font-display text-[13px] font-semibold text-[#0a1b33]">
            {label}
          </span>
          {proxyDisplay &&
            (getProxyState(status) === 'started' || !!status?.current_mirror) && (
              <span className="truncate font-mono text-[11px] text-slate-500">
                {proxyDisplay}
              </span>
            )}
          {connected && (
            <ChevronDown
              className={cn(
                'ml-auto h-4 w-4 shrink-0 text-slate-400 transition-transform',
                expanded && 'rotate-180',
              )}
              strokeWidth={2}
            />
          )}
        </button>
        <button
          type="button"
          className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-slate-500 hover:bg-slate-100 hover:text-[#0a1b33] disabled:opacity-40"
          onClick={handleRefresh}
          disabled={loading || !connected}
          title="Refresh status"
        >
          <RefreshCw
            className={cn('h-3.5 w-3.5', loading && 'animate-spin')}
            strokeWidth={2}
          />
        </button>
      </div>

      {expanded && (
        <div className="border-t border-slate-200/60 px-4 pb-4 pt-3">
          {status?.config_files && status.config_files.length > 0 && (
            <div className="mb-2">
              <div className="mb-1 text-[11px] font-medium text-slate-400">
                Config files
              </div>
              {status.config_files.map((f) => (
                <code
                  key={f}
                  className="block font-mono text-[11px] text-slate-500"
                >
                  {f}
                </code>
              ))}
            </div>
          )}

          {status?.manual_setup_steps && (
            <ManualGuide
              steps={status.manual_setup_steps}
              defaultOpen={guideOnly}
            />
          )}

          {message && (
            <div
              className={cn(
                'mt-3 rounded-lg px-3 py-2 text-[12px]',
                messageTone === 'ok'
                  ? 'bg-emerald-50 text-emerald-700'
                  : 'bg-red-50 text-red-700',
              )}
            >
              {message}
            </div>
          )}

          {!guideOnly && (
            <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field
                label="HTTP Proxy"
                value={httpProxy}
                placeholder="http://127.0.0.1:7890"
                onChange={setHttpProxy}
              />
              <Field
                label="HTTPS Proxy"
                value={httpsProxy}
                placeholder="http://127.0.0.1:7890"
                onChange={setHttpsProxy}
              />
              <div className="sm:col-span-2">
                <Field
                  label="No Proxy"
                  value={noProxy}
                  placeholder="localhost,127.0.0.1,::1"
                  onChange={setNoProxy}
                />
              </div>
              {mirrorOk && (
                <div className="sm:col-span-2">
                  <Field
                    label={maven ? 'Maven Mirror' : 'Mirror URL'}
                    value={mirror}
                    placeholder={
                      maven ? ALIYUN_MAVEN : 'https://mirror.example.com'
                    }
                    onChange={setMirror}
                  />
                </div>
              )}
            </div>
          )}

          {!guideOnly && (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <button
                type="button"
                className="rounded-full bg-[#0a152d] px-4 py-2 text-[12px] font-semibold text-white disabled:opacity-40"
                onClick={() => void handleEnable()}
                disabled={loading}
              >
                Apply
              </button>
              {maven && (
                <button
                  type="button"
                  className="rounded-full border border-slate-200/60 bg-white px-4 py-2 text-[12px] font-semibold text-[#0a1b33] shadow-sm hover:border-slate-300 disabled:opacity-40"
                  onClick={() => void handleAliyunMirror()}
                  disabled={loading}
                  title={ALIYUN_MAVEN}
                >
                  Aliyun mirror
                </button>
              )}
              <button
                type="button"
                className="rounded-full border border-red-200 bg-white px-4 py-2 text-[12px] font-semibold text-red-600 hover:bg-red-50 disabled:opacity-40"
                onClick={() => void handleDisable()}
                disabled={loading || getProxyState(status) !== 'started'}
              >
                Disable
              </button>
              {sudo && isRemote && (
                <span className="ml-auto rounded-full bg-amber-50 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-amber-700">
                  sudo
                </span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Field({
  label,
  value,
  placeholder,
  onChange,
}: {
  label: string;
  value: string;
  placeholder: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[11px] font-medium text-slate-500">{label}</span>
      <input
        className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 font-mono text-[12px] text-[#0a1b33] outline-none transition-colors placeholder:text-slate-400 focus:border-slate-400 focus:bg-white"
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}
