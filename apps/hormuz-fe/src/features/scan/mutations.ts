import { useMutation } from '@tanstack/react-query'
import { scanApi } from './api'

export function usePreviewScanMutation() {
  return useMutation({
    mutationFn: scanApi.preview,
  })
}

export function useGenerateFixesMutation() {
  return useMutation({
    mutationFn: scanApi.generateFixes,
  })
}
