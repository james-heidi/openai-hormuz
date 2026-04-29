# Backend Architecture - Module Monolith + Hexagonal Slices

**Status:** Adopted.

## Decision

Run one FastAPI process in `apps/hormuz-be`, with each bounded context under
`modules/<name>` split into domain, application, and adapters.

## Why

- The hackathon scope needs speed and local reliability more than deploy-time
  service isolation.
- The shape still leaves future extraction cheap because concrete adapters stay
  outside domain code.
- It mirrors the `scribe-workspace` backend convention the team already knows.

## Module Shape

```text
modules/<name>/
├── domain/
│   ├── entities.py
│   └── ports.py
├── application/
│   └── use_case.py
└── adapters/
    ├── inbound/
    │   └── router.py
    └── outbound/
```

## Invariants

- Domain code depends only on Python and Pydantic.
- Application code depends on domain ports, not concrete adapters.
- Inbound adapters own HTTP/WebSocket schemas and FastAPI dependencies.
- Each module owns its DI factories in `modules/<name>/__init__.py`.
- Cross-cutting code lives in `infrastructure/`, not in a bounded context.

## Current Contexts

- `scan`: orchestrates scanner agents, emits progress, maps findings, and
  computes the compliance score.
- `shared`: reusable domain event and event bus primitives reserved for
  cross-context reactions.

