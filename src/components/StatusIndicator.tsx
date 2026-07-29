import { getProxyState } from '../types';
import type { ProxyStatus } from '../types';

interface Props {
  status: ProxyStatus | null;
  loading: boolean;
}

export function StatusIndicator({ status, loading }: Props) {
  if (loading) {
    return (
      <span className="proxy-status-text status-loading">
        ⟳ Detecting...
      </span>
    );
  }

  if (!status) {
    return (
      <span className="proxy-status-text status-muted">
        — Not checked
      </span>
    );
  }

  const state = getProxyState(status);

  if (state === 'not_installed') {
    return (
      <span className="proxy-status-text status-not-installed">
        ✕ NOT INSTALLED
      </span>
    );
  }

  if (state === 'not_started') {
    return (
      <span className="proxy-status-text status-not-started">
        ◐ NOT STARTED
      </span>
    );
  }

  // state === 'started'
  const proxy = status.current_https_proxy || status.current_http_proxy;
  return (
    <span className="proxy-status-text status-started">
      ● ENABLED{proxy ? ` — ${proxy}` : ''}
    </span>
  );
}
