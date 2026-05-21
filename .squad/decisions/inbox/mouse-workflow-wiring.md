# Mouse decision: workflow wiring for Foundry-backed chat

- **Date:** 2026-05-21T16:09:13.440+02:00
- **Owner:** Mouse
- **Requested by:** Kiko de Ángel

## Context

The first protected E2E path was already working up to `POST /chat` with APIM JWT validation, but the Agent Host still had two wiring gaps for real message processing:
- `main.py` expected `AgentHostWorkflow` while `workflow.py` only exposed `WFMWorkflow`.
- The host and workflow did not yet pass APIM identity context or emit the SSE event contract expected by the Angular chat UI.

## Decision

For the current PoC, keep the runtime workflow on the already-working direct Foundry Responses API + local MCP JSON-RPC path, and finish the host wiring around it instead of blocking on native MAF `WorkflowBuilder` / `MCPStreamableHTTPTool` adoption.

Implemented contract:
1. `workflow.py` now exports `AgentHostWorkflow` as the no-arg runtime entrypoint while preserving `WFMWorkflow` for unit tests.
2. `/chat` now accepts localhost:8080 CORS, extracts APIM identity headers, and forwards them inside `session_context`.
3. Foundry agent calls reuse the incoming conversation id across hops and preflight agent existence with `project.agents.get(...)` so missing agents return: `Foundry agent '{name}' not found, please create it in Azure AI Foundry Studio`.
4. `run_streaming()` emits frontend-compatible SSE events (`intent_resolved`, `sql_building`, `sql_ready`, `executing`, `result`, `done`) with `conversation_id` inside `data`.

## Consequences

- The PoC now has a complete backend execution path for frontend chat turns without changing any middleware modules.
- Native MAF workflow/tool binding remains a follow-up concern, but it is no longer on the critical path for protected chat message processing.
- Regression safety is preserved by the passing `src/agent_host` pytest suite, including the middleware tests.
