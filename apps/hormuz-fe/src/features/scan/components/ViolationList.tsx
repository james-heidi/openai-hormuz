import type { Finding } from '../types'
import { ViolationCard } from './ViolationCard'

type ViolationListProps = {
  findings: Finding[]
}

export function ViolationList({ findings }: ViolationListProps) {
  return (
    <section className="rounded-lg border border-zinc-200 bg-white">
      <div className="border-b border-zinc-200 px-5 py-4">
        <h2 className="text-sm font-semibold text-zinc-950">Findings</h2>
      </div>
      <div className="grid gap-3 p-4">
        {findings.length ? (
          findings.map((finding) => <ViolationCard key={finding.id} finding={finding} />)
        ) : (
          <div className="rounded-md border border-dashed border-zinc-300 p-8 text-center text-sm text-zinc-500">
            No findings
          </div>
        )}
      </div>
    </section>
  )
}

