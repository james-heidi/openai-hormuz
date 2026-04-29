import { EVT, AGENT_STATUSES } from './protocol';

/**
 * Domain mock server for Compliance Codex. Emits the same wire protocol as
 * the real backend would, with realistic GDPR + AU Privacy Act metadata
 * embedded in each finding. Lets `npm run dev` walk the full demo flow
 * (scan → 10 violations → score 24 → auto-fix → 5 patches → score 91)
 * without an orchestrator running.
 *
 * Two scripted phases:
 *   1. `run.start`           → 10 violations stream in, score lands at 24
 *   2. `action.invoke`        → 5 patches stream in, score animates to 91
 *      (actionId='auto-fix-all')
 *
 * `VITE_MOCK_SPEED=fast` halves all timings for video recording.
 */

const SPEED =
  typeof import.meta !== 'undefined' &&
  import.meta.env?.VITE_MOCK_SPEED === 'fast'
    ? 0.5
    : 1;

const t = (ms) => Math.round(ms * SPEED);

const AGENTS = [
  { id: 'pii-scanner', label: 'PII Scanner' },
  { id: 'api-auditor', label: 'API Auditor' },
  { id: 'auth-checker', label: 'Auth Checker' },
];

// ───────────── Regulation reference data ─────────────
// Mirrors what the backend's Regulation Mapper would produce.
const GDPR = {
  ART_32: {
    article: 'Art. 32',
    title: 'Security of processing',
    summary:
      'The controller and processor shall implement appropriate technical and organisational measures to ensure a level of security appropriate to the risk.',
    fine: 'Up to €10M or 2% global turnover',
    url: 'https://gdpr-info.eu/art-32-gdpr/',
  },
  ART_25: {
    article: 'Art. 25',
    title: 'Data protection by design and by default',
    summary:
      'Implement appropriate technical and organisational measures designed to implement data-protection principles in an effective manner.',
    fine: 'Up to €10M or 2% global turnover',
    url: 'https://gdpr-info.eu/art-25-gdpr/',
  },
  ART_5_1_C: {
    article: 'Art. 5(1)(c)',
    title: 'Data minimisation',
    summary:
      'Personal data shall be adequate, relevant and limited to what is necessary in relation to the purposes for which they are processed.',
    fine: 'Up to €20M or 4% global turnover',
    url: 'https://gdpr-info.eu/art-5-gdpr/',
  },
  ART_5_1_E: {
    article: 'Art. 5(1)(e)',
    title: 'Storage limitation',
    summary:
      'Personal data shall be kept in a form which permits identification of data subjects for no longer than is necessary.',
    fine: 'Up to €20M or 4% global turnover',
    url: 'https://gdpr-info.eu/art-5-gdpr/',
  },
  ART_6: {
    article: 'Art. 6',
    title: 'Lawfulness of processing',
    summary:
      'Processing shall be lawful only if and to the extent that at least one of the listed conditions applies (e.g. consent, contract, legal obligation).',
    fine: 'Up to €20M or 4% global turnover',
    url: 'https://gdpr-info.eu/art-6-gdpr/',
  },
};

const APP = {
  APP_11: {
    principle: 'APP 11',
    title: 'Security of personal information',
    summary:
      'An APP entity must take such steps as are reasonable in the circumstances to protect the information from misuse, interference, loss, and unauthorised access, modification or disclosure.',
    fine: 'AU$50M / 30% turnover',
    url: 'https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-quick-reference',
  },
  APP_3_6: {
    principle: 'APP 3 & 6',
    title: 'Collection and use of personal information',
    summary:
      'Only collect personal information reasonably necessary for the entity\'s functions, and use it only for the primary purpose of collection.',
    fine: 'AU$50M / 30% turnover',
    url: 'https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-quick-reference',
  },
  APP_6: {
    principle: 'APP 6',
    title: 'Use or disclosure of personal information',
    summary:
      'Only use or disclose personal information for the primary purpose of collection, unless an exception applies (consent, related secondary purpose, etc.).',
    fine: 'AU$50M / 30% turnover',
    url: 'https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-quick-reference',
  },
};

// ───────────── Violations (match Notion demo repo §3) ─────────────
const VIOLATIONS = [
  {
    agentId: 'pii-scanner',
    severity: 'critical',
    title: 'Plaintext PII in log output',
    location: 'demo_repo/auth.py:14',
    description:
      'Login attempt logs include the user\'s email and password in plaintext, exposing credentials in any log aggregator.',
    metadata: {
      violationCode: 'PII-LOG-001',
      gdpr: GDPR.ART_32,
      app: APP.APP_11,
    },
    actions: [
      { label: 'Auto-fix', actionId: 'auto-fix' },
      { label: 'Suppress', actionId: 'suppress' },
    ],
  },
  {
    agentId: 'auth-checker',
    severity: 'critical',
    title: 'Hardcoded JWT secret',
    location: 'demo_repo/config.py:7',
    description:
      'JWT signing secret is committed to source. Anyone with repo access can forge tokens.',
    metadata: {
      violationCode: 'AUTH-SECRET-001',
      gdpr: GDPR.ART_32,
      app: APP.APP_11,
    },
    actions: [
      { label: 'Auto-fix', actionId: 'auto-fix' },
      { label: 'Suppress', actionId: 'suppress' },
    ],
  },
  {
    agentId: 'auth-checker',
    severity: 'critical',
    title: 'SQL injection via f-string',
    location: 'demo_repo/auth.py:42',
    description:
      'User input is interpolated directly into a SQL query string. A crafted email value can read or modify arbitrary rows.',
    metadata: {
      violationCode: 'AUTH-SQLI-002',
      gdpr: GDPR.ART_32,
      app: APP.APP_11,
    },
    actions: [
      { label: 'Auto-fix', actionId: 'auto-fix' },
      { label: 'Suppress', actionId: 'suppress' },
    ],
  },
  {
    agentId: 'api-auditor',
    severity: 'high',
    title: 'API response over-exposure',
    location: 'demo_repo/api/users.py:23',
    description:
      'Endpoint returns the full ORM dict, including password_hash, ssn, and date_of_birth. Violates data minimisation.',
    metadata: {
      violationCode: 'API-EXPOSE-003',
      gdpr: GDPR.ART_5_1_C,
      app: APP.APP_3_6,
    },
    actions: [
      { label: 'Auto-fix', actionId: 'auto-fix' },
      { label: 'Suppress', actionId: 'suppress' },
    ],
  },
  {
    agentId: 'auth-checker',
    severity: 'critical',
    title: 'Admin endpoint missing auth middleware',
    location: 'demo_repo/api/users.py:48',
    description:
      '`/admin/all-users` is callable by any unauthenticated client. Returns full user list.',
    metadata: {
      violationCode: 'AUTH-MISS-004',
      gdpr: GDPR.ART_25,
      app: APP.APP_11,
    },
    actions: [
      { label: 'Auto-fix', actionId: 'auto-fix' },
      { label: 'Suppress', actionId: 'suppress' },
    ],
  },
  {
    agentId: 'api-auditor',
    severity: 'high',
    title: 'Stack trace returned to client',
    location: 'demo_repo/middleware.py:18',
    description:
      'Generic exception handler echoes `traceback.format_exc()` to the response body, leaking internal paths and dependency versions.',
    metadata: {
      violationCode: 'API-TRACE-005',
      gdpr: GDPR.ART_32,
      app: APP.APP_11,
    },
    actions: [
      { label: 'Auto-fix', actionId: 'auto-fix' },
      { label: 'Suppress', actionId: 'suppress' },
    ],
  },
  {
    agentId: 'pii-scanner',
    severity: 'critical',
    title: 'Plaintext password storage',
    location: 'demo_repo/models.py:11',
    description:
      'User.password is stored as a plain `String` column with no hashing. A DB dump leaks every credential.',
    metadata: {
      violationCode: 'PII-STORE-006',
      gdpr: GDPR.ART_32,
      app: APP.APP_11,
    },
    actions: [
      { label: 'Auto-fix', actionId: 'auto-fix' },
      { label: 'Suppress', actionId: 'suppress' },
    ],
  },
  {
    agentId: 'pii-scanner',
    severity: 'high',
    title: 'PII forwarded to third party without consent',
    location: 'demo_repo/email_service.py:31',
    description:
      'Sends user email, date of birth, and SSN to an external analytics endpoint. No consent record, no DPA in place.',
    metadata: {
      violationCode: 'PII-EXFIL-007',
      gdpr: GDPR.ART_6,
      app: APP.APP_6,
    },
    actions: [
      { label: 'Auto-fix', actionId: 'auto-fix' },
      { label: 'Suppress', actionId: 'suppress' },
    ],
  },
  {
    agentId: 'pii-scanner',
    severity: 'medium',
    title: 'No data-retention policy on User model',
    location: 'demo_repo/models.py:5',
    description:
      'User table has no `created_at` / `deleted_at` columns and no scheduled deletion. Violates storage-limitation principle.',
    metadata: {
      violationCode: 'PII-RETAIN-008',
      gdpr: GDPR.ART_5_1_E,
      app: APP.APP_11,
    },
    actions: [
      { label: 'Auto-fix', actionId: 'auto-fix' },
      { label: 'Suppress', actionId: 'suppress' },
    ],
  },
  {
    agentId: 'api-auditor',
    severity: 'medium',
    title: 'Permissive CORS policy',
    location: 'demo_repo/middleware.py:9',
    description:
      'CORS configured with `allow_origins=["*"]`. Any origin can read authenticated responses if cookies are sent.',
    metadata: {
      violationCode: 'API-CORS-009',
      gdpr: GDPR.ART_32,
      app: APP.APP_11,
    },
    actions: [
      { label: 'Auto-fix', actionId: 'auto-fix' },
      { label: 'Suppress', actionId: 'suppress' },
    ],
  },
];

// ───────────── Patches (5 — covers the worst offenders) ─────────────
const PATCHES = [
  {
    title: 'Redact credentials from login logs',
    file: 'demo_repo/auth.py',
    violationCode: 'PII-LOG-001',
    diffLines: [
      { type: ' ', text: 'def login(email, password):' },
      { type: '-', text: '    logger.info(f"Login attempt: email={email}, password={password}")' },
      { type: '+', text: '    logger.info("login.attempt", extra={"email_hash": hash_email(email)})' },
      { type: ' ', text: '    user = authenticate(email, password)' },
    ],
  },
  {
    title: 'Move JWT secret to environment',
    file: 'demo_repo/config.py',
    violationCode: 'AUTH-SECRET-001',
    diffLines: [
      { type: ' ', text: 'import os' },
      { type: '-', text: 'JWT_SECRET = "super-secret-key-do-not-share-12345"' },
      { type: '+', text: 'JWT_SECRET = os.environ.get("JWT_SECRET")' },
      { type: '+', text: 'if not JWT_SECRET:' },
      { type: '+', text: '    raise RuntimeError("JWT_SECRET environment variable is required")' },
    ],
  },
  {
    title: 'Use parameterised SQL query',
    file: 'demo_repo/auth.py',
    violationCode: 'AUTH-SQLI-002',
    diffLines: [
      { type: ' ', text: 'def get_user(email_input):' },
      { type: '-', text: '    query = f"SELECT * FROM users WHERE email = \'{email_input}\'"' },
      { type: '-', text: '    return db.execute(query)' },
      { type: '+', text: '    return db.execute(' },
      { type: '+', text: '        "SELECT * FROM users WHERE email = %s",' },
      { type: '+', text: '        (email_input,),' },
      { type: '+', text: '    )' },
    ],
  },
  {
    title: 'Return safe DTO from user endpoint',
    file: 'demo_repo/api/users.py',
    violationCode: 'API-EXPOSE-003',
    diffLines: [
      { type: ' ', text: '@app.get("/users/{id}")' },
      { type: ' ', text: 'def get_user(id: int):' },
      { type: ' ', text: '    user = db.query(User).get(id)' },
      { type: '-', text: '    return user.__dict__  # exposes password_hash, ssn, dob' },
      { type: '+', text: '    return UserPublic.model_validate(user)  # only safe fields' },
    ],
  },
  {
    title: 'Hash passwords with bcrypt',
    file: 'demo_repo/models.py',
    violationCode: 'PII-STORE-006',
    diffLines: [
      { type: '+', text: 'from passlib.context import CryptContext' },
      { type: '+', text: '' },
      { type: '+', text: 'pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")' },
      { type: '+', text: '' },
      { type: ' ', text: 'class User(Base):' },
      { type: '-', text: '    password = Column(String)  # not hashed' },
      { type: '+', text: '    password_hash = Column(String, nullable=False)' },
      { type: '+', text: '' },
      { type: '+', text: '    def set_password(self, raw: str) -> None:' },
      { type: '+', text: '        self.password_hash = pwd_ctx.hash(raw)' },
    ],
  },
];

export function createDomainMockServer() {
  const subscribers = new Set();
  const timers = new Set();

  const emit = (type, payload) => {
    for (const cb of subscribers) {
      try {
        cb({ type, payload });
      } catch (err) {
        console.error('[domainMockServer] subscriber threw', err);
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

  const playScan = (runId) => {
    clearAll();

    schedule(0, () => emit(EVT.RUN_ACCEPTED, { runId, agents: AGENTS }));

    schedule(200, () => {
      for (const a of AGENTS) {
        emit(EVT.AGENT_STATUS, {
          runId,
          agentId: a.id,
          status: AGENT_STATUSES.RUNNING,
          message: `Spawning Codex worktree for ${a.label}…`,
        });
      }
    });

    const VIOL_TIMINGS = [600, 950, 1300, 1700, 2100, 2500, 2900, 3300, 3700, 4100];
    VIOLATIONS.forEach((v, i) => {
      schedule(VIOL_TIMINGS[i], () =>
        emit(EVT.RESULT_ADD, {
          runId,
          agentId: v.agentId,
          result: {
            id: `${runId}_v${i + 1}`,
            agentId: v.agentId,
            title: v.title,
            description: v.description,
            severity: v.severity,
            location: v.location,
            metadata: v.metadata,
            actions: v.actions,
          },
        }),
      );
    });

    schedule(4500, () => emit(EVT.SCORE_UPDATE, { runId, score: 24 }));

    schedule(4700, () => {
      for (const a of AGENTS) {
        emit(EVT.AGENT_STATUS, {
          runId,
          agentId: a.id,
          status: AGENT_STATUSES.DONE,
          message: 'Scan complete.',
        });
      }
    });

    schedule(4800, () => emit(EVT.RUN_COMPLETE, { runId }));
  };

  const playAutoFix = (runId) => {
    clearAll();

    schedule(200, () => {
      for (const a of AGENTS) {
        emit(EVT.AGENT_STATUS, {
          runId,
          agentId: a.id,
          status: AGENT_STATUSES.RUNNING,
          message: 'Generating patches in isolated worktrees…',
        });
      }
    });

    const PATCH_TIMINGS = [700, 1200, 1700, 2200, 2700];
    PATCHES.forEach((p, i) => {
      schedule(PATCH_TIMINGS[i], () =>
        emit(EVT.RESULT_ADD, {
          runId,
          agentId: 'auth-checker', // attribution — any agent fine
          result: {
            id: `${runId}_p${i + 1}`,
            agentId: 'auth-checker',
            title: p.title,
            severity: undefined,
            location: p.file,
            metadata: {
              kind: 'patch',
              violationCode: p.violationCode,
              file: p.file,
              diffLines: p.diffLines,
            },
            actions: [{ label: 'Apply', actionId: 'apply-patch' }],
          },
        }),
      );
    });

    schedule(3300, () =>
      emit(EVT.SCORE_UPDATE, { runId, score: 91, prev: 24 }),
    );

    schedule(3500, () => {
      for (const a of AGENTS) {
        emit(EVT.AGENT_STATUS, {
          runId,
          agentId: a.id,
          status: AGENT_STATUSES.DONE,
          message: 'Patches generated.',
        });
      }
    });

    schedule(3700, () => emit(EVT.RUN_COMPLETE, { runId }));
  };

  return {
    send(msg) {
      if (!msg || typeof msg !== 'object') return;
      if (msg.type === EVT.RUN_START) {
        playScan(msg.payload?.runId ?? `mock_${Date.now()}`);
      } else if (msg.type === EVT.RUN_CANCEL) {
        clearAll();
      } else if (msg.type === EVT.ACTION_INVOKE) {
        const { actionId, runId } = msg.payload ?? {};
        if (actionId === 'auto-fix-all' && runId) {
          playAutoFix(runId);
        }
        // Single-violation auto-fix and suppress are no-ops in the mock.
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
