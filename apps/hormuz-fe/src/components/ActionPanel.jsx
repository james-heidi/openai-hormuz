import { useState } from 'react';
import clsx from 'clsx';

export default function ActionPanel({
  disabled = false,
  onRun,
  label = 'Input',
  placeholder = 'Enter target...',
  buttonLabel = 'Run',
  helperText,
}) {
  const [input, setInput] = useState('');

  const submit = (e) => {
    e?.preventDefault();
    if (disabled) return;
    onRun?.(input.trim());
  };

  const onKeyDown = (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') submit(e);
  };

  return (
    <form onSubmit={submit} className="glass-panel-soft theme-transition flex flex-col gap-3 rounded-lg p-4">
      <label className="flex flex-col gap-2">
        <span className="text-xs font-medium uppercase tracking-wider text-text-dim">{label}</span>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={disabled}
          placeholder={placeholder}
          className={clsx(
            'glass-control theme-transition rounded-md px-3 py-2 text-sm text-text placeholder:text-text-dim/60',
            'focus:border-accent/60 focus:outline-none focus:ring-2 focus:ring-accent/30',
            disabled && 'opacity-60',
          )}
        />
      </label>

      <button
        type="submit"
        disabled={disabled}
        className={clsx(
          'glass-primary theme-transition rounded-md px-4 py-2 text-sm font-semibold',
          'hover:-translate-y-0.5 hover:brightness-110 focus:outline-none focus:ring-2 focus:ring-accent/40',
          disabled && 'cursor-not-allowed opacity-60',
        )}
      >
        {buttonLabel}
      </button>

      {helperText && (
        <p className="text-[11px] leading-relaxed text-text-dim">{helperText}</p>
      )}
    </form>
  );
}
