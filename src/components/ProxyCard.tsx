import { useState, useEffect, useCallback, useRef } from 'react';
import { useProxyStatus } from '../hooks/useProxyStatus';
import { StatusIndicator } from './StatusIndicator';
import { ManualGuide } from './ManualGuide';
import type { ComponentId, ProxyConfig } from '../types';
import './ProxyCard.css';

interface Props {
  component: ComponentId;
  label: string;
  isRemote: boolean;
  connected: boolean;
}

export function ProxyCard({ component, label, isRemote, connected }: Props) {
  const { status, loading, message, refresh, enable, disable, setMessage } =
    useProxyStatus(component, isRemote);
  const [expanded, setExpanded] = useState(false);

  const [httpProxy, setHttpProxy] = useState('');
  const [httpsProxy, setHttpsProxy] = useState('');
  const [noProxy, setNoProxy] = useState('');
  const [mirror, setMirror] = useState('');

  const needsSudo = ['system_proxy', 'apt', 'docker_remote'].includes(component);
  const supportsMirror = ['apt', 'docker_remote', 'npm_remote', 'maven_remote'].includes(component);

  // Auto-detect on mount for local components (always "connected")
  useEffect(() => {
    if (!isRemote) {
      refresh();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-detect for remote components when SSH connects
  const prevConnected = useRef(connected);
  useEffect(() => {
    if (isRemote && connected && !prevConnected.current) {
      refresh();
    }
    prevConnected.current = connected;
  }, [isRemote, connected]); // eslint-disable-line react-hooks/exhaustive-deps

  // Fill form from detected status
  useEffect(() => {
    if (status?.enabled) {
      if (status.current_http_proxy && !httpProxy) setHttpProxy(status.current_http_proxy);
      if (status.current_https_proxy && !httpsProxy) setHttpsProxy(status.current_https_proxy);
      if (status.current_no_proxy && !noProxy) setNoProxy(status.current_no_proxy);
      if (status.current_mirror && !mirror) setMirror(status.current_mirror);
    }
  }, [status]);

  const handleRefresh = useCallback(() => {
    setMessage(null);
    refresh();
  }, [refresh, setMessage]);

  const handleEnable = useCallback(async () => {
    if (!httpProxy && !httpsProxy) {
      setMessage('At least one proxy URL is required.');
      return;
    }
    setMessage(null);
    const config: ProxyConfig = {
      http_proxy: httpProxy.trim(),
      https_proxy: httpsProxy.trim(),
      no_proxy: noProxy.trim(),
      mirror: mirror.trim(),
    };
    await enable(config);
  }, [httpProxy, httpsProxy, noProxy, mirror, enable, setMessage]);

  const handleDisable = useCallback(async () => {
    setMessage(null);
    await disable();
  }, [disable, setMessage]);

  const proxyDisplay = status?.current_https_proxy || status?.current_http_proxy || null;

  return (
    <div className={`proxy-card${expanded ? ' expanded' : ''}`}>
      {/* ── Header (always visible) ─────────────────────────────── */}
      <button
        className="proxy-card-header"
        onClick={() => {
          if (connected) setExpanded(!expanded);
        }}
        disabled={!connected}
        title={connected ? 'Click to expand' : 'Not connected'}
      >
        <div className="proxy-card-title">
          <StatusIndicator status={status} loading={loading} />
          <span className="proxy-card-label">{label}</span>
          {proxyDisplay && !status?.enabled === false && (
            <span className="proxy-card-value">{proxyDisplay}</span>
          )}
        </div>
        <span className={`proxy-card-chevron${expanded ? ' up' : ''}`}>
          {connected ? (expanded ? '▲' : '▼') : ''}
        </span>
      </button>

      {/* ── Expanded content ────────────────────────────────────── */}
      {expanded && (
        <div className="proxy-card-body">
          {/* Config files */}
          {status?.config_files && status.config_files.length > 0 && (
            <div className="proxy-files">
              <div className="proxy-files-label">Config files:</div>
              {status.config_files.map((f, i) => (
                <code key={i} className="proxy-file-path">
                  {f}
                </code>
              ))}
            </div>
          )}

          {/* Manual guide */}
          {status?.manual_setup_steps && (
            <ManualGuide steps={status.manual_setup_steps} />
          )}

          {/* Message */}
          {message && (
            <div
              className={`proxy-message${message.toLowerCase().includes('fail') || message.toLowerCase().includes('error')
                  ? ' error'
                  : ' ok'
                }`}
            >
              {message}
            </div>
          )}

          {/* Input fields */}
          <div className="proxy-inputs">
            <div className="proxy-field">
              <label className="proxy-field-label">HTTP Proxy</label>
              <input
                className="proxy-input"
                type="text"
                placeholder="http://127.0.0.1:7890"
                value={httpProxy}
                onChange={(e) => setHttpProxy(e.target.value)}
              />
            </div>
            <div className="proxy-field">
              <label className="proxy-field-label">HTTPS Proxy</label>
              <input
                className="proxy-input"
                type="text"
                placeholder="http://127.0.0.1:7890"
                value={httpsProxy}
                onChange={(e) => setHttpsProxy(e.target.value)}
              />
            </div>
            <div className="proxy-field">
              <label className="proxy-field-label">No Proxy</label>
              <input
                className="proxy-input"
                type="text"
                placeholder="localhost,127.0.0.1,::1"
                value={noProxy}
                onChange={(e) => setNoProxy(e.target.value)}
              />
            </div>
            {supportsMirror && (
              <div className="proxy-field">
                <label className="proxy-field-label">Mirror URL</label>
                <input
                  className="proxy-input"
                  type="text"
                  placeholder="https://mirror.example.com"
                  value={mirror}
                  onChange={(e) => setMirror(e.target.value)}
                />
              </div>
            )}
          </div>

          {/* Action buttons */}
          <div className="proxy-actions">
            <button
              className="btn btn-primary"
              onClick={handleEnable}
              disabled={loading}
            >
              Apply
            </button>
            <button
              className="btn btn-danger-outline"
              onClick={handleDisable}
              disabled={loading || !status || !status.enabled}
            >
              Disable
            </button>
            <button
              className="btn btn-ghost"
              onClick={handleRefresh}
              disabled={loading}
            >
              ⟳ Refresh
            </button>
            {needsSudo && isRemote && (
              <span className="sudo-tag">sudo</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
