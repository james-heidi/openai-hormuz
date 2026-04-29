# Error Contract

**Status:** Adopted.

## Decision

Backend handlers raise `HTTPException(detail={ code, message, ... })` for
expected failures. WebSocket failures send an `error` event with the same
shape before closing.

## Why

- Frontend can route all API failures through one toast layer.
- Demo failures stay readable instead of leaking Python tracebacks.
- The shape gives clients one predictable structured-error format.

## Shape

```json
{
  "code": "invalid_repo_path",
  "message": "The repository path does not exist."
}
```
