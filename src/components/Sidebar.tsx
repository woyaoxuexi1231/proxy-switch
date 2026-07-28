import { useState } from 'react';
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
    <aside className="sidebar">
      <div className="sidebar-header">
        <span className="sidebar-logo">🔌 Proxy Switch</span>
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
              <div className="server-card-actions">
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
                <div className="server-card-mini-btns">
                  <button
                    className="mini-btn"
                    title="Edit server"
                    onClick={() => onEditServer(s)}
                  >
                    ✏️
                  </button>
                  <button
                    className={`mini-btn${confirmDelete === s.name ? ' danger' : ''}`}
                    title={confirmDelete === s.name ? 'Click again to confirm' : 'Delete server'}
                    onClick={() => handleDelete(s.name)}
                    onBlur={() => setConfirmDelete(null)}
                  >
                    {confirmDelete === s.name ? '⚠️' : '🗑️'}
                  </button>
                </div>
              </div>
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
            <div className="server-name">🖥 This PC</div>
            <div className="server-addr">Windows</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
