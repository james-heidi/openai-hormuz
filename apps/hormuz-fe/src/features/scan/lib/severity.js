/**
 * Severity ordering and presentation. Generic — no domain meaning attached.
 *
 * `RANK` lets us sort highest-first. `tone()` returns the tailwind classes
 * for a severity chip. A fork adding a domain layer can extend or remap
 * tones without touching this file (just call its own helper).
 */

export const SEVERITIES = ['critical', 'high', 'medium', 'low'];

export const RANK = Object.freeze({
  critical: 4,
  high: 3,
  medium: 2,
  low: 1,
});

const TONE = Object.freeze({
  critical: 'bg-bad/15 text-bad border-bad/30',
  high: 'bg-warn/15 text-warn border-warn/30',
  medium: 'bg-accent/15 text-accent border-accent/30',
  low: 'bg-text-dim/15 text-text-dim border-border',
});

export const tone = (severity) =>
  TONE[severity] ?? 'bg-text-dim/10 text-text-dim border-border';

export const sortBySeverity = (a, b) =>
  (RANK[b?.severity] ?? 0) - (RANK[a?.severity] ?? 0);
