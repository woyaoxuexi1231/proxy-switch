import { useState, useEffect, useCallback } from 'react';
import { ManualGuide } from './ManualGuide';
import { StatusIndicator } from './StatusIndicator';
import {
  ALIYUN_MAVEN,
  getProxyState,
  isGuideOnly,
  isMavenComponent,
  needsSudo,
  supportsMirror,
} from '../types';
import type {
  ComponentId,
  OpResult,
  ProxyConfig,
  ProxyStatus,
} from '../types';
import { cn } from '../lib/cn';
import { RefreshCw, X } from 'lucide-react';

interface Props {
  component: ComponentId;
  label: string;
  isRemote: boolean;
  status: ProxyStatus | null;
  loading: boolean;
  message: string | null;
  lastResult: OpResult | null;
  onClose: () => void;
  onRefresh: () => void;
  onEnable: (config: ProxyConfig) => Promise<OpResult | void>;
  onDisable: () => Promise<OpResult | void>;
  setMessage: (msg: string | null) => void;
  setLastResult: (result: OpResult | null) => void;
}

export function ProxyDialog({
  component,
  label,
  isRemote,
  status,
  loading,
  message,
  lastResult,
  onClose,
  onRefresh,
  onEnable,
  onDisable,
  setMessage,
  setLastResult,
}: Props) {
  const [httpProxy, setHttpProxy] = useState('');
  const [httpsProxy, setHttpsProxy] = useState('');
  const [noProxy, setNoProxy] = useState('');
  const [mirror, setMirror] = useState('');

  const guideOnly = isGuideOnly(component);
  const sudo = needsSudo(component);
  const mirrorOk = supportsMirror(component);
  const maven = isMavenComponent(component);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  useEffect(() => {
    if (!status) return;
    setHttpProxy(status.current_http_proxy ?? '');
    setHttpsProxy(status.current_https_proxy ?? '');
    setNoProxy(status.current_no_proxy ?? '');
    setMirror(status.current_mirror ?? '');
  }, [status]);

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
    await onEnable({
      http_proxy: httpProxy.trim(),
      https_proxy: httpsProxy.trim(),
      no_proxy: noProxy.trim(),
      mirror: mirror.trim(),
    });
  }, [
    httpProxy,
    httpsProxy,
    noProxy,
    mirror,
    mirrorOk,
    onEnable,
    setMessage,
    setLastResult,
  ]);

  const handleAliyunMirror = useCallback(async () => {
    setMirror(ALIYUN_MAVEN);
    setMessage(null);
    setLastResult(null);
    await onEnable({
      http_proxy: '',
      https_proxy: '',
      no_proxy: '',
      mirror: ALIYUN_MAVEN,
    });
  }, [onEnable, setMessage, setLastResult]);

  const handleDisable = useCallback(async () => {
    setMessage(null);
    setLastResult(null);
    await onDisable();
  }, [onDisable, setMessage, setLastResult]);

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
      className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/25 px-4 backdrop-blur-[2px]"
      onClick={onClose}
    >
      <div
        className="flex max-h-[90vh] w-full max-w-[480px] flex-col overflow-hidden rounded-[28px] border border-slate-200/60 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.12)]"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={label}
      >
        <div className="flex shrink-0 items-center justify-between border-b border-slate-100 px-5 py-4">
          <div className="min-w-0">
            <h2 className="font-display text-[16px] font-semibold text-[#0a1b33]">
              {label}
            </h2>
            <p className="mt-0.5 text-[11px] text-[#64748b]">
              {isRemote ? 'Remote · Ubuntu via SSH' : 'Local · Windows'}
              {sudo && isRemote ? ' · sudo' : ''}
            </p>
            <div className="mt-1.5">
              <StatusIndicator status={status} loading={loading} />
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              className="inline-flex h-8 w-8 items-center justify-center rounded-full text-slate-400 hover:bg-slate-100 hover:text-[#0a1b33] disabled:opacity-40"
              onClick={onRefresh}
              disabled={loading}
              title="Refresh status"
            >
              <RefreshCw
                className={cn('h-3.5 w-3.5', loading && 'animate-spin')}
                strokeWidth={2}
              />
            </button>
            <button
              type="button"
              className="inline-flex h-8 w-8 items-center justify-center rounded-full text-slate-400 hover:bg-slate-100 hover:text-[#0a1b33]"
              onClick={onClose}
              aria-label="Close"
            >
              <X className="h-4 w-4" strokeWidth={2} />
            </button>
          </div>
        </div>

        <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-5 py-4">
          {status?.config_files && status.config_files.length > 0 && (
            <div>
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
                'rounded-lg px-3 py-2 text-[12px]',
                messageTone === 'ok'
                  ? 'bg-emerald-50 text-emerald-700'
                  : 'bg-red-50 text-red-700',
              )}
            >
              {message}
            </div>
          )}

          {!guideOnly && (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
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
        </div>

        {!guideOnly && (
          <div className="flex shrink-0 flex-wrap items-center gap-2 border-t border-slate-100 px-5 py-4">
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

        {guideOnly && (
          <div className="shrink-0 border-t border-slate-100 px-5 py-4">
            <button
              type="button"
              className="rounded-full border border-slate-200/60 bg-white px-4 py-2 text-[12px] font-semibold text-[#0a1b33] shadow-sm hover:border-slate-300"
              onClick={onClose}
            >
              Close
            </button>
          </div>
        )}
      </div>
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
