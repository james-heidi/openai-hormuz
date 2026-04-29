# Compliance Codex Frontend Specification

## 1. Purpose

Compliance Codex is a single-screen React frontend for scanning repositories, showing parallel agent progress, reviewing privacy and compliance findings, and triggering remediation actions.

The frontend is presentation-only. The backend owns source analysis, regulation mapping, scoring, and patch generation. Every finding sent to the frontend must include display-ready metadata, so the UI does not perform regulation lookups.

## 2. Goals

- Start a scan from a repository path or URL.
- Show live status for multiple scanning agents.
- Stream findings as they arrive.
- Show a compliance score that updates over the run.
- Render GDPR and Australian Privacy Principles context for each finding.
- Trigger result-level and bulk remediation actions.
- Work without a backend by falling back to deterministic mock data.

## 3. Non-goals

- Authentication, multi-user state, or persistence.
- Complex routing; the app is a single workflow screen.
- Client-side regulation lookup or rule mapping.
- Virtualized lists; expected result volume is small.
- Browser support beyond the demo environment.

## 4. Stack

- Vite
- React 18
- Tailwind CSS 3.4
- framer-motion
- clsx

No additional frontend dependency is required for diffs. The backend sends pre-rendered diff lines.

## 5. Architecture

### 5.1 Layout

```text
+--------------------------------------------------------+
| Header                                ConnectionBadge  |
+------------------+-------------------------------------+
| ScanPanel        | AgentStatusBoard                    |
|                  |                                     |
| ComplianceScore  | ViolationList                       |
|                  |                                     |
| FixPanel         |                                     |
+------------------+-------------------------------------+
```

Use one column on mobile and `md:grid-cols-[320px_1fr]` on wider screens.

### 5.2 Data flow

```text
WebSocket event -> useWebSocket -> useRunState reducer -> React render
```

The reducer is the single state mutation point. Components should not apply protocol logic directly.

### 5.3 Frontend responsibilities

- Manage connection state and mock fallback.
- Dispatch scan and action messages.
- Render agent status, findings, score, and patches.
- Ignore stale events from old runs.
- Keep regulation metadata display-only.

### 5.4 Backend responsibilities

- Accept scan and action messages.
- Emit agent, finding, score, completion, and error events.
- Attach full regulation metadata to each compliance finding.
- Generate patch previews and send them as `diffLines`.

## 6. File Structure

```text
src/
|-- main.jsx
|-- App.jsx
|-- index.css
|-- components/
|   |-- ActionPanel.jsx
|   |-- AgentBoard.jsx
|   |-- AgentCard.jsx
|   |-- ConnectionBadge.jsx
|   |-- ResultItem.jsx
|   |-- ResultList.jsx
|   |-- ScoreCard.jsx
|   |-- domain/
|   |   |-- AgentStatusBoard.jsx
|   |   |-- ComplianceScore.jsx
|   |   |-- FixPanel.jsx
|   |   |-- ScanPanel.jsx
|   |   |-- ViolationCard.jsx
|   |   `-- ViolationList.jsx
|   `-- ui/
|       |-- DiffView.jsx
|       `-- RegulationBadge.jsx
|-- hooks/
|   |-- useRunState.js
|   `-- useWebSocket.js
`-- lib/
    |-- domainMockServer.js
    |-- mockServer.js
    |-- protocol.js
    `-- severity.js
```

Generic components must not interpret compliance metadata. Domain components may read `result.metadata`.

## 7. Wire Protocol

Source of truth: `src/lib/protocol.js`. Export event constants as `EVT.*` and document payloads with JSDoc typedefs.

### 7.1 Client to server

| Type | Payload | Description |
| --- | --- | --- |
| `run.start` | `{ runId, input }` | Starts a scan. |
| `run.cancel` | `{ runId }` | Cancels the active scan. |
| `action.invoke` | `{ runId, actionId, params? }` | Invokes a finding or remediation action. |

### 7.2 Server to client

| Type | Payload |
| --- | --- |
| `run.accepted` | `{ runId, agents: [{ id, label }] }` |
| `agent.status` | `{ runId, agentId, status, message?, progress? }` |
| `result.add` | `{ runId, agentId, result }` |
| `score.update` | `{ runId, score, prev? }` |
| `run.complete` | `{ runId, summary? }` |
| `run.error` | `{ runId, error }` |

`agent.status.status` is one of `idle`, `running`, `done`, or `error`. `progress` is a number from `0` to `1`.

### 7.3 Result shape

```js
/**
 * @typedef {'low'|'medium'|'high'|'critical'} Severity
 * @typedef {{ label: string, actionId: string }} ResultAction
 * @typedef {Object} GenericResult
 * @property {string} id
 * @property {string} agentId
 * @property {string} title
 * @property {string} [description]
 * @property {Severity} [severity]
 * @property {string} [location]
 * @property {Object<string, any>} [metadata]
 * @property {ResultAction[]} [actions]
 */
```

Generic UI components render only common fields. Compliance-specific fields belong in `metadata`.

### 7.4 Compliance metadata

```json
{
  "violationCode": "PII-LOG-001",
  "gdpr": {
    "article": "Art. 32",
    "title": "Security of processing",
    "summary": "The controller and processor shall implement appropriate technical and organisational measures.",
    "fine": "Up to EUR 10M or 2% of global annual turnover",
    "url": "https://gdpr-info.eu/art-32-gdpr/"
  },
  "app": {
    "principle": "APP 11",
    "title": "Security of personal information",
    "summary": "An APP entity must take reasonable steps to protect the personal information it holds.",
    "fine": "Civil penalty up to AU$50M for corporations",
    "url": "https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-quick-reference"
  },
  "diffLines": [
    { "type": "-", "text": "logger.info(f\"login: {email} {password}\")" },
    { "type": "+", "text": "logger.info(f\"login: {email}\")" }
  ]
}
```

`diffLines` is optional and appears on patch-related results.

### 7.5 Stale event guard

The reducer must ignore any server event whose `runId` does not match `state.runId`. This prevents late events from previous scans from affecting the current run.

## 8. State

### 8.1 Run state

```js
{
  runId: string | null,
  status: 'idle' | 'running' | 'complete' | 'error',
  agents: Record<string, {
    id: string,
    label: string,
    status: 'idle' | 'running' | 'done' | 'error',
    message?: string,
    progress?: number
  }>,
  results: GenericResult[],
  score: number | null,
  prevScore: number | null,
  error: string | null
}
```

### 8.2 Reducer actions

| Action | Effect |
| --- | --- |
| `RUN_REQUESTED` | Clears previous run data and sets `status` to `running`. |
| `RUN_ACCEPTED` | Initializes the agent map. |
| `AGENT_STATUS` | Updates one agent. |
| `RESULT_ADD` | Appends a result. |
| `SCORE_UPDATE` | Stores `prevScore` and updates `score`. |
| `RUN_COMPLETE` | Sets `status` to `complete`. |
| `RUN_ERROR` | Sets `status` to `error` and stores the error. |

## 9. Components

### 9.1 Generic components

| Component | Props | Behavior |
| --- | --- | --- |
| `ActionPanel` | `{ disabled, onRun, placeholder?, buttonLabel? }` | Local input state. Cmd/Ctrl+Enter submits. |
| `AgentBoard` | `{ agents }` | Grid of agent cards. |
| `AgentCard` | `{ agent }` | Shows idle, running, done, and error states. |
| `ResultList` | `{ results, onAction?, emptyState?, renderItem? }` | Sorts by severity, then arrival order. Uses `renderItem` for domain-specific rendering. |
| `ResultItem` | `{ result, onAction? }` | Generic result row. Does not inspect `metadata`. |
| `ScoreCard` | `{ score, label?, thresholds? }` | Animated score readout. |
| `ConnectionBadge` | `{ status, retryCount }` | Shows connected, connecting, disconnected, or mock state. |

### 9.2 Domain components

| Component | Behavior |
| --- | --- |
| `ScanPanel` | Wraps `ActionPanel` with scan copy and repo input. |
| `AgentStatusBoard` | Wraps `AgentBoard` and pins expected scanner order. |
| `ComplianceScore` | Wraps `ScoreCard` with compliance thresholds. |
| `ViolationList` | Renders `ResultList` with `ViolationCard`. |
| `ViolationCard` | Displays finding details, severity, location, GDPR metadata, APP metadata, and actions. |
| `FixPanel` | Triggers bulk fixes and renders streamed patch results. |
| `DiffView` | Displays backend-provided diff lines. |
| `RegulationBadge` | Displays compact regulation labels. |

### 9.3 Violation card layout

```text
+----------------------------------------------------------+
| [HIGH] Plaintext password in logs                        |
|        src/auth/login.py:142                             |
+------------------------------+---------------------------+
| GDPR                         | AU Privacy Act            |
| Art. 32 - Security of        | APP 11 - Security of      |
| processing                   | personal information      |
| Fine information             | Fine information          |
+------------------------------+---------------------------+
| [Auto-fix] [Suppress] [View code]                        |
+----------------------------------------------------------+
```

`ViolationCard` reads `result.metadata.gdpr` and `result.metadata.app` directly. It should degrade gracefully if either object is missing.

### 9.4 Score animation

- First non-null score appears without count-up.
- Later score changes animate over 1.5 seconds with ease-out timing.
- Color derives from final score thresholds, not the animated value.
- Default thresholds: good at `80`, warning at `50`.

## 10. Hooks

### 10.1 `useWebSocket`

```js
useWebSocket({ url, onMessage, enabled = true, mock = false })
// returns { status, send, retryCount }
```

`status` is one of `connecting`, `open`, `closed`, or `mock`.

Behavior:

- Connects to `VITE_WS_URL` when provided.
- Reconnects with bounded exponential backoff.
- Falls back to mock mode when explicitly requested, when no URL is configured, or when reconnect attempts are exhausted.
- Drops outgoing messages while disconnected and logs a warning.

Mock mode decision:

```js
const useMock = import.meta.env.VITE_USE_MOCK === '1' || !import.meta.env.VITE_WS_URL;
```

### 10.2 `useRunState`

Returns `[state, dispatchers]`.

Dispatchers should expose named methods such as `runRequested(input)` and `handleEvent(msg)` so components do not construct reducer actions directly.

## 11. Mock Server

`src/lib/mockServer.js` provides a deterministic generic stream. `src/lib/domainMockServer.js` provides compliance-specific fixtures.

The mock server must use the same protocol events as the real backend.

Expected generic stream:

| Step | Event | Notes |
| --- | --- | --- |
| 1 | `run.accepted` | Three agents. |
| 2 | `agent.status` | Agents enter `running`. |
| 3 | `result.add` | Findings stream incrementally. |
| 4 | `score.update` | Initial score. |
| 5 | `result.add` | More findings. |
| 6 | `score.update` | Updated score. |
| 7 | `agent.status` | Agents enter `done`. |
| 8 | `run.complete` | Run finishes. |

Optional environment setting:

```text
VITE_MOCK_SPEED=fast
```

## 12. Styling

### 12.1 Theme tokens

```css
:root {
  --bg: #0a0a0b;
  --surface: #141418;
  --surface-2: #1c1c22;
  --border: #2a2a32;
  --text: #e8e8ee;
  --text-dim: #8a8a98;
  --accent: #7c5cff;
  --good: #22c55e;
  --warn: #f59e0b;
  --bad: #ef4444;
}
```

### 12.2 Severity helpers

```js
export const RANK = { critical: 4, high: 3, medium: 2, low: 1 };

export const sortBySeverity = (a, b) =>
  (RANK[b.severity] ?? 0) - (RANK[a.severity] ?? 0);
```

Tone helpers should map severity to Tailwind classes for background, text, and border color.

## 13. Acceptance Criteria

- `npm run dev` starts without errors.
- With no `VITE_WS_URL`, the app enters mock mode and the full scan flow works.
- With an unreachable `VITE_WS_URL`, the app retries and then falls back to mock mode.
- Starting a scan shows agents running, streams findings, updates the score, and completes the run.
- Results are sorted by severity and keep stable ordering within the same severity.
- `ViolationCard` renders GDPR and APP metadata from the result payload.
- `FixPanel` sends `action.invoke` for bulk and result-level remediation actions.
- Patch results render through `DiffView`.
- Re-running a scan clears previous state and ignores stale events.
- Console output has no runtime errors during the main flow.

## 14. Critical Files

| File | Responsibility |
| --- | --- |
| `src/lib/protocol.js` | Event constants and payload typedefs. |
| `src/hooks/useRunState.js` | Reducer, run lifecycle, stale event guard. |
| `src/hooks/useWebSocket.js` | Connection state, reconnects, mock fallback. |
| `src/lib/mockServer.js` | Generic standalone demo stream. |
| `src/lib/domainMockServer.js` | Compliance-specific standalone fixtures. |
| `src/components/ResultList.jsx` | Generic result rendering extension point. |
| `src/components/domain/ViolationCard.jsx` | Regulation-aware finding presentation. |
| `src/components/domain/FixPanel.jsx` | Remediation action and patch display flow. |
| `src/components/ScoreCard.jsx` | Score display and animation behavior. |
| `src/App.jsx` | Screen composition and event wiring. |
