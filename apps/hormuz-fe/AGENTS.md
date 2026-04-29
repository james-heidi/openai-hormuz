# Hormuz Frontend

Vite + React frontend uses feature-first structure.

## Rules

- Run commands through `task fe:*` from the repo root.
- Use `pnpm`, not npm or yarn.
- Keep server state in TanStack Query hooks.
- Keep feature code under `src/features/<name>`.
- Do not import sibling feature internals from non-page files.
- Keep shared UI and transport helpers under `src/components` and `src/lib`.
