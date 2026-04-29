import { motion } from 'framer-motion';
import clsx from 'clsx';

const STATUS_STYLES = {
  idle: {
    border: 'border-border',
    dot: 'bg-text-dim/40',
    label: 'text-text-dim',
    chip: 'Idle',
  },
  running: {
    border: 'border-warn/60',
    dot: 'bg-warn animate-pulse-dot',
    label: 'text-warn',
    chip: 'Running',
  },
  done: {
    border: 'border-good/50',
    dot: 'bg-good',
    label: 'text-good',
    chip: 'Done',
  },
  error: {
    border: 'border-bad/60',
    dot: 'bg-bad',
    label: 'text-bad',
    chip: 'Error',
  },
};

function CheckIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 8.5l3.5 3.5L13 4.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ErrorIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M4 4l8 8M12 4L4 12" strokeLinecap="round" />
    </svg>
  );
}

export default function AgentCard({ agent }) {
  const status = agent?.status ?? 'idle';
  const s = STATUS_STYLES[status] ?? STATUS_STYLES.idle;
  const progress = typeof agent?.progress === 'number' ? Math.max(0, Math.min(1, agent.progress)) : null;

  return (
    <motion.div
      layout
      className={clsx(
        'glass-subpanel theme-transition rounded-lg p-3',
        s.border,
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-medium text-text">
            {agent?.label ?? agent?.id ?? 'Agent'}
          </div>
          <div className="mt-0.5 truncate font-mono text-[11px] text-text-dim">
            {agent?.id}
          </div>
        </div>
        <div className={clsx('flex items-center gap-1.5 text-xs font-medium', s.label)}>
          <span className={clsx('h-2 w-2 rounded-full', s.dot)} />
          <span className="flex items-center gap-1">
            {status === 'done' && <CheckIcon />}
            {status === 'error' && <ErrorIcon />}
            {s.chip}
          </span>
        </div>
      </div>

      {progress !== null && status === 'running' && (
        <div className="mt-3 h-1 overflow-hidden rounded-full bg-surface-2/70">
          <motion.div
            className="h-full bg-warn"
            initial={{ width: 0 }}
            animate={{ width: `${progress * 100}%` }}
            transition={{ duration: 0.4, ease: 'easeOut' }}
          />
        </div>
      )}

      {agent?.message && (
        <div
          className={clsx(
            'mt-3 text-xs',
            status === 'error' ? 'text-bad/90' : 'text-text-dim',
          )}
        >
          {agent.message}
        </div>
      )}
    </motion.div>
  );
}
