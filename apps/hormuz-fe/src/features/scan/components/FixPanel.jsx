import { useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import clsx from 'clsx';
import DiffView from '../../../components/ui/DiffView';

const isPatch = (r) => r?.metadata?.kind === 'patch';
const isFixable = (r) =>
  r?.metadata?.kind !== 'patch' &&
  Array.isArray(r?.actions) &&
  r.actions.some((a) => a.actionId === 'auto-fix');

export default function FixPanel({
  results,
  runId,
  onFixAll,
  onAcceptPatch,
  acceptingPatchId,
  status,
}) {
  const patches = useMemo(
    () => (Array.isArray(results) ? results.filter(isPatch) : []),
    [results],
  );
  const patchedFindingIds = useMemo(
    () =>
      new Set(
        patches
          .filter((patch) => patch.metadata?.applied || patch.metadata?.accepted)
          .map((patch) => patch.metadata?.violationCode)
          .filter(Boolean),
      ),
    [patches],
  );
  const fixableCount = useMemo(
    () =>
      Array.isArray(results)
        ? results.filter((result) => isFixable(result) && !patchedFindingIds.has(result.id)).length
        : 0,
    [patchedFindingIds, results],
  );

  const [expandedId, setExpandedId] = useState(null);
  const hasAutoExpandedRef = useRef(false);

  // Auto-expand the first patch as it streams in.
  useEffect(() => {
    if (patches.length === 0) {
      hasAutoExpandedRef.current = false;
      if (expandedId !== null) setExpandedId(null);
      return;
    }
    if (!hasAutoExpandedRef.current && expandedId === null) {
      hasAutoExpandedRef.current = true;
      setExpandedId(patches[0].id);
    }
  }, [patches, expandedId]);

  useEffect(() => {
    const expandedPatch = patches.find((patch) => patch.id === expandedId);
    if (expandedPatch?.metadata?.applied || expandedPatch?.metadata?.accepted) {
      setExpandedId(null);
    }
  }, [patches, expandedId]);

  const phase =
    status === 'fixing'
      ? 'fixing'
      : patches.length > 0
        ? 'streaming'
        : 'idle';
  const canFixRemaining = runId && fixableCount > 0 && phase !== 'fixing';
  const fixAllLabel = patches.length > 0
    ? `Auto-fix remaining (${fixableCount})`
    : `Auto-fix all (${fixableCount})`;

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
              `${patches.length} ${patches.length === 1 ? 'patch' : 'patches'} generated. Review diffs, accept changes, or keep fixing remaining issues.`}
          </p>
        </div>
        <button
          type="button"
          disabled={!canFixRemaining}
          onClick={() => onFixAll?.()}
          className={clsx(
            'glass-primary theme-transition shrink-0 rounded-md px-4 py-2 text-sm font-semibold',
            'hover:-translate-y-0.5 hover:brightness-110 focus:outline-none focus:ring-2 focus:ring-accent/40',
            !canFixRemaining &&
              'cursor-not-allowed opacity-40',
          )}
        >
          {phase === 'fixing'
            ? 'Fixing…'
            : fixAllLabel}
        </button>
      </header>

      {patches.length > 0 && (
        <ul className="mt-4 flex flex-col gap-2">
          <AnimatePresence initial={false}>
            {patches.map((p) => {
              const isOpen = expandedId === p.id;
              const file = p.metadata?.file ?? p.location ?? 'patch';
              const accepted = p.metadata?.applied || p.metadata?.accepted;
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
                  <div className="theme-transition flex w-full items-center justify-between gap-3 px-3 py-2 hover:bg-surface-2/70">
                    <button
                      type="button"
                      onClick={() => setExpandedId(isOpen ? null : p.id)}
                      className="min-w-0 flex-1 text-left focus:outline-none"
                    >
                      <div className="truncate text-xs font-medium text-text">
                        {p.title ?? 'Patch'}
                      </div>
                      <div className="truncate font-mono text-[10px] text-text-dim">
                        {file}
                      </div>
                    </button>
                    {onAcceptPatch && (
                      <button
                        type="button"
                        disabled={
                          status === 'fixing' ||
                          accepted ||
                          acceptingPatchId === p.id
                        }
                        onClick={() => onAcceptPatch(p)}
                        className={clsx(
                          'theme-transition shrink-0 rounded-md border border-accent/35 px-2.5 py-1',
                          'text-[11px] font-semibold text-accent hover:border-accent hover:bg-accent/10',
                          'focus:outline-none focus:ring-2 focus:ring-accent/30',
                          (status === 'fixing' ||
                            accepted ||
                            acceptingPatchId === p.id) &&
                            'cursor-not-allowed opacity-50',
                        )}
                      >
                        {accepted
                          ? 'Accepted'
                          : acceptingPatchId === p.id
                            ? 'Accepting...'
                            : 'Accept'}
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => setExpandedId(isOpen ? null : p.id)}
                      className="shrink-0 font-mono text-[10px] text-text-dim focus:outline-none"
                      aria-label={isOpen ? 'Collapse patch' : 'Expand patch'}
                    >
                      {isOpen ? '−' : '+'}
                    </button>
                  </div>
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
