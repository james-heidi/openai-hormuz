import { useMemo } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import clsx from 'clsx';
import ResultList from '../../../components/ResultList';
import ViolationCard from './ViolationCard';
import { sortBySeverity, tone } from '../lib/severity';

const isViolation = (r) => r?.metadata?.kind !== 'patch';

function clauseLabel(regulation, fallback) {
  return regulation?.clause ?? regulation?.article ?? regulation?.principle ?? fallback;
}

export default function ViolationList({
  results,
  onAction,
  selectedId,
  onSelect,
  compact = false,
}) {
  const violations = useMemo(
    () => (Array.isArray(results) ? results.filter(isViolation).sort(sortBySeverity) : []),
    [results],
  );

  if (compact) {
    return (
      <section className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="mb-3 flex shrink-0 items-baseline justify-between">
          <h2 className="text-sm font-medium text-text">Violation List</h2>
          <span className="font-mono text-[11px] text-text-dim">
            {violations.length} {violations.length === 1 ? 'item' : 'items'}
          </span>
        </header>

        {violations.length === 0 ? (
          <div className="glass-subpanel theme-transition rounded-lg border-dashed p-6 text-center text-sm text-text-dim shadow-none">
            No violations detected yet.
          </div>
        ) : (
          <ul className="glass-panel-soft theme-transition min-h-0 flex-1 overflow-y-auto rounded-lg">
            <AnimatePresence initial={false}>
              {violations.map((result) => {
                const selected = result.id === selectedId;
                const primaryAction = result.actions?.find((a) => a.actionId === 'auto-fix');
                return (
                  <motion.li
                    key={result.id}
                    layout
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.2, ease: 'easeOut' }}
                    className="border-b border-border last:border-b-0"
                  >
                    <div
                      role="button"
                      tabIndex={0}
                      onClick={() => onSelect?.(result.id)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                          event.preventDefault();
                          onSelect?.(result.id);
                        }
                      }}
                      className={clsx(
                        'theme-transition grid w-full cursor-pointer grid-cols-1 gap-3 px-4 py-3 text-left focus:outline-none focus:ring-2 focus:ring-inset focus:ring-accent/40 md:grid-cols-[112px_1fr_128px_96px]',
                        selected ? 'bg-accent/10' : 'hover:bg-surface-2/55',
                      )}
                    >
                      <div className="flex items-center gap-2">
                        {result.severity && (
                          <span
                            className={clsx(
                              'rounded-md border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
                              tone(result.severity),
                            )}
                          >
                            {result.severity}
                          </span>
                        )}
                      </div>
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium text-text">
                          {result.title}
                        </div>
                        <div className="mt-0.5 truncate font-mono text-[11px] text-text-dim">
                          {result.location}
                        </div>
                      </div>
                      <div className="min-w-0 font-mono text-[11px] text-text-dim">
                        <div className="truncate">
                          {clauseLabel(result.metadata?.gdpr, 'GDPR')}
                        </div>
                        <div className="truncate">
                          {clauseLabel(result.metadata?.app, 'APP')}
                        </div>
                      </div>
                      <div className="flex items-center md:justify-end">
                        {primaryAction && (
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              onAction?.(primaryAction.actionId, result.id);
                            }}
                            className="glass-control theme-transition rounded-md px-2 py-1 text-xs text-text hover:border-accent/50 hover:text-accent"
                          >
                            {primaryAction.label}
                          </button>
                        )}
                      </div>
                    </div>
                  </motion.li>
                );
              })}
            </AnimatePresence>
          </ul>
        )}
      </section>
    );
  }

  return (
    <ResultList
      title="Violations"
      results={violations}
      onAction={onAction}
      renderItem={(r, oa) => <ViolationCard result={r} onAction={oa} />}
      emptyState="No violations detected yet. Trigger a scan to see findings here."
    />
  );
}
