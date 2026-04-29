/**
 * WebSocket protocol — single source of truth for events that flow between
 * the React frontend and the orchestrator backend (or the in-process mock
 * server). The frontend never invents event names; everything reads from
 * `EVT.*` here.
 *
 * Wire format: `{ type: string, payload: object }`. Payload shapes are
 * defined as JSDoc typedefs at the bottom of this file.
 *
 * The protocol is intentionally generic. Domain-specific data rides inside
 * `result.metadata` and `result.actions` — this lets a fork add a domain
 * layer without changing the protocol.
 */

export const EVT = Object.freeze({
  // Client → Server
  RUN_START: 'run.start',
  RUN_CANCEL: 'run.cancel',
  ACTION_INVOKE: 'action.invoke',

  // Server → Client
  RUN_ACCEPTED: 'run.accepted',
  AGENT_STATUS: 'agent.status',
  RESULT_ADD: 'result.add',
  SCORE_UPDATE: 'score.update',
  RUN_COMPLETE: 'run.complete',
  RUN_ERROR: 'run.error',
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

/**
 * @typedef {'low'|'medium'|'high'|'critical'} Severity
 *
 * @typedef {Object} ResultAction
 * @property {string} label
 * @property {string} actionId
 *
 * @typedef {Object} GenericResult
 * @property {string} id
 * @property {string} agentId
 * @property {string} title
 * @property {string} [description]
 * @property {Severity} [severity]
 * @property {string} [location]               // e.g. "src/foo.py:42"
 * @property {Object<string, any>} [metadata]  // free-form; domain layer fills this
 * @property {ResultAction[]} [actions]
 *
 * @typedef {Object} AgentDescriptor
 * @property {string} id
 * @property {string} label
 *
 * @typedef {Object} AgentState
 * @property {string} id
 * @property {string} label
 * @property {'idle'|'running'|'done'|'error'} status
 * @property {string} [message]
 * @property {number} [progress]               // 0..1
 *
 * @typedef {Object} WSEnvelope
 * @property {string} type
 * @property {Object} payload
 */
