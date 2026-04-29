export const scanKeys = {
  all: ['scan'] as const,
  preview: (repoPath: string) => [...scanKeys.all, 'preview', repoPath] as const,
}

