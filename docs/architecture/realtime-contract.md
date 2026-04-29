# Realtime Contract - Scan Events

**Status:** Adopted.

## Decision

Scan progress streams over `/ws/scans` as JSON messages with a stable `type`
field.

## Event Types

| Type | Purpose |
| --- | --- |
| `scan_started` | Backend accepted the request. |
| `agent_update` | One scanner changed status or progress. |
| `finding` | One compliance finding is available. |
| `scan_complete` | Scan finished with score, counts, findings, and failure state. |
| `error` | Backend could not complete the request. |

## Invariants

- The first client message is the scan request: `{ "repo_path": "..." }`.
- Every event has a `type`.
- Findings include `id`, `agent`, `category`, `violation_type`, `severity`,
  `file_path`, `line`, `context`, `title`, `description`, `regulations`,
  `recommendation`, and `remediation_hint`.
- `scan_complete.summary` includes `scan_status`, `score`, `total_findings`,
  `counts_by_severity`, `counts_by_agent`, streamed `findings`, and
  `failed_agents`.
- Scores start at 100 and subtract severity weights from mapped findings:
  critical 18, high 10, medium 5, low 2, floored at 0.
- The REST preview endpoint and WebSocket path use the same domain models.
