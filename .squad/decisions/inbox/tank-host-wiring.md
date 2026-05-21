# Tank decision inbox — Agent Host wiring (Sprint 1 Batch 2)

**Date:** 2026-05-20  
**Author:** Tank  
**Scope:** `src/agent_host`

## Decision

Implement a lightweight Foundry SDK wrapper in Agent Host and wire `/chat` to the workflow integration seam with defensive lazy-loading.

## Why

- The host needs a stable, testable abstraction over Foundry conversations/responses before full workflow orchestration lands.
- Mouse-owned `workflow.py` is not guaranteed to exist on this branch, so runtime-safe lazy import/error fallback is required to keep the host bootable.
- Sprint 1 requires `/chat` response fields (`intent`, `sql`, `answer`, `conversation_id`, timing) to support the 3-agent pipeline contract.

## Applied changes

1. Added runtime dependencies for Foundry + identity + MCP HTTP + YAML prompt loading in `src/agent_host/pyproject.toml`.
2. Extended `Settings` with:
   - `model_deployment`
   - `mcp_wfm_url`
   - `intent_agent_name`
   - `sql_builder_agent_name`
   - `query_executor_agent_name`
   - `default_bu_id`
3. Added `FoundryClientManager` singleton wrapper in `app/foundry_client.py`:
   - lazy init of `AIProjectClient` and OpenAI client
   - timeout-wrapped calls
   - `create_conversation`, `chat`, `chat_structured`, `health_check`
   - structured error logging
4. Updated `app/main.py`:
   - defensive workflow import seam with TODO note for Mouse merge timing
   - `/ready` now includes Foundry connectivity probe
   - `/chat` now accepts `bu_id` + `conversation_id`, builds session context, executes workflow, and returns enriched payload
5. Updated `app/models.py` request/response schemas for workflow payload shape.

## Consequences

- Agent Host now has an operational Foundry plumbing baseline without coupling to unfinished workflow code.
- Once Mouse’s workflow implementation is merged, only adapter-level alignment may be needed (class name and output shape).
