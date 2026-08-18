import { useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { ProxyCard } from './components/ProxyCard';
import { ServerDialog } from './components/ServerDialog';
import { Island } from './components/Island';
import { useSshConnection } from './hooks/useSshConnection';
import { useServers } from './hooks/useServers';
import {
  REMOTE_COMPONENTS,
  LOCAL_COMPONENTS,
  COMPONENT_LABELS,
} from './types';
import type { ComponentId, ProxyStatus, Server } from './types';

export default function App() {
  const {
    servers,
    error: serversError,
    loadServers,
    removeServer,
  } = useServers();
  const [showServerDialog, setShowServerDialog] = useState(false);
  const [editingServer, setEditingServer] = useState<Server | null>(null);
  const {
    connected,
    serverName,
    loading: connLoading,
    error: connError,
    connect,
    disconnect,
    remoteStatuses,
    localStatuses,
    bulkDetecting,
  } = useSshConnection();

  const handleAddServer = () => {
    setEditingServer(null);
    setShowServerDialog(true);
  };

  const handleEditServer = (server: Server) => {
    setEditingServer(server);
    setShowServerDialog(true);
  };

  const handleServerSaved = () => {
    setShowServerDialog(false);
    setEditingServer(null);
    void loadServers();
  };

  const seedFor = (
    component: ComponentId,
    list: ProxyStatus[] | null,
  ): ProxyStatus | null | undefined => {
    if (!list) return undefined;
    return list.find((s) => s.component === component) ?? null;
  };

  return (
    <div className="flex h-screen min-h-0 bg-[#f9fafb] p-2.5 text-[#0a1b33]">
      <div className="grid min-h-0 flex-1 grid-cols-[248px_1fr] gap-2.5">
        <Island className="flex flex-col">
          <Sidebar
            servers={servers}
            connected={connected}
            serverName={serverName}
            connLoading={connLoading}
            connError={connError}
            onConnect={(name) => void connect(name)}
            onDisconnect={() => void disconnect()}
            onAddServer={handleAddServer}
            onEditServer={handleEditServer}
            onDeleteServer={(name) => void removeServer(name)}
          />
        </Island>

        <div className="flex min-h-0 flex-col gap-2.5">
          <Island className="shrink-0 px-4 py-3">
            <div className="font-display text-[13px] font-semibold tracking-tight text-[#0a1b33]">
              Workspace
            </div>
            <div className="mt-0.5 font-mono text-[11px] text-[#64748b]">
              {connected
                ? `Connected: ${serverName}`
                : 'Not connected to a remote server'}
              {bulkDetecting ? ' · Detecting...' : ''}
            </div>
          </Island>

          {(serversError || connError) && (
            <Island className="shrink-0 bg-red-50 px-4 py-2.5 text-[12px] text-red-700">
              {serversError || connError}
            </Island>
          )}

          <Island className="flex min-h-0 flex-1 flex-col">
            <h2 className="shrink-0 px-4 pb-2 pt-3 font-display text-[12px] font-semibold text-[#0a1b33]">
              Remote
              <span className="ml-2 font-sans text-[11px] font-medium text-[#64748b]">
                Ubuntu via SSH
              </span>
            </h2>
            <div className="min-h-0 flex-1 space-y-1.5 overflow-y-auto px-3 pb-3">
              {REMOTE_COMPONENTS.map((comp) => (
                <ProxyCard
                  key={comp}
                  component={comp}
                  label={COMPONENT_LABELS[comp]}
                  isRemote
                  connected={connected}
                  seedStatus={
                    connected ? seedFor(comp, remoteStatuses) : null
                  }
                />
              ))}
            </div>
          </Island>

          <Island className="flex min-h-0 flex-1 flex-col">
            <h2 className="shrink-0 px-4 pb-2 pt-3 font-display text-[12px] font-semibold text-[#0a1b33]">
              Local
              <span className="ml-2 font-sans text-[11px] font-medium text-[#64748b]">
                Windows
              </span>
            </h2>
            <div className="min-h-0 flex-1 space-y-1.5 overflow-y-auto px-3 pb-3">
              {LOCAL_COMPONENTS.map((comp) => (
                <ProxyCard
                  key={comp}
                  component={comp}
                  label={COMPONENT_LABELS[comp]}
                  isRemote={false}
                  connected
                  seedStatus={seedFor(comp, localStatuses)}
                />
              ))}
            </div>
          </Island>
        </div>
      </div>

      {showServerDialog && (
        <ServerDialog
          server={editingServer}
          onSaved={handleServerSaved}
          onCancel={() => {
            setShowServerDialog(false);
            setEditingServer(null);
          }}
        />
      )}
    </div>
  );
}
