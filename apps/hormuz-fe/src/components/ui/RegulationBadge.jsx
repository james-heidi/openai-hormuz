import clsx from 'clsx';

/**
 * Small pill that names a specific clause. The kind controls the dot color
 * so GDPR (EU blue) and APP (AU gold) are visually distinguishable at a
 * glance. The label text is whatever string the caller passes.
 */
const KINDS = {
  gdpr: { dot: 'bg-gdpr', text: 'text-gdpr' },
  app: { dot: 'bg-app', text: 'text-app' },
  default: { dot: 'bg-text-dim', text: 'text-text-dim' },
};

export default function RegulationBadge({ kind = 'default', label, href }) {
  const cfg = KINDS[kind] ?? KINDS.default;
  const inner = (
    <span
      className={clsx(
        'glass-control theme-transition inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider',
        cfg.text,
      )}
    >
      <span className={clsx('h-1.5 w-1.5 rounded-full', cfg.dot)} />
      {label}
    </span>
  );

  if (href) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noreferrer noopener"
        className="transition-opacity hover:opacity-80"
      >
        {inner}
      </a>
    );
  }
  return inner;
}
