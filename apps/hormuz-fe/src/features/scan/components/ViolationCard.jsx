import clsx from 'clsx';
import { tone } from '../lib/severity';
import RegulationBadge from '../../../components/ui/RegulationBadge';

const AGENT_LABELS = {
  'pii-scanner': 'PII Scanner',
  'api-auditor': 'API Auditor',
  'auth-checker': 'Auth Checker',
};

function ClausePanel({
  kind,
  badge,
  badgeHref,
  title,
  summary,
  requirement,
  fine,
  divider = false,
}) {
  return (
    <div className={clsx('min-w-0', divider && 'md:border-l md:border-border md:pl-4')}>
      <div className="flex flex-col gap-2">
        <RegulationBadge kind={kind} label={badge} href={badgeHref} />
        {fine && (
          <span className="text-[10px] font-semibold uppercase tracking-wider text-text-dim">
            {fine}
          </span>
        )}
      </div>
      {title && <div className="text-[12px] font-medium text-text">{title}</div>}
      {summary && (
        <p className="line-clamp-3 text-[11px] leading-relaxed text-text-dim">
          {summary}
        </p>
      )}
      {requirement && requirement !== summary && (
        <p className="line-clamp-3 text-[11px] leading-relaxed text-text-dim">
          {requirement}
        </p>
      )}
    </div>
  );
}

function locationFor(result) {
  if (result.location) return result.location;
  if (!result.file_path) return null;
  return result.line ? `${result.file_path}:${result.line}` : result.file_path;
}

function metadataFor(result) {
  const metadata = result.metadata ?? {};
  const regulations = Array.isArray(result.regulations) ? result.regulations : [];
  return {
    metadata,
    gdpr: metadata.gdpr ?? regulations.find((r) => r.framework === 'GDPR'),
    app: metadata.app ?? regulations.find((r) => r.framework === 'APP'),
  };
}

function regulationClause(regulation, fallback) {
  return regulation?.article ?? regulation?.principle ?? regulation?.clause ?? fallback;
}

function regulationFine(regulation) {
  return regulation?.fine ?? regulation?.max_penalty;
}

export default function ViolationCard({ result, onAction, variant = 'default' }) {
  if (!result) return null;
  const sev = result.severity;
  const { metadata: m, gdpr, app } = metadataFor(result);
  const featured = variant === 'featured';
  const location = locationFor(result);
  const violationCode = m.violationCode ?? result.violation_type;
  const agentLabel = AGENT_LABELS[result.agentId] ?? result.agent ?? result.agentId;

  return (
    <article className={featured ? 'min-w-0' : 'glass-panel theme-transition rounded-lg p-4'}>
      <header className="flex items-start justify-between gap-3">
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
            <h3 className={clsx('min-w-0 truncate font-medium text-text', featured ? 'text-lg' : 'text-sm')}>
              {result.title}
            </h3>
          </div>
          {location && (
            <div className="mt-1 truncate font-mono text-[11px] text-text-dim">
              {location}
            </div>
          )}
          {result.description && (
            <p className={clsx('mt-3 line-clamp-2 leading-relaxed text-text-dim', featured ? 'text-sm' : 'text-xs')}>
              {result.description}
            </p>
          )}
        </div>
        <div className="shrink-0 text-right">
          <div className="text-[10px] uppercase tracking-wider text-text-dim/80">
            {agentLabel}
          </div>
          {violationCode && (
            <div className="mt-0.5 font-mono text-[10px] text-text-dim/70">
              {violationCode}
            </div>
          )}
        </div>
      </header>

      {(gdpr || app) && (
        <div className="mt-4 grid grid-cols-1 gap-4 border-t border-border pt-4 md:grid-cols-2">
          {gdpr && (
            <ClausePanel
              kind="gdpr"
              badge={`GDPR · ${regulationClause(gdpr, 'GDPR')}`}
              badgeHref={gdpr.url}
              title={gdpr.title}
              summary={gdpr.summary}
              requirement={gdpr.requirement}
              fine={regulationFine(gdpr)}
            />
          )}
          {app && (
            <ClausePanel
              kind="app"
              badge={`AU Privacy · ${regulationClause(app, 'APP')}`}
              badgeHref={app.url}
              title={app.title}
              summary={app.summary}
              requirement={app.requirement}
              fine={regulationFine(app)}
              divider={Boolean(gdpr)}
            />
          )}
        </div>
      )}

      {result.regulation_warning && (
        <p className="mt-4 border-t border-border pt-3 text-[11px] leading-relaxed text-warn">
          {result.regulation_warning}
        </p>
      )}

      {Array.isArray(result.actions) && result.actions.length > 0 && (
        <footer className="mt-4 flex flex-wrap gap-2 border-t border-border pt-4">
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
        </footer>
      )}
    </article>
  );
}
