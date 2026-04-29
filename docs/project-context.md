# Project Context

Source: Notion page "OpenAI x UTS Hackathon" and linked PRD/architecture
pages.

## Product

Compliance Codex scans a codebase for privacy and security compliance issues,
maps each finding to GDPR and Australian Privacy Principles, and prepares fixes
for review.

## Hackathon MVP

- Web UI accepts a local repository path.
- Backend runs scanner workers in parallel.
- Progress streams to the frontend over WebSocket.
- Findings include file, line, severity, category, regulation mapping, and
  recommendation.
- Demo target contains deterministic violations so the live demo is stable.

## Architecture Direction

- React + Vite frontend.
- FastAPI backend.
- Parallel scanner workers behind a `ScanAgent` port.
- Git worktree and OpenAI Agents SDK integration points are isolated behind
  backend ports so the first scaffold can run deterministically without LLM
  calls.

