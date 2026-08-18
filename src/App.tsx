import { useRef, useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { ProxyCard } from './components/ProxyCard';
import { ServerDialog } from './components/ServerDialog';
import { HeroLanding } from './components/HeroLanding';
import { LogoMarquee } from './components/LogoMarquee';
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
  const workspaceRef = useRef<HTMLElement>(null);
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

  const scrollToWorkspace = () => {
    workspaceRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const seedFor = (
    component: ComponentId,
    list: ProxyStatus[] | null,
  ): ProxyStatus | null | undefined => {
    if (!list) return undefined;
    return list.find((s) => s.component === component) ?? null;
  };

  return (
    <div className="min-h-screen bg-[#f9fafb] text-[#0a1b33]">
      <div className="px-4 pb-16 pt-6 md:px-8 md:pt-10">
        <HeroLanding
          onContact={scrollToWorkspace}
          onProducts={scrollToWorkspace}
          onDocs={scrollToWorkspace}
        />
        <LogoMarquee />

        <section
          ref={workspaceRef}
          id="workspace"
          className="mx-auto mt-12 w-full max-w-[1400px] overflow-hidden rounded-[32px] border border-slate-200/60 bg-white shadow-[0_24px_80px_-28px_rgba(0,0,0,0.08)]"
        >
          <div className="grid min-h-[640px] grid-cols-1 md:grid-cols-[260px_1fr]">
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

            <main className="flex min-h-0 flex-col bg-[#fbfcfd]">
              <div className="flex items-center justify-between gap-3 border-b border-slate-200/70 px-5 py-3">
                <div>
                  <div className="text-[13px] font-semibold text-[#0a1b33]">
                    Proxy workspace
                  </div>
                  <div className="text-[11px] text-slate-500">
                    {connected
                      ? `Connected: ${serverName}`
                      : 'Not connected to a remote server'}
                    {bulkDetecting ? ' · Detecting…' : ''}
                  </div>
                </div>
              </div>

              {(serversError || connError) && (
                <div className="mx-5 mt-4 rounded-xl bg-red-50 px-3 py-2 text-[12px] text-red-700">
                  {serversError || connError}
                </div>
              )}

              <div className="flex-1 space-y-6 overflow-y-auto px-5 py-5">
                <section>
                  <h2 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                    Remote (Ubuntu via SSH)
                  </h2>
                  <div className="space-y-2">
                    {REMOTE_COMPONENTS.map((comp) => (
                      <ProxyCard
                        key={comp}
                        component={comp}
                        label={COMPONENT_LABELS[comp]}
                        isRemote
                        connected={connected}
                        seedStatus={
                          connected
                            ? seedFor(comp, remoteStatuses)
                            : null
                        }
                      />
                    ))}
                  </div>
                </section>

                <section>
                  <h2 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                    Local (Windows)
                  </h2>
                  <div className="space-y-2">
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
                </section>
              </div>

              <footer className="border-t border-slate-200/70 px-5 py-2 text-[11px] text-slate-500">
                {connected ? `Connected: ${serverName}` : 'Not connected'}
              </footer>
            </main>
          </div>
        </section>
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
