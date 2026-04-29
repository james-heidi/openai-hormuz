import { useCallback, useRef, useState } from 'react'
import type { AgentStatus, AgentUpdate, Finding, ScanEvent, ScanSummary } from '../types'

type AgentState = AgentUpdate

type SocketState = {
  connected: boolean
  running: boolean
  agents: AgentState[]
  findings: Finding[]
  summary: ScanSummary | null
  error: string | null
}

const EMPTY_STATE: SocketState = {
  connected: false,
  running: false,
  agents: [],
  findings: [],
  summary: null,
  error: null,
}

function statusFor(agent: string, status: AgentStatus = 'idle'): AgentState {
  return { agent, status, message: 'Waiting', progress: 0 }
}

function socketUrl() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/ws/scans`
}

export function useScanSocket() {
  const socketRef = useRef<WebSocket | null>(null)
  const [state, setState] = useState<SocketState>(EMPTY_STATE)

  const startScan = useCallback((repoPath: string) => {
    socketRef.current?.close()
    setState({ ...EMPTY_STATE, running: true })

    const socket = new WebSocket(socketUrl())
    socketRef.current = socket

    socket.onopen = () => {
      setState((current) => ({ ...current, connected: true }))
      socket.send(JSON.stringify({ repo_path: repoPath }))
    }

    socket.onmessage = (event) => {
      const message = JSON.parse(event.data) as ScanEvent
      setState((current) => reduceScanEvent(current, message))
    }

    socket.onerror = () => {
      setState((current) => ({
        ...current,
        running: false,
        error: 'WebSocket connection failed',
      }))
    }

    socket.onclose = () => {
      setState((current) => ({ ...current, connected: false, running: false }))
    }
  }, [])

  const reset = useCallback(() => {
    socketRef.current?.close()
    setState(EMPTY_STATE)
  }, [])

  return { ...state, startScan, reset }
}

function reduceScanEvent(state: SocketState, event: ScanEvent): SocketState {
  switch (event.type) {
    case 'scan_started':
      return {
        ...state,
        running: true,
        error: null,
        agents: event.agents.map((agent) => statusFor(agent, 'running')),
      }
    case 'agent_update':
      return {
        ...state,
        agents: upsertAgent(state.agents, event.update),
      }
    case 'finding':
      if (state.findings.some((finding) => finding.id === event.finding.id)) {
        return state
      }
      return {
        ...state,
        findings: [...state.findings, event.finding],
      }
    case 'scan_complete':
      return {
        ...state,
        running: false,
        summary: event.summary,
        findings: event.summary.findings,
      }
    case 'error':
      return {
        ...state,
        running: false,
        error: event.detail.message,
      }
  }
}

function upsertAgent(agents: AgentState[], update: AgentUpdate) {
  const exists = agents.some((agent) => agent.agent === update.agent)
  if (!exists) return [...agents, update]
  return agents.map((agent) => (agent.agent === update.agent ? update : agent))
}

