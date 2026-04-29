import { AGENT_STATUSES, EVT } from './protocol';

const SPEED =
  typeof import.meta !== 'undefined' &&
  import.meta.env?.VITE_MOCK_SPEED === 'fast'
    ? 0.5
    : 1;

const t = (ms) => Math.round(ms * SPEED);

const AGENTS = ['Agent A', 'Agent B', 'Agent C'];

const SAMPLE_FINDINGS = [
  { agent: 'Agent A', severity: 'high', title: 'Sample finding 1', file_path: 'src/sample/a1.ext', line: 12 },
  { agent: 'Agent B', severity: 'medium', title: 'Sample finding 2', file_path: 'src/sample/b1.ext', line: 48 },
  { agent: 'Agent A', severity: 'critical', title: 'Sample finding 3', file_path: 'src/sample/a2.ext', line: 7 },
  { agent: 'Agent C', severity: 'low', title: 'Sample finding 4', file_path: 'src/sample/c1.ext', line: 101 },
  { agent: 'Agent B', severity: 'high', title: 'Sample finding 5', file_path: 'src/sample/b2.ext', line: 30 },
  { agent: 'Agent C', severity: 'medium', title: 'Sample finding 6', file_path: 'src/sample/c2.ext', line: 64 },
].map((finding, index) => ({
  id: `mock:${index + 1}`,
  violation_type: `MOCK_${index + 1}`,
  category: 'mock',
  context: null,
  description: 'Mock finding emitted by the in-process mock server.',
  snippet: null,
  regulations: [],
  regulation_warning: null,
  recommendation: 'Review the mock finding.',
  remediation_hint: 'Review the mock finding.',
  ...finding,
}));

export function createMockServer() {
  const subscribers = new Set();
  const timers = new Set();

  const emit = (type, payload) => {
    for (const cb of subscribers) {
      try {
        cb({ type, ...payload });
      } catch (err) {
        console.error('[mockServer] subscriber threw', err);
      }
    }
  };

  const schedule = (ms, fn) => {
    const id = setTimeout(() => {
      timers.delete(id);
      fn();
    }, t(ms));
    timers.add(id);
  };

  const clearAll = () => {
    for (const id of timers) clearTimeout(id);
    timers.clear();
  };

  const playRun = (repoPath) => {
    clearAll();

    schedule(0, () => emit(EVT.SCAN_STARTED, { repo_path: repoPath, agents: AGENTS }));

    schedule(150, () => {
      for (const agent of AGENTS) {
        emit(EVT.AGENT_UPDATE, {
          update: { agent, status: AGENT_STATUSES.RUNNING, message: 'Scanning', progress: 5 },
        });
      }
    });

    const resultTimings = [800, 1300, 1800, 2700, 3400, 4100];
    SAMPLE_FINDINGS.forEach((finding, index) => {
      schedule(resultTimings[index], () => emit(EVT.FINDING, { finding }));
    });

    schedule(5500, () => {
      for (const agent of AGENTS) {
        emit(EVT.AGENT_UPDATE, {
          update: { agent, status: AGENT_STATUSES.DONE, message: 'Scan complete', progress: 100 },
        });
      }
    });

    schedule(5700, () =>
      emit(EVT.SCAN_COMPLETE, {
        summary: {
          scan_status: 'complete',
          score: 72,
          total_findings: SAMPLE_FINDINGS.length,
          counts_by_severity: { critical: 1, high: 2, medium: 2, low: 1 },
          counts_by_agent: { 'Agent A': 2, 'Agent B': 2, 'Agent C': 2 },
          findings: SAMPLE_FINDINGS,
          failed_agents: [],
        },
      }),
    );
  };

  return {
    send(msg) {
      if (!msg || typeof msg !== 'object') return;
      if (msg.repo_path) playRun(msg.repo_path);
    },
    subscribe(cb) {
      subscribers.add(cb);
      return () => subscribers.delete(cb);
    },
    close() {
      clearAll();
      subscribers.clear();
    },
  };
}
