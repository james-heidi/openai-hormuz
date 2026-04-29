import { Play } from 'lucide-react'
import { FormEvent, useState } from 'react'

type ScanPanelProps = {
  running: boolean
  error: string | null
  onScan: (repoPath: string) => void
}

export function ScanPanel({ running, error, onScan }: ScanPanelProps) {
  const [repoPath, setRepoPath] = useState('')

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!repoPath.trim()) return
    onScan(repoPath.trim())
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-lg border border-zinc-200 bg-white p-4">
      <label htmlFor="repo-path" className="text-sm font-medium text-zinc-700">
        Repository path
      </label>
      <div className="mt-2 flex gap-2">
        <input
          id="repo-path"
          value={repoPath}
          onChange={(event) => setRepoPath(event.target.value)}
          placeholder="/absolute/path/to/demo_repo"
          className="min-w-0 flex-1 rounded-md border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-zinc-900"
        />
        <button
          type="submit"
          disabled={running || !repoPath.trim()}
          className="inline-flex h-10 items-center gap-2 rounded-md bg-zinc-950 px-3 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-zinc-300"
        >
          <Play size={16} aria-hidden="true" />
          {running ? 'Scanning' : 'Scan'}
        </button>
      </div>
      {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
    </form>
  )
}

