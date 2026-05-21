# Mouse — SSE workflow event schema

- **Date:** 2026-05-21
- **Issue:** #22
- **Owner:** Mouse

## Decision

Standardize workflow-side SSE payloads on a typed `WorkflowEvent` contract with:

- `event`: enum (`intent_resolved`, `sql_building`, `sql_ready`, `executing`, `result`, `done`, `error`)
- `executor`: workflow step identifier (`intent-classifier`, `sql-builder`, `query-executor`, `workflow`)
- `data`: JSON-serializable payload for the current step
- `timestamp`: `datetime.now(timezone.utc).isoformat()`

## Why

- Keeps the workflow stream stable while Tank owns HTTP/SSE framing in FastAPI.
- Preserves backward compatibility by leaving `run()` unchanged and adding `run_streaming()`.
- Gives the frontend deterministic progress states without exposing internal SDK objects.

## Notes

- Non-data intents short-circuit with `intent_resolved` → `result` → `done`.
- Workflow failures emit `error` with the failing executor in `executor`.
- Event payloads are emitted as Pydantic models so the endpoint can serialize them directly for SSE `data:` lines.
