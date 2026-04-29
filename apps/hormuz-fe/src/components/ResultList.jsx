import { useMemo } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import ResultItem from './ResultItem';
import { sortBySeverity } from '../features/scan/lib/severity';

const defaultRenderItem = (result, onAction) => (
  <ResultItem result={result} onAction={onAction} />
);

export default function ResultList({
  results,
  onAction,
  emptyState,
  renderItem = defaultRenderItem,
  title = 'Results',
}) {
  const sorted = useMemo(() => {
    if (!Array.isArray(results)) return [];
    return [...results].sort(sortBySeverity);
  }, [results]);

  return (
    <section className="flex flex-col">
      <header className="mb-3 flex items-baseline justify-between">
        <h2 className="text-sm font-medium text-text">{title}</h2>
        <span className="font-mono text-[11px] text-text-dim">
          {sorted.length} {sorted.length === 1 ? 'item' : 'items'}
        </span>
      </header>

      {sorted.length === 0 ? (
        <div className="glass-subpanel theme-transition rounded-lg border-dashed p-6 text-center text-sm text-text-dim shadow-none">
          {emptyState ?? 'No results yet. Trigger a run to populate the list.'}
        </div>
      ) : (
        <ul className="flex flex-col gap-3">
          <AnimatePresence initial={false}>
            {sorted.map((r) => (
              <motion.li
                key={r.id}
                layout
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.25, ease: 'easeOut' }}
              >
                {renderItem(r, onAction)}
              </motion.li>
            ))}
          </AnimatePresence>
        </ul>
      )}
    </section>
  );
}
