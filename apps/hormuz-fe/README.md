# Hormuz Frontend

Vite React frontend for Compliance Codex. The UI starts scans over WebSocket,
renders streamed agent/finding events, and calls the backend REST fix endpoint
for optional remediation patches.

## Quickstart

Run from the repo root:

```bash
task install
task be:dev
task fe:dev
```

Open `http://localhost:3000`.

## Backend Routing

The local Vite server proxies backend traffic:

| Frontend path | Backend target |
| --- | --- |
| `/api/*` | `http://localhost:4000/api/*` |
| `/ws/*` | `ws://localhost:4000/ws/*` |

With no frontend env file, scans connect to `/ws/scan` on the current frontend
host and REST calls use relative `/api/*` paths. This is the expected local
integration setup.

## Environment Variables

| Variable | Default | Effect |
| --- | --- | --- |
| `VITE_WS_URL` | `/ws/scan` on the current host | Optional full WebSocket URL override. |
| `VITE_USE_MOCK` | unset | Set to `1` to force the in-process demo stream instead of the backend. |
| `VITE_MOCK_SPEED` | unset | Set to `fast` to shorten mock stream timings for recordings. |

## Wire Protocol

The backend WebSocket contract is the source of truth. The frontend sends the
first message as `{ "repo_path": "..." }` and receives direct JSON events with a
stable `type` field.

| Direction | `type` | Purpose |
| --- | --- | --- |
| -> | request body | `{ "repo_path": "..." }` starts a scan. |
| <- | `scan_started` | Backend accepted the scan and listed agents. |
| <- | `agent_update` | Agent status, progress, and message changed. |
| <- | `finding` | A finding streamed from a scanner. |
| <- | `scan_complete` | Final summary, score, findings, and failures. |
| <- | `error` | Fatal validation or runtime error. |

Auto-fix uses `POST /api/scans/fixes`; it can return generated patches and an
optional rescan summary.
