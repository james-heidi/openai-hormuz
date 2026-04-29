import { MutationCache, QueryCache, QueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { ApiError } from './apiClient'

function reportError(error: unknown) {
  if (error instanceof ApiError) {
    toast.error(error.message)
    return
  }
  toast.error('Request failed')
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
  queryCache: new QueryCache({
    onError: reportError,
  }),
  mutationCache: new MutationCache({
    onError: reportError,
  }),
})

