export type Severity = 'critical' | 'high' | 'medium' | 'low'
export type AgentStatus = 'idle' | 'running' | 'done' | 'error'

export type RegulationRef = {
  framework: 'GDPR' | 'APP'
  clause: string
  title: string
  summary: string
  requirement: string
  max_penalty: string
  severity: Severity
}

export type Finding = {
  id: string
  violation_type: string
  agent: string
  category: string
  severity: Severity
  file_path: string
  line: number | null
  context: string | null
  title: string
  description: string
  snippet: string | null
  regulations: RegulationRef[]
  regulation_warning: string | null
  recommendation: string
  remediation_hint: string
}

export type ScanSummary = {
  score: number
  total_findings: number
  counts_by_severity: Record<Severity, number>
  findings: Finding[]
}

export type AgentUpdate = {
  agent: string
  status: AgentStatus
  message: string
  progress: number
}

export type ScanEvent =
  | { type: 'scan_started'; repo_path: string; agents: string[] }
  | { type: 'agent_update'; update: AgentUpdate }
  | { type: 'finding'; finding: Finding }
  | { type: 'scan_complete'; summary: ScanSummary }
  | { type: 'error'; detail: { code: string; message: string } }
