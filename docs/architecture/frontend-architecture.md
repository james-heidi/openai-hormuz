# Frontend Architecture - Feature-First React

**Status:** Adopted.

## Decision

Use Vite + React + TypeScript with a feature-first layout. Server state goes
through TanStack Query. Client-only state stays local or in a small Zustand
store when it crosses features.

## Why

- Features map cleanly to backend bounded contexts.
- TanStack Query avoids one-off loading, retry, and cache logic.
- The structure is small enough for a hackathon while keeping frontend code
  aligned around feature boundaries.

## Feature Shape

```text
src/features/<name>/
├── api.ts
├── queries.ts
├── mutations.ts
├── types.ts
├── components/
├── hooks/
└── pages/
```

## Invariants

- A feature's `api.ts` is its data edge.
- Pages are the composition layer.
- Non-page feature files should not import sibling feature internals.
- Components do not fetch directly; they call feature hooks or receive props.
- Global error handling belongs in `src/lib/queryClient.ts`.
