# OpenAI Hormuz

Compliance Codex monorepo scaffold. The project conventions are adapted from
`scribe-workspace`, with Codex-oriented instructions in this file.

## Rules

- Use `task` commands from the workspace root. Do not bypass Taskfiles unless
  a task is missing and you are adding it as part of the change.
- Backend is Python with `uv`; frontend is TypeScript with `pnpm`.
- Services live directly in `apps/`.
- Do not use `python-dotenv` in FastAPI. Taskfile `dotenv` exports env vars.
- Keep backend code in vertical bounded contexts under `modules/`.
- Keep frontend code feature-first under `src/features/`.
- Remote frontend data goes through TanStack Query hooks. Do not hand-roll
  `useState + useEffect` fetching.
- Add architecture decisions under `docs/architecture/` when a convention is
  expected to outlive the current task.

## Service Map

- `apps/hormuz-be`: FastAPI backend on port 4000.
- `apps/hormuz-fe`: Vite React frontend on port 3000.
- `demo_repo`: deterministic demo target containing known compliance issues.

## Common Commands

```bash
task install
task infra:up
task be:dev
task fe:dev
task be:test
task fe:build
task openapi:sync
```

