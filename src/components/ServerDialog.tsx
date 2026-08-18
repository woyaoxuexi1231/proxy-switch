import { useState, useEffect } from 'react';
import { addServer, updateServer } from '../utils/invoke';
import type { Server, ServerInput } from '../types';
import { X } from 'lucide-react';

interface Props {
  server: Server | null;
  onSaved: () => void;
  onCancel: () => void;
}

export function ServerDialog({ server, onSaved, onCancel }: Props) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onCancel]);

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
      ssh_key_path:
        authMode === 'key' ? sshKeyPath.trim() || undefined : undefined,
      password: authMode === 'password' ? password || undefined : undefined,
      description: description.trim(),
    };
    setSaving(true);
    try {
      const result = server ? await updateServer(input) : await addServer(input);
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
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/25 px-4 backdrop-blur-[2px]"
      onClick={onCancel}
    >
      <div
        className="w-full max-w-[440px] overflow-hidden rounded-[28px] border border-slate-200/60 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.12)]"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={server ? 'Edit Server' : 'Add Server'}
      >
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h2 className="text-[16px] font-semibold text-[#0a1b33]">
            {server ? 'Edit Server' : 'Add Server'}
          </h2>
          <button
            type="button"
            className="inline-flex h-8 w-8 items-center justify-center rounded-full text-slate-400 hover:bg-slate-100 hover:text-[#0a1b33]"
            onClick={onCancel}
            aria-label="Close"
          >
            <X className="h-4 w-4" strokeWidth={2} />
          </button>
        </div>

        <div className="space-y-3 px-5 py-4">
          <Field label="Name" value={name} placeholder="my-ubuntu" onChange={setName} />
          <Field label="Host" value={host} placeholder="192.168.1.100" onChange={setHost} />
          <div className="grid grid-cols-2 gap-3">
            <Field label="Port" value={port} placeholder="22" onChange={setPort} type="number" />
            <Field label="User" value={user} placeholder="root" onChange={setUser} />
          </div>

          <fieldset>
            <legend className="mb-1.5 text-[11px] font-medium text-slate-500">
              Auth Method
            </legend>
            <div className="flex gap-4">
              <label className="inline-flex items-center gap-2 text-[12px] text-[#0a1b33]">
                <input
                  type="radio"
                  name="auth_mode"
                  checked={authMode === 'key'}
                  onChange={() => setAuthMode('key')}
                />
                SSH Key
              </label>
              <label className="inline-flex items-center gap-2 text-[12px] text-[#0a1b33]">
                <input
                  type="radio"
                  name="auth_mode"
                  checked={authMode === 'password'}
                  onChange={() => setAuthMode('password')}
                />
                Password
              </label>
            </div>
          </fieldset>

          {authMode === 'key' ? (
            <Field
              label="SSH Key Path"
              value={sshKeyPath}
              placeholder="~/.ssh/id_rsa"
              onChange={setSshKeyPath}
            />
          ) : (
            <Field
              label="Password"
              value={password}
              placeholder="••••••••"
              onChange={setPassword}
              type="password"
            />
          )}

          <Field
            label="Description"
            value={description}
            placeholder="Home server"
            onChange={setDescription}
          />

          {error && (
            <div className="rounded-xl bg-red-50 px-3 py-2 text-[12px] text-red-700">
              {error}
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 border-t border-slate-100 px-5 py-4">
          <button
            type="button"
            className="rounded-full border border-slate-200/60 bg-white px-4 py-2 text-[12px] font-semibold text-[#0a1b33] shadow-sm hover:border-slate-300"
            onClick={onCancel}
          >
            Cancel
          </button>
          <button
            type="button"
            className="rounded-full bg-[#0a152d] px-4 py-2 text-[12px] font-semibold text-white disabled:opacity-40"
            onClick={() => void handleSave()}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  placeholder,
  onChange,
  type = 'text',
}: {
  label: string;
  value: string;
  placeholder: string;
  onChange: (v: string) => void;
  type?: string;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[11px] font-medium text-slate-500">{label}</span>
      <input
        className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-[13px] text-[#0a1b33] outline-none transition-colors placeholder:text-slate-400 focus:border-slate-400 focus:bg-white"
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}
