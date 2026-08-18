import { getProxyState } from '../types';
import type { ProxyStatus } from '../types';
import { cn } from '../lib/cn';
import { LoaderCircle } from 'lucide-react';

interface Props {
  status: ProxyStatus | null;
  loading: boolean;
}

export function StatusIndicator({ status, loading }: Props) {
  if (loading) {
    return (
      <span className="inline-flex items-center gap-1.5 text-[12px] font-medium text-slate-400">
        <LoaderCircle className="h-3.5 w-3.5 animate-spin" strokeWidth={2} />
        Detecting...
      </span>
    );
  }

  if (!status) {
    return (
      <span className="text-[12px] font-medium text-slate-400">
        Not checked
      </span>
    );
  }

  const state = getProxyState(status);

  if (state === 'not_installed') {
    return (
      <span className="text-[12px] font-medium text-slate-400">
        NOT INSTALLED
      </span>
    );
  }

  if (state === 'not_started') {
    return (
      <span className="text-[12px] font-medium text-amber-600">
        NOT STARTED
      </span>
    );
  }

  return (
    <span
      className={cn(
        'text-[12px] font-medium text-emerald-600',
      )}
    >
      ENABLED
    </span>
  );
}
