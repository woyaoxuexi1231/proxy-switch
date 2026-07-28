import type { Server } from '../types';
import './Sidebar.css';

interface Props {
  servers: Server[];
  connected: boolean;
  serverName: string | null;
  connLoading: boolean;
  connError: string | null;
  onConnect: (name: string) => void;
  onDisconnect: () => void;
  onAddServer: () => void;
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
}: Props) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <span className="sidebar-logo">Proxy Switch</span>
      </div>

      <div className="sidebar-section-label">Servers</div>

      <div className="server-list">
        {servers.map((s) => {
          const isActive = connected && serverName === s.name;
          return (
            <div key={s.id} className={`server-card${isActive ? ' active' : ''}`}>
              <div className="server-card-top">
                <span className={`status-dot${isActive ? ' on' : ''}`} />
                <div className="server-info">
                  <div className="server-name">{s.name}</div>
                  <div className="server-addr">
                    {s.host}:{s.port}
                  </div>
                  <div className="server-user">{s.user}</div>
                </div>
              </div>
              <button
                className={`server-action-btn${isActive ? ' danger' : ''}`}
                disabled={connLoading}
                onClick={() => (isActive ? onDisconnect() : onConnect(s.name))}
              >
                {connLoading && serverName === s.name
                  ? '...'
                  : isActive
                    ? 'Disconnect'
                    : 'Connect'}
              </button>
            </div>
          );
        })}
        {servers.length === 0 && (
          <div className="server-empty">No servers yet</div>
        )}
      </div>

      <button className="add-server-btn" onClick={onAddServer}>
        + Add Server
      </button>

      {connError && <div className="sidebar-error">{connError}</div>}

      <div className="sidebar-section-label">Local</div>
      <div className="server-card active">
        <div className="server-card-top">
          <span className="status-dot on" />
          <div className="server-info">
            <div className="server-name">This PC</div>
            <div className="server-addr">Windows</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
