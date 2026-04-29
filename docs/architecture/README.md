# Architecture Decision Records

These ADRs capture repo conventions that should outlive the first hackathon
iteration.

| ADR | Decision |
| --- | --- |
| [backend-architecture.md](./backend-architecture.md) | FastAPI module monolith with DDD and hexagonal slices. |
| [frontend-architecture.md](./frontend-architecture.md) | Feature-first React with TanStack Query for server state. |
| [realtime-contract.md](./realtime-contract.md) | WebSocket scan events use typed JSON messages. |
| [error-contract.md](./error-contract.md) | Backend errors use structured `detail` payloads. |

## How to Add an ADR

1. Keep it short: decision, why, invariants, when to revisit.
2. Include the concrete paths that enforce the decision.
3. Link it from this index.

