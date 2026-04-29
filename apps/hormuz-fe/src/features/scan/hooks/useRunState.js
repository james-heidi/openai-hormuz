import { useReducer, useCallback, useMemo } from 'react';
import { EVT, RUN_STATUSES } from '../lib/protocol';

/**
 * Single source of truth for the run lifecycle. The reducer is the only
 * place that mutates state, and the only place that filters incoming WS
 * events by `runId` — preventing stale messages from a previous run from
 * leaking into a new one when the user re-clicks Run.
 */

const newRunId = () =>
  `run_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;

const initialState = Object.freeze({
  runId: null,
  status: RUN_STATUSES.IDLE,
  agents: {},
  results: [],
  score: null,
  prevScore: null,
  error: null,
});

const ACTIONS = Object.freeze({
  RUN_REQUESTED: 'RUN_REQUESTED',
  RUN_ACCEPTED: 'RUN_ACCEPTED',
  AGENT_STATUS: 'AGENT_STATUS',
  RESULT_ADD: 'RESULT_ADD',
  SCORE_UPDATE: 'SCORE_UPDATE',
  RUN_COMPLETE: 'RUN_COMPLETE',
  RUN_ERROR: 'RUN_ERROR',
  RESET: 'RESET',
});

const isStale = (state, payloadRunId) =>
  state.runId !== null && payloadRunId && payloadRunId !== state.runId;

function reducer(state, action) {
  switch (action.type) {
    case ACTIONS.RUN_REQUESTED:
      return {
        ...initialState,
        runId: action.runId,
        status: RUN_STATUSES.RUNNING,
      };

    case ACTIONS.RUN_ACCEPTED: {
      if (isStale(state, action.payload.runId)) return state;
      const agents = {};
      for (const a of action.payload.agents ?? []) {
        agents[a.id] = { id: a.id, label: a.label, status: 'idle' };
      }
      return { ...state, agents };
    }

    case ACTIONS.AGENT_STATUS: {
      const { runId, agentId, status, message, progress } = action.payload;
      if (isStale(state, runId)) return state;
      const prev = state.agents[agentId] ?? { id: agentId, label: agentId };
      return {
        ...state,
        agents: {
          ...state.agents,
          [agentId]: { ...prev, status, message, progress },
        },
      };
    }

    case ACTIONS.RESULT_ADD: {
      const { runId, result } = action.payload;
      if (isStale(state, runId)) return state;
      if (!result?.id) return state;
      // Dedupe on id in case the BE re-sends.
      if (state.results.some((r) => r.id === result.id)) return state;
      return { ...state, results: [...state.results, result] };
    }

    case ACTIONS.SCORE_UPDATE: {
      if (isStale(state, action.payload.runId)) return state;
      const next = action.payload.score;
      if (typeof next !== 'number') return state;
      return { ...state, prevScore: state.score, score: next };
    }

    case ACTIONS.RUN_COMPLETE:
      if (isStale(state, action.payload.runId)) return state;
      return { ...state, status: RUN_STATUSES.COMPLETE };

    case ACTIONS.RUN_ERROR:
      if (isStale(state, action.payload.runId)) return state;
      return {
        ...state,
        status: RUN_STATUSES.ERROR,
        error: action.payload.error ?? 'Unknown error',
      };

    case ACTIONS.RESET:
      return initialState;

    default:
      return state;
  }
}

const EVT_TO_ACTION = Object.freeze({
  [EVT.RUN_ACCEPTED]: ACTIONS.RUN_ACCEPTED,
  [EVT.AGENT_STATUS]: ACTIONS.AGENT_STATUS,
  [EVT.RESULT_ADD]: ACTIONS.RESULT_ADD,
  [EVT.SCORE_UPDATE]: ACTIONS.SCORE_UPDATE,
  [EVT.RUN_COMPLETE]: ACTIONS.RUN_COMPLETE,
  [EVT.RUN_ERROR]: ACTIONS.RUN_ERROR,
});

export function useRunState() {
  const [state, dispatch] = useReducer(reducer, initialState);

  const handleEvent = useCallback((msg) => {
    if (!msg || typeof msg !== 'object') return;
    const actionType = EVT_TO_ACTION[msg.type];
    if (!actionType) return;
    dispatch({ type: actionType, payload: msg.payload ?? {} });
  }, []);

  const runRequested = useCallback(() => {
    const runId = newRunId();
    dispatch({ type: ACTIONS.RUN_REQUESTED, runId });
    return runId;
  }, []);

  const reset = useCallback(() => {
    dispatch({ type: ACTIONS.RESET });
  }, []);

  const dispatchers = useMemo(
    () => ({ handleEvent, runRequested, reset }),
    [handleEvent, runRequested, reset],
  );

  return [state, dispatchers];
}
