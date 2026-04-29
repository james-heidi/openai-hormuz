import type { AgentUpdate } from '../types'
import { AgentCard } from './AgentCard'

type AgentStatusBoardProps = {
  agents: AgentUpdate[]
}

export function AgentStatusBoard({ agents }: AgentStatusBoardProps) {
  const visibleAgents = agents.length
    ? agents
    : ['PII Scanner', 'API Auditor', 'Auth Checker'].map((agent) => ({
        agent,
        status: 'idle' as const,
        message: 'Waiting',
        progress: 0,
      }))

  return (
    <div className="grid gap-3">
      {visibleAgents.map((agent) => (
        <AgentCard key={agent.agent} agent={agent} />
      ))}
    </div>
  )
}

