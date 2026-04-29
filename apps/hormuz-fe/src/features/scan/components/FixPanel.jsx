import { useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import clsx from 'clsx';
import DiffView from '../../../components/ui/DiffView';

const isPatch = (r) => r?.metadata?.kind === 'patch';
const isFixable = (r) =>
  r?.metadata?.kind !== 'patch' &&
  Array.isArray(r?.actions) &&
  r.actions.some((a) => a.actionId === 'auto-fix');

export default function FixPanel({ results, runId, onFixAll, status }) {
  const fixableCount = useMemo(
    () => (Array.isArray(results) ? results.filter(isFixable).length : 0),
    [results],
  );

  const patches = useMemo(
    () => (Array.isArray(results) ? results.filter(isPatch) : []),
    [results],
  );

  const [expandedId, setExpandedId] = useState(null);

  // Auto-expand the first patch as it streams in.
  useEffect(() => {
    if (patches.length > 0 && expandedId === null) {
      setExpandedId(patches[0].id);
    }
  }, [patches, expandedId]);

  const phase =
    patches.length > 0
      ? 'streaming'
      : status === 'fixing'
        ? 'fixing'
        : 'idle';

  return (
    <section className="glass-panel-soft theme-transition rounded-lg p-4">
      <header className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-medium text-text">Auto-fix</h2>
          <p className="mt-0.5 text-[11px] text-text-dim">
            {phase === 'idle' &&
              (fixableCount > 0
                ? `${fixableCount} ${fixableCount === 1 ? 'violation' : 'violations'} can be auto-fixed by Codex.`
                : 'Run a scan first — fixes appear here once violations are detected.')}
            {phase === 'fixing' && 'Codex subagents are writing patches in parallel worktrees…'}
            {phase === 'streaming' &&
              `${patches.length} ${patches.length === 1 ? 'patch' : 'patches'} generated. Click a row to view the diff.`}
          </p>
        </div>
        <button
          type="button"
          disabled={!runId || fixableCount === 0 || phase !== 'idle'}
          onClick={() => onFixAll?.()}
          className={clsx(
            'glass-primary theme-transition shrink-0 rounded-md px-4 py-2 text-sm font-semibold',
            'hover:-translate-y-0.5 hover:brightness-110 focus:outline-none focus:ring-2 focus:ring-accent/40',
            (!runId || fixableCount === 0 || phase !== 'idle') &&
              'cursor-not-allowed opacity-40',
          )}
        >
          {phase === 'fixing'
            ? 'Fixing…'
            : phase === 'streaming'
              ? 'Done'
              : `Auto-fix all (${fixableCount})`}
        </button>
      </header>

      {patches.length > 0 && (
        <ul className="mt-4 flex flex-col gap-2">
          <AnimatePresence initial={false}>
            {patches.map((p) => {
              const isOpen = expandedId === p.id;
              const file = p.metadata?.file ?? p.location ?? 'patch';
              return (
                <motion.li
                  key={p.id}
                  layout
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2, ease: 'easeOut' }}
                  className="glass-subpanel theme-transition overflow-hidden rounded-lg"
                >
                  <button
                    type="button"
                    onClick={() => setExpandedId(isOpen ? null : p.id)}
                    className="theme-transition flex w-full items-center justify-between gap-3 px-3 py-2 text-left hover:bg-surface-2/70"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-xs font-medium text-text">
                        {p.title ?? 'Patch'}
                      </div>
                      <div className="truncate font-mono text-[10px] text-text-dim">
                        {file}
                      </div>
                    </div>
                    <span className="shrink-0 font-mono text-[10px] text-text-dim">
                      {isOpen ? '−' : '+'}
                    </span>
                  </button>
                  <AnimatePresence initial={false}>
                    {isOpen && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2, ease: 'easeOut' }}
                      >
                        <div className="border-t border-border p-3">
                          <DiffView
                            lines={p.metadata?.diffLines}
                            file={file}
                          />
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.li>
              );
            })}
          </AnimatePresence>
        </ul>
      )}
    </section>
  );
}
