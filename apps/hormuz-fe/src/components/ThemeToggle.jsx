import { useEffect, useState } from 'react';
import clsx from 'clsx';

const STORAGE_KEY = 'compliance-codex-theme';

function getInitialTheme() {
  if (typeof window === 'undefined') return 'light';
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === 'light' || stored === 'dark') return stored;
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light';
  } catch {
    return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
  }
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState(getInitialTheme);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle('dark', theme === 'dark');
    root.style.colorScheme = theme;
    try {
      window.localStorage.setItem(STORAGE_KEY, theme);
    } catch {}
  }, [theme]);

  return (
    <div className="glass-control theme-transition inline-flex rounded-full p-0.5">
      {['light', 'dark'].map((option) => {
        const active = theme === option;
        return (
          <button
            key={option}
            type="button"
            onClick={() => setTheme(option)}
            className={clsx(
              'theme-transition rounded-full px-2.5 py-1 text-[11px] font-medium uppercase tracking-wider',
              active
                ? 'glass-segment-active'
                : 'text-text-dim hover:text-text',
            )}
            aria-pressed={active}
          >
            {option}
          </button>
        );
      })}
    </div>
  );
}
