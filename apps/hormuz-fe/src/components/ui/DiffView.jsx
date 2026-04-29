import clsx from 'clsx';

/**
 * Renders a unified diff from a list of pre-rendered lines.
 * Backend is responsible for producing the line-by-line classification —
 * we only present.
 *
 * Each line is `{ type: '+' | '-' | ' ', text: string }`.
 */

const LINE_STYLES = {
  '+': 'bg-good/10 text-good border-l-2 border-good/60',
  '-': 'bg-bad/10 text-bad border-l-2 border-bad/60',
  ' ': 'bg-transparent text-text-dim border-l-2 border-transparent',
};

export default function DiffView({ lines, file, maxHeight = 280 }) {
  if (!Array.isArray(lines) || lines.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-border p-3 text-xs text-text-dim">
        No diff available.
      </div>
    );
  }

  return (
    <div className="theme-transition overflow-hidden rounded-md border border-border/60 bg-code-bg shadow-inner">
      {file && (
        <div className="border-b border-white/10 bg-white/5 px-3 py-1.5 font-mono text-[11px] text-slate-300">
          {file}
        </div>
      )}
      <div
        className="overflow-auto font-mono text-[12px] leading-relaxed"
        style={{ maxHeight }}
      >
        {lines.map((line, i) => (
          <div
            key={i}
            className={clsx(
              'flex gap-2 px-3 py-0.5 whitespace-pre',
              LINE_STYLES[line.type] ?? LINE_STYLES[' '],
            )}
          >
            <span className="w-3 shrink-0 select-none text-text-dim/70">
              {line.type === '+' ? '+' : line.type === '-' ? '−' : ' '}
            </span>
            <span className="flex-1">{line.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
