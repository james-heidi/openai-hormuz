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
| `scan_complete` | Scan finished with score and counts. |
| `error` | Backend could not complete the request. |

## Invariants

- The first client message is the scan request: `{ "repo_path": "..." }`.
- Every event has a `type`.
- Findings include `id`, `agent`, `category`, `violation_type`, `severity`,
  `file_path`, `line`, `context`, `title`, `description`, `regulations`,
  `recommendation`, and `remediation_hint`.
- The REST preview endpoint and WebSocket path use the same domain models.
