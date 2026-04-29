export type Severity = 'critical' | 'high' | 'medium' | 'low'
export type AgentStatus = 'idle' | 'running' | 'done' | 'error'
export type ScanStatus = 'complete' | 'partial' | 'failed'

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
  scan_status: ScanStatus
  score: number
  total_findings: number
  counts_by_severity: Record<Severity, number>
  counts_by_agent: Record<string, number>
  findings: Finding[]
  failed_agents: { agent: string; message: string }[]
}

export type FixPatch = {
  finding_id: string
  file_path: string
  diff: string
  patch_path: string | null
  applied: boolean
}

export type FixFailure = {
  finding_id?: string | null
  file_path?: string | null
  code: string
  message: string
}

export type FixSummary = {
  output_type: 'local_diff' | 'github_pr'
  pr_url: string | null
  patch_path: string | null
  diff: string
  patches: FixPatch[]
  failures: FixFailure[]
  applied: boolean
  rescan_summary: ScanSummary | null
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
