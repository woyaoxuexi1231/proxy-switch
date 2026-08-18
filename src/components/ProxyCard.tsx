import { useState, useCallback } from 'react';
import { useProxyStatus } from '../hooks/useProxyStatus';
import { ProxyDialog } from './ProxyDialog';
import {
  COMPONENT_SHORT,
  getProxyState,
} from '../types';
import type { ComponentId, ProxyStatus } from '../types';
import { cn } from '../lib/cn';
import { LoaderCircle } from 'lucide-react';

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
  const [open, setOpen] = useState(false);

  const handleOpen = useCallback(() => {
    if (!connected) return;
    setMessage(null);
    setLastResult(null);
    setOpen(true);
  }, [connected, setMessage, setLastResult]);

  const handleRefresh = useCallback(() => {
    setMessage(null);
    setLastResult(null);
    void refresh();
  }, [refresh, setMessage, setLastResult]);

  const shortLabel = COMPONENT_SHORT[component];
  const state = getProxyState(status);
  const proxyDisplay =
    status?.current_https_proxy ||
    status?.current_http_proxy ||
    status?.current_mirror ||
    null;

  return (
    <>
      <button
        type="button"
        onClick={handleOpen}
        disabled={!connected}
        title={connected ? `Configure ${label}` : 'Not connected'}
        className={cn(
          'flex min-h-[76px] w-full flex-col items-start rounded-[14px] bg-[#f9fafb] px-3 py-2.5 text-left transition-colors',
          'hover:bg-[#eef2f7] disabled:cursor-default disabled:opacity-55',
          open && 'bg-[#eef2f7] ring-1 ring-slate-200/80',
        )}
      >
        <div className="flex w-full items-start justify-between gap-2">
          <span className="font-display text-[13px] font-semibold leading-tight text-[#0a1b33]">
            {shortLabel}
          </span>
          <TileStatus status={status} loading={loading} />
        </div>

        {proxyDisplay &&
          (state === 'started' || !!status?.current_mirror) && (
            <span className="mt-auto w-full truncate pt-2 font-mono text-[10px] text-[#64748b]">
              {proxyDisplay}
            </span>
          )}

        {!proxyDisplay && !loading && (
          <span className="mt-auto pt-2 text-[10px] text-slate-400">
            {connected ? 'Click to configure' : 'Unavailable'}
          </span>
        )}
      </button>

      {open && (
        <ProxyDialog
          component={component}
          label={label}
          isRemote={isRemote}
          status={status}
          loading={loading}
          message={message}
          lastResult={lastResult}
          onClose={() => setOpen(false)}
          onRefresh={handleRefresh}
          onEnable={enable}
          onDisable={disable}
          setMessage={setMessage}
          setLastResult={setLastResult}
        />
      )}
    </>
  );
}

function TileStatus({
  status,
  loading,
}: {
  status: ProxyStatus | null;
  loading: boolean;
}) {
  if (loading) {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-medium text-slate-400">
        <LoaderCircle className="h-3 w-3 animate-spin" strokeWidth={2} />
      </span>
    );
  }

  if (!status) {
    return (
      <span className="rounded-full bg-slate-100 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-slate-400">
        —
      </span>
    );
  }

  const state = getProxyState(status);
  if (!state) return null;

  return (
    <span
      className={cn(
        'rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide',
        state === 'started' && 'bg-emerald-50 text-emerald-700',
        state === 'not_started' && 'bg-amber-50 text-amber-700',
        state === 'not_installed' && 'bg-slate-100 text-slate-400',
      )}
    >
      {state === 'started'
        ? 'ON'
        : state === 'not_started'
          ? 'OFF'
          : 'N/A'}
    </span>
  );
}
