# Hormuz Backend

FastAPI backend uses module-monolith rules.

## Rules

- Run commands through `task be:*` from the repo root.
- Use `uv` for dependency management.
- Do not call `load_dotenv()` from app code.
- Keep domain models pure: no FastAPI, filesystem, OpenAI SDK, or database
  dependencies in `modules/*/domain`.
- Put orchestration in `application/` and transport details in
  `adapters/inbound`.
- WebSocket and REST paths must share the same domain models.
