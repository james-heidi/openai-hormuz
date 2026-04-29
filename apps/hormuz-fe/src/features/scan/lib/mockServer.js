import { EVT, AGENT_STATUSES } from './protocol';

/**
 * In-process mock that emits the same wire protocol the real backend
 * would. Lets `npm run dev` work standalone with no orchestrator running.
 *
 * Deterministic schedule so demo recordings look the same every take.
 * `VITE_MOCK_SPEED=fast` halves all timings.
 */

const SPEED =
  typeof import.meta !== 'undefined' &&
  import.meta.env?.VITE_MOCK_SPEED === 'fast'
    ? 0.5
    : 1;

const t = (ms) => Math.round(ms * SPEED);

const AGENTS = [
  { id: 'agent-a', label: 'Agent A' },
  { id: 'agent-b', label: 'Agent B' },
  { id: 'agent-c', label: 'Agent C' },
];

const SAMPLE_RESULTS = [
  { agentId: 'agent-a', severity: 'high', title: 'Sample finding 1', location: 'src/sample/a1.ext:12' },
  { agentId: 'agent-b', severity: 'medium', title: 'Sample finding 2', location: 'src/sample/b1.ext:48' },
  { agentId: 'agent-a', severity: 'critical', title: 'Sample finding 3', location: 'src/sample/a2.ext:7' },
  { agentId: 'agent-c', severity: 'low', title: 'Sample finding 4', location: 'src/sample/c1.ext:101' },
  { agentId: 'agent-b', severity: 'high', title: 'Sample finding 5', location: 'src/sample/b2.ext:30' },
  { agentId: 'agent-c', severity: 'medium', title: 'Sample finding 6', location: 'src/sample/c2.ext:64' },
];

export function createMockServer() {
  const subscribers = new Set();
  const timers = new Set();

  const emit = (type, payload) => {
    for (const cb of subscribers) {
      try {
        cb({ type, payload });
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

  const playRun = (runId) => {
    clearAll();

    schedule(0, () =>
      emit(EVT.RUN_ACCEPTED, { runId, agents: AGENTS }),
    );

    schedule(150, () => {
      for (const a of AGENTS) {
        emit(EVT.AGENT_STATUS, {
          runId,
          agentId: a.id,
          status: AGENT_STATUSES.RUNNING,
        });
      }
    });

    const RESULT_TIMINGS = [800, 1300, 1800, 2700, 3400, 4100];
    SAMPLE_RESULTS.forEach((r, i) => {
      schedule(RESULT_TIMINGS[i], () =>
        emit(EVT.RESULT_ADD, {
          runId,
          agentId: r.agentId,
          result: {
            id: `${runId}_r${i + 1}`,
            agentId: r.agentId,
            title: r.title,
            description: 'Mock finding emitted by the in-process mock server.',
            severity: r.severity,
            location: r.location,
            metadata: {},
          },
        }),
      );
    });

    schedule(2200, () =>
      emit(EVT.SCORE_UPDATE, { runId, score: 50 }),
    );
    schedule(5300, () =>
      emit(EVT.SCORE_UPDATE, { runId, score: 72 }),
    );

    schedule(5500, () => {
      for (const a of AGENTS) {
        emit(EVT.AGENT_STATUS, {
          runId,
          agentId: a.id,
          status: AGENT_STATUSES.DONE,
        });
      }
    });

    schedule(5700, () => emit(EVT.RUN_COMPLETE, { runId }));
  };

  return {
    /** Mock-side `send` mirrors a real WS client → server message. */
    send(msg) {
      if (!msg || typeof msg !== 'object') return;
      if (msg.type === EVT.RUN_START) {
        playRun(msg.payload?.runId ?? `mock_${Date.now()}`);
      } else if (msg.type === EVT.RUN_CANCEL) {
        clearAll();
      } else if (msg.type === EVT.ACTION_INVOKE) {
        // No-op in the generic mock; a domain mock would respond here.
      }
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
