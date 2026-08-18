import { useState } from 'react';
import type { Server } from '../types';
import { cn } from '../lib/cn';
import { Monitor, Pencil, Plus, Trash2 } from 'lucide-react';

interface Props {
  servers: Server[];
  connected: boolean;
  serverName: string | null;
  connLoading: boolean;
  connError: string | null;
  onConnect: (name: string) => void;
  onDisconnect: () => void;
  onAddServer: () => void;
  onEditServer: (server: Server) => void;
  onDeleteServer: (name: string) => void;
}

export function Sidebar({
  servers,
  connected,
  serverName,
  connLoading,
  connError,
  onConnect,
  onDisconnect,
  onAddServer,
  onEditServer,
  onDeleteServer,
}: Props) {
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const handleDelete = (name: string) => {
    if (confirmDelete === name) {
      onDeleteServer(name);
      setConfirmDelete(null);
    } else {
      setConfirmDelete(name);
    }
  };

  return (
    <aside className="flex h-full min-h-0 flex-col border-r border-slate-200/70 bg-white/80 px-3 py-4 backdrop-blur-xl">
      <div className="mb-4 px-1">
        <div className="text-[15px] font-semibold tracking-tight text-[#0a1b33]">
          Proxy Switch
        </div>
        <div className="mt-0.5 text-[11px] text-slate-500">
          Local and remote proxy control
        </div>
      </div>

      <div className="px-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
        Servers
      </div>

      <div className="mt-2 flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto pr-0.5">
        {servers.map((s) => {
          const isActive = connected && serverName === s.name;
          return (
            <div
              key={s.id}
              className={cn(
                'rounded-2xl border px-3 py-2.5 transition-colors',
                isActive
                  ? 'border-slate-300 bg-slate-50'
                  : 'border-slate-200/70 bg-white',
              )}
            >
              <div className="flex items-start gap-2">
                <span
                  className={cn(
                    'mt-1.5 h-2 w-2 shrink-0 rounded-full',
                    isActive ? 'bg-emerald-500' : 'bg-slate-300',
                  )}
                />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[13px] font-semibold text-[#0a1b33]">
                    {s.name}
                  </div>
                  <div className="truncate font-mono text-[11px] text-slate-500">
                    {s.host}:{s.port}
                  </div>
                  <div className="truncate text-[11px] text-slate-400">
                    {s.user}
                  </div>
                </div>
              </div>
              <div className="mt-2 flex items-center gap-1.5">
                <button
                  type="button"
                  className={cn(
                    'flex-1 rounded-full px-3 py-1.5 text-[11px] font-semibold transition-colors disabled:opacity-40',
                    isActive
                      ? 'border border-red-200 text-red-600 hover:bg-red-50'
                      : 'bg-[#0a152d] text-white hover:bg-[#15213d]',
                  )}
                  disabled={connLoading}
                  onClick={() =>
                    isActive ? onDisconnect() : onConnect(s.name)
                  }
                >
                  {connLoading && serverName === s.name
                    ? '...'
                    : isActive
                      ? 'Disconnect'
                      : 'Connect'}
                </button>
                <button
                  type="button"
                  className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-200/70 text-slate-500 hover:border-slate-300 hover:text-[#0a1b33]"
                  title="Edit server"
                  onClick={() => onEditServer(s)}
                >
                  <Pencil className="h-3.5 w-3.5" strokeWidth={2} />
                </button>
                <button
                  type="button"
                  className={cn(
                    'inline-flex h-8 w-8 items-center justify-center rounded-full border text-slate-500 hover:border-slate-300',
                    confirmDelete === s.name
                      ? 'border-amber-300 bg-amber-50 text-amber-700'
                      : 'border-slate-200/70 hover:text-[#0a1b33]',
                  )}
                  title={
                    confirmDelete === s.name
                      ? 'Click again to confirm'
                      : 'Delete server'
                  }
                  onClick={() => handleDelete(s.name)}
                  onBlur={() => setConfirmDelete(null)}
                >
                  <Trash2 className="h-3.5 w-3.5" strokeWidth={2} />
                </button>
              </div>
            </div>
          );
        })}
        {servers.length === 0 && (
          <div className="rounded-2xl border border-dashed border-slate-200 px-3 py-6 text-center text-[12px] text-slate-400">
            No servers yet
          </div>
        )}
      </div>

      <button
        type="button"
        className="mt-3 inline-flex items-center justify-center gap-1.5 rounded-full border border-slate-200/60 bg-white px-4 py-2 text-[12px] font-semibold text-[#0a1b33] shadow-sm hover:border-slate-300"
        onClick={onAddServer}
      >
        <Plus className="h-3.5 w-3.5" strokeWidth={2} />
        Add Server
      </button>

      {connError && (
        <div className="mt-2 rounded-xl bg-red-50 px-3 py-2 text-[11px] text-red-700">
          {connError}
        </div>
      )}

      <div className="mt-4 px-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
        Local
      </div>
      <div className="mt-2 rounded-2xl border border-slate-200/70 bg-slate-50 px-3 py-2.5">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-emerald-500" />
          <Monitor className="h-3.5 w-3.5 text-slate-500" strokeWidth={2} />
          <div>
            <div className="text-[13px] font-semibold text-[#0a1b33]">
              This PC
            </div>
            <div className="text-[11px] text-slate-500">Windows</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
