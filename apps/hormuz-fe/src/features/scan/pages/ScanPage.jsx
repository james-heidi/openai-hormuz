import { useCallback, useEffect, useMemo, useState } from 'react';
import clsx from 'clsx';
import { useRunState } from '../hooks/useRunState';
import { useWebSocket } from '../hooks/useWebSocket';
import { AGENT_STATUSES, RUN_STATUSES } from '../lib/protocol';
import { createDomainMockServer } from '../lib/domainMockServer';
import { sortBySeverity } from '../lib/severity';
import { useGenerateFixesMutation } from '../mutations';

import ScanPanel from '../components/ScanPanel';
import AgentStatusBoard from '../components/AgentStatusBoard';
import ComplianceScore from '../components/ComplianceScore';
import ViolationList from '../components/ViolationList';
import FixPanel from '../components/FixPanel';
import ViolationCard from '../components/ViolationCard';
import ConnectionBadge from '../../../components/ConnectionBadge';
import ThemeToggle from '../../../components/ThemeToggle';

const isViolation = (result) => result?.metadata?.kind !== 'patch';
const REMOTE_REPO_PATTERN = /^(?:https?:\/\/|git@|ssh:\/\/)/i;

function canApplyDirectly(repoPath) {
  return repoPath && !REMOTE_REPO_PATTERN.test(repoPath.trim());
}

function defaultSocketUrl() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/ws/scan`;
}

function getAgentSummary(agents) {
  if (!agents.length) {
    return {
      label: 'Standby',
      dot: 'bg-text-dim/60',
      text: 'text-text-dim',
    };
  }
  if (agents.some((agent) => agent.status === AGENT_STATUSES.ERROR)) {
    return {
      label: 'Error',
      dot: 'bg-bad',
      text: 'text-bad',
    };
  }
  if (agents.some((agent) => agent.status === AGENT_STATUSES.RUNNING)) {
    return {
      label: 'Running',
      dot: 'bg-warn animate-pulse-dot',
      text: 'text-warn',
    };
  }
  if (agents.every((agent) => agent.status === AGENT_STATUSES.DONE)) {
    return {
      label: 'Done',
      dot: 'bg-good',
      text: 'text-good',
    };
  }
  return {
    label: 'Idle',
    dot: 'bg-text-dim/60',
    text: 'text-text-dim',
  };
}

export function ScanPage() {
  const wsUrl = import.meta.env.VITE_WS_URL || defaultSocketUrl();
  const useMock = import.meta.env.VITE_USE_MOCK === '1';

  const [state, { fixesGenerated, handleEvent, runRequested }] = useRunState();
  const [selectedViolationId, setSelectedViolationId] = useState(null);
  const [fixRequested, setFixRequested] = useState(false);
  const [fixError, setFixError] = useState(null);
  const [fixingFindingId, setFixingFindingId] = useState(null);
  const [acceptingPatchId, setAcceptingPatchId] = useState(null);
  const [targetRepoPath, setTargetRepoPath] = useState('');
  const generateFixes = useGenerateFixesMutation();

  const { status: connectionStatus, retryCount, maxRetries, send } = useWebSocket({
    url: wsUrl,
    mock: useMock,
    onMessage: handleEvent,
    mockFactory: createDomainMockServer,
  });

  const onScan = useCallback(
    (input) => {
      const repoPath = input.trim();
      if (!repoPath) return;
      setTargetRepoPath(repoPath);
      setFixRequested(false);
      setFixError(null);
      setFixingFindingId(null);
      setAcceptingPatchId(null);
      runRequested(repoPath);
      send({ repo_path: repoPath });
    },
    [runRequested, send],
  );

  const agentList = useMemo(() => Object.values(state.agents), [state.agents]);
  const agentSummary = useMemo(() => getAgentSummary(agentList), [agentList]);
  const violations = useMemo(
    () => state.results.filter(isViolation).sort(sortBySeverity),
    [state.results],
  );
  const hasPatches = useMemo(
    () => state.results.some((result) => result?.metadata?.kind === 'patch'),
    [state.results],
  );
  const acceptedFindingIds = useMemo(
    () =>
      new Set(
        state.results
          .filter((result) => result?.metadata?.kind === 'patch')
          .filter((patch) => patch.metadata?.applied || patch.metadata?.accepted)
          .map((patch) => patch.metadata?.violationCode)
          .filter(Boolean),
      ),
    [state.results],
  );
  const remainingViolations = useMemo(
    () => violations.filter((violation) => !acceptedFindingIds.has(violation.id)),
    [acceptedFindingIds, violations],
  );
  const selectedViolation = useMemo(
    () =>
      violations.find((result) => result.id === selectedViolationId) ??
      violations[0] ??
      null,
    [selectedViolationId, violations],
  );
  const isRunning = state.status === RUN_STATUSES.RUNNING;
  const isFixing = fixRequested || generateFixes.isPending;
  const errorMessage = state.error ?? fixError;
  const actionStateByResultId = useMemo(
    () => (fixingFindingId ? { [fixingFindingId]: 'fixing' } : {}),
    [fixingFindingId],
  );

  const requestFixes = useCallback(
    async (findings, fixingId = null, options = {}) => {
      const repoPath = targetRepoPath || state.repoPath;
      if (isFixing) return;
      if (!repoPath) {
        setFixError('Run a scan before generating fixes for this finding.');
        return;
      }
      if (!findings.length) return;
      const {
        apply = false,
        acceptGeneratedInUi = false,
        acceptedFindingIds = [],
        mergePatches = false,
        rescan = false,
        patchId = null,
        acceptInUi = false,
      } = options;
      setFixRequested(true);
      setFixingFindingId(fixingId);
      setAcceptingPatchId(patchId);
      setFixError(null);
      try {
        const summary = await generateFixes.mutateAsync({
          repoPath,
          findings,
          apply,
          rescan,
        });
        if (apply && !summary.applied) {
          const failure = summary.failures?.find((item) => item.code === 'apply_unavailable') ??
            summary.failures?.[0];
          throw new Error(
            failure?.message ?? 'The patch could not be accepted.',
          );
        }
        if (rescan && typeof summary.rescan_summary?.score !== 'number') {
          throw new Error('The patch was generated, but the score could not be refreshed.');
        }
        fixesGenerated(summary, {
          acceptGeneratedPatches: acceptGeneratedInUi,
          acceptedFindingIds,
          acceptedPatchId: acceptInUi ? patchId : null,
          mergePatches,
        });
      } catch (error) {
        setFixError(error instanceof Error ? error.message : 'Fix generation failed');
      } finally {
        setFixRequested(false);
        setFixingFindingId(null);
        setAcceptingPatchId(null);
      }
    },
    [fixesGenerated, generateFixes, isFixing, state.repoPath, targetRepoPath],
  );

  const onResultAction = useCallback(
    (actionId, resultId) => {
      if (actionId !== 'auto-fix') return;
      const finding = violations.find((result) => result.id === resultId);
      if (!finding) return;
      void requestFixes([finding], finding.id, { mergePatches: hasPatches });
    },
    [hasPatches, requestFixes, violations],
  );

  const onFixAll = useCallback(() => {
    const repoPath = targetRepoPath || state.repoPath;
    const applyDirectly = canApplyDirectly(repoPath);
    void requestFixes(remainingViolations, null, {
      acceptGeneratedInUi: !applyDirectly,
      acceptedFindingIds: [
        ...acceptedFindingIds,
        ...remainingViolations.map((violation) => violation.id),
      ],
      apply: applyDirectly,
      mergePatches: true,
      rescan: true,
    });
  }, [acceptedFindingIds, remainingViolations, requestFixes, state.repoPath, targetRepoPath]);

  const onAcceptPatch = useCallback(
    (patch) => {
      const findingId = patch?.metadata?.violationCode;
      const finding = violations.find((result) => result.id === findingId);
      if (!finding) {
        setFixError('The original finding for this patch is no longer available.');
        return;
      }
      const repoPath = targetRepoPath || state.repoPath;
      const applyDirectly = canApplyDirectly(repoPath);
      void requestFixes([finding], finding.id, {
        acceptInUi: !applyDirectly,
        acceptedFindingIds: applyDirectly
          ? Array.from(acceptedFindingIds)
          : [...acceptedFindingIds, finding.id],
        apply: applyDirectly,
        mergePatches: true,
        rescan: true,
        patchId: patch.id,
      });
    },
    [acceptedFindingIds, requestFixes, state.repoPath, targetRepoPath, violations],
  );

  useEffect(() => {
    if (hasPatches) setFixRequested(false);
  }, [hasPatches]);

  useEffect(() => {
    if (violations.length === 0) {
      setSelectedViolationId(null);
      return;
    }
    if (!selectedViolationId || !violations.some((v) => v.id === selectedViolationId)) {
      setSelectedViolationId(violations[0].id);
    }
  }, [selectedViolationId, violations]);

  return (
    <div className="mx-auto flex h-full max-w-7xl flex-col gap-5 overflow-hidden px-5 py-5 md:px-8">
      <header className="glass-panel-strong theme-transition flex shrink-0 items-center justify-between gap-4 rounded-lg px-4 py-3">
        <div className="min-w-0">
          <h1 className="truncate text-base font-semibold tracking-tight text-text">
            Compliance Codex
          </h1>
          <div className="mt-0.5 font-mono text-[11px] text-text-dim">
            Evidence review workspace
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <ThemeToggle />
          <ConnectionBadge
            status={connectionStatus}
            retryCount={retryCount}
            maxRetries={maxRetries}
          />
        </div>
      </header>

      {errorMessage && (
        <div className="glass-subpanel theme-transition flex w-full items-center justify-center rounded-lg border-bad/40 bg-bad/10 p-4 text-center text-sm text-bad">
          {errorMessage}
        </div>
      )}

      <main className="grid min-h-0 flex-1 grid-cols-1 gap-5 overflow-y-auto lg:grid-cols-[360px_1fr] lg:overflow-hidden">
        <aside className="flex flex-col gap-5 lg:sticky lg:top-5 lg:self-start">
          <ScanPanel disabled={isRunning} onScan={onScan} />

          <section className="glass-panel-soft theme-transition rounded-lg p-4">
            <div className="mb-3 flex items-baseline justify-between gap-3">
              <h2 className="text-sm font-medium text-text">
                Agents
              </h2>
              <div className="flex items-center gap-2">
                <span className={clsx('h-1.5 w-1.5 rounded-full', agentSummary.dot)} />
                <span className={clsx('text-[11px] font-medium uppercase tracking-wider', agentSummary.text)}>
                  {agentSummary.label}
                </span>
                <span className="font-mono text-[11px] text-text-dim">
                  {agentList.length || 3}
                </span>
              </div>
            </div>
            <AgentStatusBoard agents={agentList} />
          </section>
        </aside>

        <section className="flex min-h-0 min-w-0 flex-col gap-5 lg:overflow-y-auto lg:pr-1">
          <div className="grid shrink-0 grid-cols-1 gap-5 xl:grid-cols-[240px_1fr]">
            <ComplianceScore score={state.score} />

            <section className="glass-panel theme-transition min-w-0 rounded-lg p-4">
              <div className="mb-4 flex items-baseline justify-between gap-3">
                <h2 className="text-sm font-medium text-text">
                  Selected Violation
                </h2>
                <span className="font-mono text-[11px] text-text-dim">
                  {selectedViolation?.metadata?.violationCode ?? 'awaiting scan'}
                </span>
              </div>
              {selectedViolation ? (
                <ViolationCard
                  result={selectedViolation}
                  onAction={onResultAction}
                  variant="featured"
                  actionsDisabled={isFixing}
                  actionStateById={actionStateByResultId}
                />
              ) : (
                <div className="glass-subpanel theme-transition rounded-lg border-dashed p-8 text-center text-sm text-text-dim shadow-none">
                  Run a scan to review the highest-risk finding here.
                </div>
              )}
            </section>
          </div>

          <div className="shrink-0">
            <FixPanel
              results={state.results}
              runId={state.runId}
              status={isFixing ? 'fixing' : 'idle'}
              onFixAll={onFixAll}
              onAcceptPatch={onAcceptPatch}
              acceptingPatchId={acceptingPatchId}
            />
          </div>

          <ViolationList
            results={state.results}
            onAction={onResultAction}
            selectedId={selectedViolation?.id}
            onSelect={setSelectedViolationId}
            actionsDisabled={isFixing}
            actionStateById={actionStateByResultId}
            compact
          />
        </section>
      </main>
    </div>
  );
}
