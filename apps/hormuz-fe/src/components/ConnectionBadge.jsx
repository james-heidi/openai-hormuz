import clsx from 'clsx';
import { WS_STATUS } from '../features/scan/hooks/useWebSocket';

const COPY = {
  [WS_STATUS.OPEN]: { label: 'Connected', dot: 'bg-good', text: 'text-good' },
  [WS_STATUS.CONNECTING]: { label: 'Connecting', dot: 'bg-warn animate-pulse-dot', text: 'text-warn' },
  [WS_STATUS.CLOSED]: { label: 'Disconnected', dot: 'bg-bad', text: 'text-bad' },
  [WS_STATUS.MOCK]: { label: 'MOCK', dot: 'bg-accent', text: 'text-accent' },
};

export default function ConnectionBadge({ status, retryCount = 0, maxRetries = 5 }) {
  const cfg = COPY[status] ?? COPY[WS_STATUS.CLOSED];
  const showRetry = status === WS_STATUS.CONNECTING && retryCount > 0;

  return (
    <div className="glass-control theme-transition inline-flex items-center gap-2 rounded-full px-2.5 py-1">
      <span className={clsx('h-1.5 w-1.5 rounded-full', cfg.dot)} />
      <span className={clsx('text-[11px] font-medium uppercase tracking-wider', cfg.text)}>
        {cfg.label}
      </span>
      {showRetry && (
        <span className="font-mono text-[10px] text-text-dim">
          {retryCount}/{maxRetries}
        </span>
      )}
    </div>
  );
}
