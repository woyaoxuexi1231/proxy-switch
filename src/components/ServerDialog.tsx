import { useState } from 'react';
import { addServer, updateServer } from '../utils/invoke';
import type { Server, ServerInput } from '../types';
import './ServerDialog.css';

interface Props {
  server: Server | null;
  onSaved: () => void;
  onCancel: () => void;
}

export function ServerDialog({ server, onSaved, onCancel }: Props) {
  const [name, setName] = useState(server?.name || '');
  const [host, setHost] = useState(server?.host || '');
  const [port, setPort] = useState(String(server?.port || 22));
  const [user, setUser] = useState(server?.user || 'root');
  const [authMode, setAuthMode] = useState<'key' | 'password'>(
    server?.auth_mode || 'key',
  );
  const [sshKeyPath, setSshKeyPath] = useState(server?.ssh_key_path || '');
  const [password, setPassword] = useState(server?.password || '');
  const [description, setDescription] = useState(server?.description || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    setError(null);
    if (!name.trim()) {
      setError('Server name is required.');
      return;
    }
    if (!host.trim()) {
      setError('Host is required.');
      return;
    }
    const portNum = parseInt(port, 10);
    if (isNaN(portNum) || portNum < 1 || portNum > 65535) {
      setError('Port must be between 1 and 65535.');
      return;
    }
    const input: ServerInput = {
      name: name.trim(),
      host: host.trim(),
      port: portNum,
      user: user.trim() || 'root',
      auth_mode: authMode,
      ssh_key_path: authMode === 'key' ? sshKeyPath.trim() || undefined : undefined,
      password: authMode === 'password' ? password || undefined : undefined,
      description: description.trim(),
    };
    setSaving(true);
    try {
      const result = server
        ? await updateServer(input)
        : await addServer(input);
      if (result.success) {
        onSaved();
      } else {
        setError(result.message);
      }
    } catch (e) {
      setError(String(e));
    }
    setSaving(false);
  };

  return (
    <div className="dialog-overlay" onClick={onCancel}>
      <div className="dialog" onClick={(e) => e.stopPropagation()}>
        <div className="dialog-header">
          <span className="dialog-title">
            {server ? 'Edit Server' : 'Add Server'}
          </span>
          <button className="dialog-close" onClick={onCancel}>
            ×
          </button>
        </div>
        <div className="dialog-body">
          <div className="dialog-field">
            <label>Name</label>
            <input
              className="dialog-input"
              type="text"
              placeholder="my-ubuntu"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="dialog-field">
            <label>Host</label>
            <input
              className="dialog-input"
              type="text"
              placeholder="192.168.1.100"
              value={host}
              onChange={(e) => setHost(e.target.value)}
            />
          </div>
          <div className="dialog-row">
            <div className="dialog-field">
              <label>Port</label>
              <input
                className="dialog-input"
                type="number"
                placeholder="22"
                value={port}
                onChange={(e) => setPort(e.target.value)}
              />
            </div>
            <div className="dialog-field">
              <label>User</label>
              <input
                className="dialog-input"
                type="text"
                placeholder="root"
                value={user}
                onChange={(e) => setUser(e.target.value)}
              />
            </div>
          </div>
          <div className="dialog-field">
            <label>Auth Method</label>
            <div className="dialog-radio-group">
              <label className="dialog-radio">
                <input
                  type="radio"
                  name="auth_mode"
                  checked={authMode === 'key'}
                  onChange={() => setAuthMode('key')}
                />
                SSH Key
              </label>
              <label className="dialog-radio">
                <input
                  type="radio"
                  name="auth_mode"
                  checked={authMode === 'password'}
                  onChange={() => setAuthMode('password')}
                />
                Password
              </label>
            </div>
          </div>
          {authMode === 'key' ? (
            <div className="dialog-field">
              <label>SSH Key Path</label>
              <input
                className="dialog-input"
                type="text"
                placeholder="~/.ssh/id_rsa"
                value={sshKeyPath}
                onChange={(e) => setSshKeyPath(e.target.value)}
              />
            </div>
          ) : (
            <div className="dialog-field">
              <label>Password</label>
              <input
                className="dialog-input"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          )}
          <div className="dialog-field">
            <label>Description</label>
            <input
              className="dialog-input"
              type="text"
              placeholder="Home server"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          {error && <div className="dialog-error">{error}</div>}
        </div>
        <div className="dialog-footer">
          <button className="btn" onClick={onCancel}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}
