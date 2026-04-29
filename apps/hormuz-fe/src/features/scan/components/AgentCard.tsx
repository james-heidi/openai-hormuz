import { CheckCircle2, Circle, LoaderCircle, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { AgentUpdate } from '../types'

type AgentCardProps = {
  agent: AgentUpdate
}

const STATUS_CLASS = {
  idle: 'text-zinc-400',
  running: 'text-blue-600',
  done: 'text-emerald-600',
  error: 'text-red-600',
}

export function AgentCard({ agent }: AgentCardProps) {
  const Icon =
    agent.status === 'done'
      ? CheckCircle2
      : agent.status === 'error'
        ? XCircle
        : agent.status === 'running'
          ? LoaderCircle
          : Circle

  return (
    <article className="rounded-lg border border-zinc-200 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="truncate text-sm font-semibold text-zinc-950">{agent.agent}</h2>
          <p className="mt-1 truncate text-sm text-zinc-500">{agent.message}</p>
        </div>
        <Icon
          size={20}
          aria-hidden="true"
          className={cn(STATUS_CLASS[agent.status], agent.status === 'running' && 'animate-spin')}
        />
      </div>
      <div className="mt-4 h-2 overflow-hidden rounded-full bg-zinc-100">
        <div
          className="h-full rounded-full bg-zinc-950 transition-all"
          style={{ width: `${agent.progress}%` }}
        />
      </div>
    </article>
  )
}

