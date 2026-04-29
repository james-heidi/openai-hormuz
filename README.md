# OpenAI Hormuz

Compliance Codex is a hackathon project for scanning source code with parallel
agent workers, mapping privacy/security findings to GDPR and Australian Privacy
Principles, and preparing fix output for review.

This repo is scaffolded as a small monorepo with root Taskfile orchestration,
`apps/*` services, uv for Python, pnpm for frontend, FastAPI module monolith,
feature-sliced React, OpenAPI sync, and architecture notes under
`docs/architecture/`.

## Getting Started

```bash
cp .env.example .env
# Fill OPENAI_API_KEY in .env before starting a scan.
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

## Backend Environment

The root `Taskfile.yml` loads `.env.local` and `.env` before starting backend
tasks. FastAPI app code does not load dotenv files directly.

| Variable | Required | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | Yes for scans | OpenAI credential used by the Agents SDK scan flow. Missing or placeholder values return `missing_openai_config` when a scan starts. |
| `OPENAI_AGENT_MODEL` | No | Optional Agents SDK model override. Leave unset to use SDK defaults. |
| `OPENAI_PROJECT` | No | Optional OpenAI project header for API calls. |
| `OPENAI_ORG_ID` | No | Optional OpenAI organization header for API calls. |
| `OPENAI_BASE_URL` | No | Optional OpenAI-compatible API base URL. |
| `SCAN_ALLOWED_ROOTS` | No | Colon-separated directories the scanner may read. Defaults to this repo root. |
| `SCAN_WORKTREE_ROOT` | No | Directory reserved for GitPython worktree operations. Defaults to `.worktrees`. |
| `CORS_ORIGINS` | No | Comma-separated frontend origins. Defaults to `http://localhost:3000`. |
| `GITHUB_TOKEN` | No | Enables optional GitHub PR creation only when paired with `GITHUB_REPOSITORY`. |
| `GITHUB_REPOSITORY` | No | Repository slug for optional PR creation, for example `owner/repo`. |
| `GITHUB_BASE_BRANCH` | No | Base branch for optional PR creation. Defaults to `main`. |

## Repository Layout

```text
openai-hormuz/
├── apps/
│   ├── hormuz-be/        # FastAPI backend
│   └── hormuz-fe/        # Vite React frontend
├── docs/
│   └── architecture/     # ADRs for long-lived repo conventions
├── docker-compose.yml
└── Taskfile.yml
```

## Demo Target

The deterministic scan target now lives in a standalone private repository:
[openai-hormuz-demo-repo](https://github.com/james-heidi/openai-hormuz-demo-repo).

## Demo Flow

1. Clone the demo target repository separately.
2. Start backend and frontend.
3. Enter the absolute path to the cloned demo target in the frontend.
4. Trigger a scan.
5. Watch three scanner workers stream status over WebSocket.
6. Review findings mapped to GDPR and APP clauses.

The current backend uses deterministic rule scanners so the scaffold is
demo-safe. The OpenAI Agents SDK integration point is the `ScanAgent` port in
`apps/hormuz-be/modules/scan/domain/ports.py`.
