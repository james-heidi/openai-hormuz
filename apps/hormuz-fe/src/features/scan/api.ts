import { apiFetch } from '@/lib/apiClient'
import type { Finding, FixSummary, ScanSummary } from './types'

type GenerateFixesInput = {
  repoPath: string
  findings: Finding[]
  apply?: boolean
  createPr?: boolean
  rescan?: boolean
}

export const scanApi = {
  preview: (repoPath: string) =>
    apiFetch<ScanSummary>('/api/scans/preview', {
      method: 'POST',
      body: JSON.stringify({ repo_path: repoPath }),
    }),
  generateFixes: ({ repoPath, findings, apply = false, createPr = false, rescan = false }: GenerateFixesInput) =>
    apiFetch<FixSummary>('/api/scans/fixes', {
      method: 'POST',
      body: JSON.stringify({
        repo_path: repoPath,
        findings: findings.map(toFindingPayload),
        apply,
        create_pr: createPr,
        rescan,
      }),
    }),
}

function toFindingPayload(finding: Finding) {
  return {
    id: finding.id,
    violation_type: finding.violation_type,
    agent: finding.agent,
    category: finding.category,
    severity: finding.severity,
    file_path: finding.file_path,
    line: finding.line,
    context: finding.context,
    title: finding.title,
    description: finding.description,
    snippet: finding.snippet,
    regulations: finding.regulations,
    regulation_warning: finding.regulation_warning,
    recommendation: finding.recommendation,
    remediation_hint: finding.remediation_hint,
  }
}
