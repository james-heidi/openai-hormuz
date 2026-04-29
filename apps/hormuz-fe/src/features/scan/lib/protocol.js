/**
 * Backend WebSocket event names. The wire format is a direct JSON object with
 * a stable `type` field, for example `{ type: 'finding', finding: {...} }`.
 */

export const EVT = Object.freeze({
  SCAN_STARTED: 'scan_started',
  AGENT_UPDATE: 'agent_update',
  FINDING: 'finding',
  SCAN_COMPLETE: 'scan_complete',
  ERROR: 'error',
});

export const AGENT_STATUSES = Object.freeze({
  IDLE: 'idle',
  RUNNING: 'running',
  DONE: 'done',
  ERROR: 'error',
});

export const RUN_STATUSES = Object.freeze({
  IDLE: 'idle',
  RUNNING: 'running',
  COMPLETE: 'complete',
  ERROR: 'error',
});
