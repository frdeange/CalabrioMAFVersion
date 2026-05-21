# Architecture Review — PR #36: feat(agent-host): wire Foundry chat workflow

**Reviewer:** Morpheus (Lead / Architect)  
**Date:** 2026-05-21T16:25:00Z  
**PR:** #36 (`feat/workflow-foundry-wiring` → `develop`)  
**Author:** Mouse  
**Verdict:** ✅ APPROVE (with advisory observations for upcoming spikes)

---

## Summary

PR #36 delivers the core runtime wiring between the `/chat` endpoint and Azure AI Foundry Agent Service. It implements the sequential Intent → SQL Builder → Executor workflow (§2.4), conversation reuse across hops, SSE streaming with frontend-compatible events, APIM identity propagation, and defensive error handling throughout.

**683 additions, 97 deletions, 8 files.** 102 tests pass (2 xfailed — expected).

---

## Evaluation

### 1. Architecture Alignment (§2.4 Sequential Workflow)

**PASS.** The `WFMWorkflow.run()` method follows the exact sequential pipeline:
1. Intent classification → conditional routing (CONVERSATIONAL / OUT_OF_SCOPE short-circuits)
2. SQL Builder (with schema fetch from MCP) → validation (SELECT-only, BU filter enforcement via sqlglot)
3. Query execution via MCP → Executor agent for NL answer

This matches §2.4's "Intent → SQL → Executor with conditional routing" pattern. The `run_streaming()` generator emits granular `WorkflowEvent` SSE frames at each stage boundary — exactly what the frontend needs.

### 2. Foundry Integration Pattern

**PASS.** `AIProjectClient` + `DefaultAzureCredential` — correct pattern for Managed Identity (ADR-001 §2). No API keys in code. The `_call_foundry_agent()` method uses `agent_reference` by name (not hardcoded agent IDs), which survives redeployment. Conversation reuse via `self._openai.conversations.create()` is correct for multi-hop statefulness.

**Note:** `_ensure_agent_exists()` caches known agents in `_known_agents` set — good optimization, avoids round-trips after first verification.

### 3. SSE Streaming

**PASS.** The `_stream_chat()` async generator in `main.py` correctly:
- Uses a producer thread + queue pattern to bridge sync generators to async FastAPI
- Detects client disconnection via `request.is_disconnected()`
- Implements a 30-second per-event timeout (prevents zombie streams)
- Emits properly formatted `data: {...}\n\n` SSE frames
- Sets `Cache-Control: no-cache` + `X-Accel-Buffering: no` headers (required for nginx/proxy passthrough)

### 4. Error Handling

**PASS.** Comprehensive coverage:
- `WorkflowExecutionError` wraps all Foundry/MCP failures → never fabricates data
- `_wrap_foundry_exception()` distinguishes 404/not-found from transient errors
- MCP tool calls have 30-second HTTP timeout (`urlopen(..., timeout=30)`)
- Empty SQL, non-SELECT statements, missing BU filter all raise defensively
- SSE stream emits error events (not HTTP 500) so frontend can display them
- `_missing_agent_message()` gives actionable "create it in Foundry Studio" guidance

### 5. User Context Propagation

**PASS.** `_extract_user_context()` reads APIM-injected headers: `x-user-oid`, `x-user-tid`, `x-user-name`, `x-user-upn`, `x-user-roles`, `x-user-teams`. Supports fallback names (`x-ms-client-principal-id`, etc.). Context flows into `session_context["user"]` and is passed to `workflow.run()` / `workflow.run_streaming()`. Test `test_chat_serializes_workflow_model_and_passes_apim_identity` explicitly verifies this end-to-end.

**Future work (TODO[S3]):** Context does NOT yet propagate to MCP requests (HMAC + `x-user-context` headers). This is correctly deferred to Spike S3.

### 6. Security

**PASS.** No credentials in code. `DefaultAzureCredential` only. No secrets in settings defaults. SQL validation blocks non-SELECT and multi-statement injection. The `extra="forbid"` on Pydantic models prevents unexpected field injection.

**Advisory:** The `_invoke_mcp_tool()` method uses stdlib `urllib` without TLS certificate pinning — acceptable for PoC intra-VNET but should be hardened in Phase 7.

### 7. CORS

**PASS.** `localhost:8080` and `127.0.0.1:8080` added alongside existing `:4200` origins. Test `test_chat_returns_sse_stream_when_requested` verifies the CORS header is returned for `Origin: http://localhost:8080`.

### 8. Test Coverage

**PASS.** Mouse added 3 new test files with targeted coverage:
- `test_workflow.py`: Streaming event contract, BU filter enforcement, error paths, catalog caching
- `test_sse_endpoint.py`: SSE negotiation, JSON fallback, error event emission, CORS verification
- `test_ready_chat.py`: Workflow model serialization, APIM identity passthrough, error responses

All 102 tests pass. The streaming contract test (`test_run_streaming_emits_frontend_event_contract`) directly validates the event sequence the frontend will consume.

---

## Advisory Observations (non-blocking)

| # | Observation | Impact | Spike |
|---|-------------|--------|-------|
| 1 | `_invoke_mcp_tool()` uses raw `urllib` — no retry/backoff on transient failures | Low (PoC) | S1 will replace with `MCPStreamableHTTPTool` |
| 2 | `WFMWorkflow.__init__` eagerly calls `_build_project_client()` — fails fast if Foundry unreachable at import time | Low — acceptable for container startup semantics | — |
| 3 | `_call_foundry_agent()` falls back on `TypeError` (drops `response_format`) — defensive but may mask SDK-version mismatches | Low — temporary until S4 confirms structured output support | S4 |
| 4 | No HMAC signature on `SqlPlan` between SqlBuilder → Executor yet | Expected — this is S3's scope | S3 |
| 5 | No OTel spans per hop yet | Expected — this is S5's scope | S5 |

All observations are already tracked via TODO comments in `workflow.py` referencing the relevant spike. No action required now.

---

## Decision

**✅ APPROVED.** Architecture is sound, follows §2.4 faithfully, credential handling is correct (ADR-001 compliant), error handling is production-grade for a PoC, and test coverage is proportional to risk. The remaining gaps (HMAC, OTel, MCP binding, structured outputs) are correctly scoped to their respective spikes (S1–S6) and marked with TODO comments.

Mouse may merge after CI green.
