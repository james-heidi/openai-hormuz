# OpenAI Hormuz

Compliance Codex is a hackathon project for scanning source code with parallel
agent workers, mapping privacy/security findings to GDPR and Australian Privacy
Principles, and preparing fix output for review.

This repo is scaffolded as a small monorepo inspired by the mature
[`scribe-workspace`](https://github.com/james-heidi/scribe-workspace.git)
template: root Taskfile orchestration, `apps/*` services, uv for Python, pnpm
for frontend, FastAPI module monolith, feature-sliced React, OpenAPI sync, and
architecture notes under `docs/architecture/`.

## Getting Started

```bash
cp .env.example .env
task install

# Optional local infra for Redis and tracing
task infra:up

# Terminal 1
task be:dev

# Terminal 2
task fe:dev
```

## Local URLs

| Service | URL | Started by |
| --- | --- | --- |
| Frontend | http://localhost:3000 | `task fe:dev` |
| Backend | http://localhost:4000 | `task be:dev` |
| Backend health | http://localhost:4000/api/health | `task be:dev` |
| Jaeger UI | http://localhost:16686 | `task infra:up` |

## Repository Layout

```text
openai-hormuz/
├── apps/
│   ├── hormuz-be/        # FastAPI backend
│   └── hormuz-fe/        # Vite React frontend
├── demo_repo/            # Deterministic demo target with known violations
├── docs/
│   └── architecture/     # ADRs copied forward from the scribe-workspace style
├── docker-compose.yml
└── Taskfile.yml
```

## Demo Flow

1. Start backend and frontend.
2. Enter the absolute path to `demo_repo` in the frontend.
3. Trigger a scan.
4. Watch three scanner workers stream status over WebSocket.
5. Review findings mapped to GDPR and APP clauses.

The current backend uses deterministic rule scanners so the scaffold is
demo-safe. The OpenAI Agents SDK integration point is the `ScanAgent` port in
`apps/hormuz-be/modules/scan/domain/ports.py`.

