import { useState, useEffect, useCallback } from 'react';
import { Sidebar } from './components/Sidebar';
import { ProxyCard } from './components/ProxyCard';
import { ServerDialog } from './components/ServerDialog';
import { getServers, deleteServer, localDetectAll, remoteDetectAll } from './utils/invoke';
import { useSshConnection } from './hooks/useSshConnection';
import { REMOTE_COMPONENTS, LOCAL_COMPONENTS, COMPONENT_LABELS } from './types';
import type { Server, ProxyStatus } from './types';

export default function App() {
  const [servers, setServers] = useState<Server[]>([]);
  const [showServerDialog, setShowServerDialog] = useState(false);
  const [editingServer, setEditingServer] = useState<Server | null>(null);
  const { connected, serverName, loading: connLoading, error: connError, connect, disconnect } =
    useSshConnection();

  // Batch-detected statuses
  const [localStatuses, setLocalStatuses] = useState<ProxyStatus[]>([]);
  const [remoteStatuses, setRemoteStatuses] = useState<ProxyStatus[]>([]);

  const loadServers = useCallback(async () => {
    try {
      const s = await getServers();
      setServers(s);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    loadServers();
  }, [loadServers]);

  // Batch detect all local components on mount
  useEffect(() => {
    localDetectAll().then(setLocalStatuses).catch(() => {});
  }, []);

  // Batch detect all remote components when SSH connects
  useEffect(() => {
    if (connected) {
      remoteDetectAll().then(setRemoteStatuses).catch(() => {});
    } else {
      setRemoteStatuses([]);
    }
  }, [connected]);

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
    loadServers();
  };

  const handleDeleteServer = async (name: string) => {
    try {
      await deleteServer(name);
      loadServers();
    } catch {
      // ignore
    }
  };

  const getLocalStatus = (comp: string) =>
    localStatuses.find((s) => s.component === comp) ?? null;

  const getRemoteStatus = (comp: string) =>
    remoteStatuses.find((s) => s.component === comp) ?? null;

  return (
    <div className="app">
      <Sidebar
        servers={servers}
        connected={connected}
        serverName={serverName}
        connLoading={connLoading}
        connError={connError}
        onConnect={connect}
        onDisconnect={disconnect}
        onAddServer={handleAddServer}
        onEditServer={handleEditServer}
        onDeleteServer={handleDeleteServer}
      />
      <main className="main-content">
        <section className="section">
          <h2 className="section-title">Remote (Ubuntu via SSH)</h2>
          {REMOTE_COMPONENTS.map((comp) => (
            <ProxyCard
              key={comp}
              component={comp}
              label={COMPONENT_LABELS[comp]}
              isRemote
              connected={connected}
              initialStatus={getRemoteStatus(comp)}
            />
          ))}
        </section>
        <section className="section">
          <h2 className="section-title">Local (Windows)</h2>
          {LOCAL_COMPONENTS.map((comp) => (
            <ProxyCard
              key={comp}
              component={comp}
              label={COMPONENT_LABELS[comp]}
              isRemote={false}
              connected={true}
              initialStatus={getLocalStatus(comp)}
            />
          ))}
        </section>
      </main>
      <footer className="status-bar">
        <span>{connected ? `Connected: ${serverName}` : 'Not connected'}</span>
      </footer>
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
