import clsx from 'clsx';
import { tone } from '../features/scan/lib/severity';

export default function ResultItem({ result, onAction }) {
  if (!result) return null;
  const sev = result.severity;

  return (
    <div className="glass-panel theme-transition rounded-lg p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            {sev && (
              <span
                className={clsx(
                  'rounded-md border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
                  tone(sev),
                )}
              >
                {sev}
              </span>
            )}
            <h3 className="truncate text-sm font-medium text-text">
              {result.title}
            </h3>
          </div>
          {result.location && (
            <div className="mt-1 truncate font-mono text-[11px] text-text-dim">
              {result.location}
            </div>
          )}
          {result.description && (
            <p className="mt-2 text-xs leading-relaxed text-text-dim">
              {result.description}
            </p>
          )}
        </div>
        <div className="shrink-0 font-mono text-[10px] text-text-dim/70">
          {result.agentId}
        </div>
      </div>

      {Array.isArray(result.actions) && result.actions.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {result.actions.map((a) => (
            <button
              key={a.actionId}
              type="button"
              onClick={() => onAction?.(a.actionId, result.id)}
              className="glass-control theme-transition rounded-md px-2.5 py-1 text-xs text-text hover:border-accent/50 hover:text-accent focus:outline-none focus:ring-2 focus:ring-accent/40"
            >
              {a.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
