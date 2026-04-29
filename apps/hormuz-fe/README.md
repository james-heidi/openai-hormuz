# codex-subagent-starter

A **generic starter kit** for building React frontends that orchestrate parallel Codex subagents over a WebSocket. **This repo contains no domain logic.** It provides a UI shell, an agent status board, a generic results list, an animated score readout, and a WebSocket hook with a mock-mode fallback so you can `npm run dev` without a backend.

Fork this repo to add your domain.

---

## Quickstart

```bash
npm install
npm run dev
```

Open `http://localhost:5173`. By default the UI connects to `/ws/scan` on the
current host through the Vite proxy. Set `VITE_USE_MOCK=1` to force the
in-process mock stream, or set `VITE_WS_URL` to point at a different backend.

## What's in here

```
src/
├── App.jsx                  # Layout shell, owns top-level state
├── components/              # Generic, reusable UI primitives
│   ├── ActionPanel.jsx
│   ├── AgentBoard.jsx
│   ├── AgentCard.jsx
│   ├── ResultList.jsx       # Accepts a `renderItem` prop — the seam a fork uses
│   ├── ResultItem.jsx
│   ├── ScoreCard.jsx
│   └── ConnectionBadge.jsx
├── hooks/
│   ├── useRunState.js       # useReducer; single chokepoint for state mutation
│   └── useWebSocket.js      # connect + reconnect + mock fallback
└── lib/
    ├── protocol.js          # Wire-protocol constants + JSDoc typedefs
    ├── severity.js          # Generic severity rank + tone helpers
    └── mockServer.js        # Deterministic scripted stream
```

## Wire Protocol

The backend WebSocket contract is source of truth. The frontend connects to
`/ws/scan`, sends the first message as `{ "repo_path": "..." }`, and receives
direct JSON events with a stable `type` field.

| Direction | `type` | Purpose |
|---|---|---|
| -> | request body | `{ "repo_path": "..." }` starts a scan |
| <- | `scan_started` | Backend accepted the scan; lists agents |
| <- | `agent_update` | Agent flipped `idle` / `running` / `done` / `error` |
| <- | `finding` | Append a finding to the list |
| <- | `scan_complete` | Run finished with summary, score, and failures |
| <- | `error` | Fatal or validation error |

Auto-fix actions use the REST fix endpoint rather than the scan WebSocket.

## Environment variables

| Variable | Default | Effect |
|---|---|---|
| `VITE_WS_URL` | `/ws/scan` on current host | Optional full WebSocket URL override. |
| `VITE_USE_MOCK` | — | Set to `1` to force mock mode even when `VITE_WS_URL` is set. |
| `VITE_MOCK_SPEED` | — | `fast` halves mock-stream timings. Useful for demo recording. |

## Forking to add a domain

1. Fork to a new repo. Link this repo from your README per hackathon rules.
2. Add domain components under `src/components/domain/`.
3. Pass a `renderItem` prop to `ResultList` so each finding renders with your domain card layout — no changes needed in the generic components.
4. Optionally write a domain-flavoured mock server alongside `mockServer.js` so the UI keeps working offline.

## License

MIT.

---

Built for the OpenAI x UTS Hackathon 2026.
