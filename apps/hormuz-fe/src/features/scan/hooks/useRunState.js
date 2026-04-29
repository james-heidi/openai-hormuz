import { useCallback, useMemo, useReducer } from 'react';
import { EVT, RUN_STATUSES } from '../lib/protocol';

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
  summary: null,
  repoPath: '',
});

const SEVERITY_WEIGHTS = Object.freeze({
  critical: 18,
  high: 10,
  medium: 5,
  low: 2,
});
const SCORE_RISK_MULTIPLIER = 1.25;

const ACTIONS = Object.freeze({
  RUN_REQUESTED: 'RUN_REQUESTED',
  SCAN_STARTED: 'SCAN_STARTED',
  AGENT_UPDATE: 'AGENT_UPDATE',
  FINDING: 'FINDING',
  SCAN_COMPLETE: 'SCAN_COMPLETE',
  ERROR: 'ERROR',
  FIXES_GENERATED: 'FIXES_GENERATED',
  RESET: 'RESET',
});

function reducer(state, action) {
  switch (action.type) {
    case ACTIONS.RUN_REQUESTED:
      return {
        ...initialState,
        runId: action.runId,
        repoPath: action.repoPath ?? '',
        status: RUN_STATUSES.RUNNING,
      };

    case ACTIONS.SCAN_STARTED: {
      const agents = {};
      for (const name of action.event.agents ?? []) {
        const id = agentId(name);
        agents[id] = { id, label: name, status: 'idle' };
      }
      return {
        ...state,
        repoPath: action.event.repo_path ?? state.repoPath,
        agents,
      };
    }

    case ACTIONS.AGENT_UPDATE: {
      const update = action.event.update;
      if (!update?.agent) return state;
      const id = agentId(update.agent);
      const prev = state.agents[id] ?? { id, label: update.agent };
      return {
        ...state,
        agents: {
          ...state.agents,
          [id]: {
            ...prev,
            label: update.agent,
            status: update.status,
            message: update.message,
            progress: normalizeProgress(update.progress),
          },
        },
      };
    }

    case ACTIONS.FINDING: {
      const result = resultFromFinding(action.event.finding);
      if (!result?.id || state.results.some((item) => item.id === result.id)) return state;
      return {
        ...state,
        results: [...state.results, result],
      };
    }

    case ACTIONS.SCAN_COMPLETE: {
      const summary = action.event.summary;
      if (!summary) return state;
      const results = Array.isArray(summary.findings)
        ? summary.findings.map(resultFromFinding).filter(Boolean)
        : state.results;
      const failedAgents = summary.failed_agents ?? [];
      return {
        ...state,
        status: summary.scan_status === 'failed' ? RUN_STATUSES.ERROR : RUN_STATUSES.COMPLETE,
        score: summary.score,
        summary,
        results,
        error: failedAgents.length
          ? failedAgents.map((failure) => `${failure.agent}: ${failure.message}`).join('\n')
          : null,
      };
    }

    case ACTIONS.ERROR:
      return {
        ...state,
        status: RUN_STATUSES.ERROR,
        error: action.event.detail?.message ?? 'Unknown error',
      };

    case ACTIONS.FIXES_GENERATED: {
      const summary = action.summary;
      const patches = Array.isArray(summary?.patches)
        ? summary.patches.map(resultFromPatch)
        : [];
      const failures = summary?.failures ?? [];
      const acceptedFindingIds = new Set([
        ...(action.options?.acceptedFindingIds ?? []),
        ...(action.options?.acceptGeneratedPatches
          ? patches.map((patch) => patch.metadata?.violationCode)
          : []),
      ].filter(Boolean));
      const rescanViolations = Array.isArray(summary?.rescan_summary?.findings)
        ? summary.rescan_summary.findings.map(resultFromFinding).filter(Boolean)
        : null;
      const nextViolations = rescanViolations
        ? rescanViolations.filter((violation) => !acceptedFindingIds.has(violation.id))
        : state.results.filter((result) => result?.metadata?.kind !== 'patch');
      const nextScore = rescanViolations
        ? scoreFindings(nextViolations)
        : summary?.rescan_summary?.score;
      const nextSummary = rescanViolations
        ? {
          ...summary.rescan_summary,
          score: nextScore,
          total_findings: nextViolations.length,
          counts_by_severity: countBySeverity(nextViolations),
          findings: nextViolations,
        }
        : summary?.rescan_summary;
      const acceptedPatchIds = action.options?.acceptGeneratedPatches
        ? patches.map((patch) => patch.id)
        : [action.options?.acceptedPatchId].filter(Boolean);
      const nextPatches = action.options?.mergePatches
        ? markAcceptedPatches(
          mergePatches(
            state.results.filter((result) => result?.metadata?.kind === 'patch'),
            patches,
          ),
          acceptedPatchIds,
        )
        : patches;
      const error = failures.length && patches.length === 0
        ? failures.map((failure) => failure.message).join('\n')
        : null;
      return {
        ...state,
        results: [...nextViolations, ...nextPatches],
        prevScore: typeof nextScore === 'number' ? state.score : state.prevScore,
        score: typeof nextScore === 'number' ? nextScore : state.score,
        summary: nextSummary ?? state.summary,
        error,
      };
    }

    case ACTIONS.RESET:
      return initialState;

    default:
      return state;
  }
}

const EVT_TO_ACTION = Object.freeze({
  [EVT.SCAN_STARTED]: ACTIONS.SCAN_STARTED,
  [EVT.AGENT_UPDATE]: ACTIONS.AGENT_UPDATE,
  [EVT.FINDING]: ACTIONS.FINDING,
  [EVT.SCAN_COMPLETE]: ACTIONS.SCAN_COMPLETE,
  [EVT.ERROR]: ACTIONS.ERROR,
});

export function useRunState() {
  const [state, dispatch] = useReducer(reducer, initialState);

  const handleEvent = useCallback((event) => {
    if (!event || typeof event !== 'object') return;
    const actionType = EVT_TO_ACTION[event.type];
    if (!actionType) return;
    dispatch({ type: actionType, event });
  }, []);

  const runRequested = useCallback((repoPath = '') => {
    const runId = newRunId();
    dispatch({ type: ACTIONS.RUN_REQUESTED, runId, repoPath });
    return runId;
  }, []);

  const fixesGenerated = useCallback((summary, options = {}) => {
    dispatch({ type: ACTIONS.FIXES_GENERATED, summary, options });
  }, []);

  const reset = useCallback(() => {
    dispatch({ type: ACTIONS.RESET });
  }, []);

  const dispatchers = useMemo(
    () => ({ fixesGenerated, handleEvent, reset, runRequested }),
    [fixesGenerated, handleEvent, reset, runRequested],
  );

  return [state, dispatchers];
}

function resultFromFinding(finding) {
  if (!finding?.id) return null;
  const id = agentId(finding.agent);
  const regulations = Array.isArray(finding.regulations) ? finding.regulations : [];
  return {
    ...finding,
    agentId: id,
    location: finding.line ? `${finding.file_path}:${finding.line}` : finding.file_path,
    metadata: {
      kind: 'violation',
      violationCode: finding.violation_type,
      context: finding.context,
      gdpr: regulations.find((regulation) => regulation.framework === 'GDPR'),
      app: regulations.find((regulation) => regulation.framework === 'APP'),
    },
    actions: [{ label: 'Auto-fix', actionId: 'auto-fix' }],
  };
}

function resultFromPatch(patch, index) {
  if (!patch) return null;
  const id = `patch:${patch.finding_id ?? patch.file_path ?? index}`;
  return {
    id,
    agentId: 'fix-generator',
    title: `Patch for ${patch.file_path ?? patch.finding_id ?? 'finding'}`,
    location: patch.file_path,
    metadata: {
      kind: 'patch',
      file: patch.file_path,
      diffLines: diffLines(patch.diff),
      violationCode: patch.finding_id,
      patchPath: patch.patch_path,
      applied: Boolean(patch.applied),
    },
    actions: [],
  };
}

function mergePatches(existingPatches, incomingPatches) {
  const byId = new Map();
  for (const patch of existingPatches) {
    if (patch?.id) byId.set(patch.id, patch);
  }
  for (const patch of incomingPatches) {
    if (patch?.id) byId.set(patch.id, patch);
  }
  return Array.from(byId.values());
}

function markAcceptedPatches(patches, acceptedPatchIds) {
  if (!acceptedPatchIds.length) return patches;
  const accepted = new Set(acceptedPatchIds);
  return patches.map((patch) => {
    if (!accepted.has(patch.id)) return patch;
    return {
      ...patch,
      metadata: {
        ...patch.metadata,
        accepted: true,
      },
    };
  });
}

function scoreFindings(findings) {
  const penalty = findings.reduce(
    (total, finding) => total + (SEVERITY_WEIGHTS[finding.severity] ?? 0),
    0,
  );
  if (penalty === 0) return 100;
  return Math.round(10000 / (100 + penalty * SCORE_RISK_MULTIPLIER));
}

function countBySeverity(findings) {
  const counts = { critical: 0, high: 0, medium: 0, low: 0 };
  for (const finding of findings) {
    if (finding.severity in counts) counts[finding.severity] += 1;
  }
  return counts;
}

function diffLines(diff) {
  if (!diff) return [];
  return diff
    .split('\n')
    .filter((line) => line && !line.startsWith('+++') && !line.startsWith('---'))
    .map((line) => {
      if (line.startsWith('+')) return { type: '+', text: line.slice(1) };
      if (line.startsWith('-')) return { type: '-', text: line.slice(1) };
      return { type: ' ', text: line.startsWith(' ') ? line.slice(1) : line };
    });
}

function normalizeProgress(progress) {
  if (typeof progress !== 'number') return undefined;
  return Math.max(0, Math.min(1, progress / 100));
}

function agentId(name) {
  return String(name ?? 'agent')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '') || 'agent';
}
