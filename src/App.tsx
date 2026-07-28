import { useState, useEffect, useCallback } from 'react';
import { Sidebar } from './components/Sidebar';
import { ProxyCard } from './components/ProxyCard';
import { ServerDialog } from './components/ServerDialog';
import { getServers } from './utils/invoke';
import { useSshConnection } from './hooks/useSshConnection';
import {
  REMOTE_COMPONENTS,
  LOCAL_COMPONENTS,
  COMPONENT_LABELS,
} from './types';
import type { Server } from './types';

export default function App() {
  const [servers, setServers] = useState<Server[]>([]);
  const [showAddServer, setShowAddServer] = useState(false);
  const { connected, serverName, loading: connLoading, error: connError, connect, disconnect } =
    useSshConnection();

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

  const handleAddServer = () => setShowAddServer(true);

  const handleServerSaved = () => {
    setShowAddServer(false);
    loadServers();
  };

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
            />
          ))}
        </section>
      </main>
      <footer className="status-bar">
        <span>{connected ? `Connected: ${serverName}` : 'Not connected'}</span>
      </footer>
      {showAddServer && (
        <ServerDialog
          server={null}
          onSaved={handleServerSaved}
          onCancel={() => setShowAddServer(false)}
        />
      )}
    </div>
  );
}
