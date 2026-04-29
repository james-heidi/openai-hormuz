import { ShieldCheck } from 'lucide-react'
import type { ScanSummary } from '../types'

type ComplianceScoreProps = {
  summary: ScanSummary | null
  running: boolean
}

export function ComplianceScore({ summary, running }: ComplianceScoreProps) {
  const score = summary?.score ?? 100
  const total = summary?.total_findings ?? 0

  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-medium text-zinc-500">Compliance score</h2>
          <div className="mt-2 flex items-end gap-2">
            <span className="text-5xl font-semibold tracking-normal">{score}</span>
            <span className="pb-2 text-sm text-zinc-500">/ 100</span>
          </div>
        </div>
        <div className="grid h-12 w-12 place-items-center rounded-md bg-emerald-50 text-emerald-700">
          <ShieldCheck size={24} aria-hidden="true" />
        </div>
      </div>
      <div className="mt-5 grid grid-cols-4 gap-2 text-sm">
        <Metric label="Critical" value={summary?.counts_by_severity.critical ?? 0} />
        <Metric label="High" value={summary?.counts_by_severity.high ?? 0} />
        <Metric label="Medium" value={summary?.counts_by_severity.medium ?? 0} />
        <Metric label="Total" value={total} />
      </div>
      {running ? <p className="mt-4 text-sm text-zinc-500">Scan running</p> : null}
    </section>
  )
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-zinc-200 bg-zinc-50 p-3">
      <div className="text-lg font-semibold">{value}</div>
      <div className="text-xs text-zinc-500">{label}</div>
    </div>
  )
}

