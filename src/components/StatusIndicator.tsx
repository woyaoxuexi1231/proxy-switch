import type { ProxyStatus } from '../types';

interface Props {
  status: ProxyStatus | null;
  loading: boolean;
}

export function StatusIndicator({ status, loading }: Props) {
  if (loading) {
    return (
      <span className="proxy-status-text" style={{ color: 'var(--text-muted)' }}>
        ⟳ detecting...
      </span>
    );
  }
  if (!status) {
    return (
      <span className="proxy-status-text" style={{ color: 'var(--text-muted)' }}>
        — not checked
      </span>
    );
  }
  if (!status.installed) {
    return (
      <span className="proxy-status-text" style={{ color: 'var(--text-muted)' }}>
        ⏭ NOT INSTALLED
      </span>
    );
  }
  if (status.enabled) {
    const proxy = status.current_https_proxy || status.current_http_proxy;
    return (
      <span className="proxy-status-text" style={{ color: 'var(--success)' }}>
        ● ENABLED{proxy ? ` — ${proxy}` : ''}
      </span>
    );
  }
  return (
    <span className="proxy-status-text" style={{ color: 'var(--text-secondary)' }}>
      ○ disabled
    </span>
  );
}
