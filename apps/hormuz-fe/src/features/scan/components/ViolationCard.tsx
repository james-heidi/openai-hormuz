import { AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Finding, Severity } from '../types'

type ViolationCardProps = {
  finding: Finding
}

const SEVERITY_CLASS: Record<Severity, string> = {
  critical: 'bg-red-50 text-red-700 border-red-200',
  high: 'bg-amber-50 text-amber-700 border-amber-200',
  medium: 'bg-blue-50 text-blue-700 border-blue-200',
  low: 'bg-zinc-50 text-zinc-700 border-zinc-200',
}

export function ViolationCard({ finding }: ViolationCardProps) {
  return (
    <article className="rounded-lg border border-zinc-200 bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <AlertTriangle size={16} className="text-zinc-500" aria-hidden="true" />
            <h3 className="text-sm font-semibold text-zinc-950">{finding.title}</h3>
          </div>
          <p className="mt-1 text-sm text-zinc-600">{finding.description}</p>
        </div>
        <span
          className={cn(
            'rounded-md border px-2 py-1 text-xs font-medium uppercase',
            SEVERITY_CLASS[finding.severity],
          )}
        >
          {finding.severity}
        </span>
      </div>
      <div className="mt-3 rounded-md bg-zinc-50 p-3 font-mono text-xs text-zinc-700">
        {finding.file_path}
        {finding.line ? `:${finding.line}` : ''}
        {finding.snippet ? <div className="mt-2 break-words">{finding.snippet}</div> : null}
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {finding.regulations.map((regulation) => (
          <span
            key={`${regulation.framework}-${regulation.clause}`}
            className="rounded-md border border-zinc-200 bg-zinc-50 px-2 py-1 text-xs text-zinc-700"
          >
            {regulation.framework} {regulation.clause}
          </span>
        ))}
      </div>
      <p className="mt-3 text-sm text-zinc-600">{finding.recommendation}</p>
    </article>
  )
}

