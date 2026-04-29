import { Activity, RotateCcw } from 'lucide-react'
import { AgentStatusBoard } from '../components/AgentStatusBoard'
import { ComplianceScore } from '../components/ComplianceScore'
import { ScanPanel } from '../components/ScanPanel'
import { ViolationList } from '../components/ViolationList'
import { useScanSocket } from '../hooks/useScanSocket'

export function ScanPage() {
  const scan = useScanSocket()

  return (
    <main className="min-h-screen bg-[#f7f7f4] text-zinc-950">
      <header className="border-b border-zinc-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-md bg-zinc-950 text-white">
              <Activity size={20} aria-hidden="true" />
            </div>
            <div>
              <h1 className="text-xl font-semibold tracking-normal">Compliance Codex</h1>
              <p className="text-sm text-zinc-500">OpenAI x UTS Hackathon</p>
            </div>
          </div>
          <button
            type="button"
            title="Reset"
            onClick={scan.reset}
            className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-zinc-300 bg-white text-zinc-700 hover:bg-zinc-100"
          >
            <RotateCcw size={18} aria-hidden="true" />
          </button>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-5 px-5 py-5 lg:grid-cols-[380px_1fr]">
        <section className="space-y-5">
          <ScanPanel running={scan.running} onScan={scan.startScan} error={scan.error} />
          <AgentStatusBoard agents={scan.agents} />
        </section>
        <section className="space-y-5">
          <ComplianceScore summary={scan.summary} running={scan.running} />
          <ViolationList findings={scan.findings} />
        </section>
      </div>
    </main>
  )
}

