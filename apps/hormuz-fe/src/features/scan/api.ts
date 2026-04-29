import { apiFetch } from '@/lib/apiClient'
import type { ScanSummary } from './types'

export const scanApi = {
  preview: (repoPath: string) =>
    apiFetch<ScanSummary>('/api/scans/preview', {
      method: 'POST',
      body: JSON.stringify({ repo_path: repoPath }),
    }),
}

