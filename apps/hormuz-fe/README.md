# codex-subagent-starter

A **generic starter kit** for building React frontends that orchestrate parallel Codex subagents over a WebSocket. **This repo contains no domain logic.** It provides a UI shell, an agent status board, a generic results list, an animated score readout, and a WebSocket hook with a mock-mode fallback so you can `npm run dev` without a backend.

Fork this repo to add your domain.

---

## Quickstart

```bash
npm install
npm run dev
```

Open `http://localhost:5173`. With no `VITE_WS_URL` configured the UI runs against an in-process mock server — the badge in the header reads `MOCK`. Click **Run** to play a deterministic ~6-second stream.

To wire up a real backend, copy `.env.example` to `.env.local` and set `VITE_WS_URL`.

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

## Wire protocol

All messages: `{ type: string, payload: object }`. Source of truth is [`src/lib/protocol.js`](src/lib/protocol.js).

| Direction | `type` | Purpose |
|---|---|---|
| → | `run.start` | Begin a run with an input string |
| → | `run.cancel` | Abort the current run |
| → | `action.invoke` | Invoke an action attached to a result |
| ← | `run.accepted` | Server confirms run; lists agents |
| ← | `agent.status` | Agent flipped `idle` / `running` / `done` / `error` |
| ← | `result.add` | Append a finding to the list |
| ← | `score.update` | Update the score readout |
| ← | `run.complete` | Run finished |
| ← | `run.error` | Fatal error |

Findings carry an open `metadata` object and an optional `actions` array — these are the seams a domain layer fills in without changing the protocol.

## Environment variables

| Variable | Default | Effect |
|---|---|---|
| `VITE_WS_URL` | — | If set, the hook connects here. Otherwise mock mode is on. |
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
