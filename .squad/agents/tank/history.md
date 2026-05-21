# Project Context

- **Owner:** Kiko de Ángel
- **Project:** WFM Supervisor Assist — FastAPI Agent Host (`POST /chat` con SSE), 2 MCP servers FastMCP (Schema Provider, SQL Executor), políticas APIM (JWT validation, header injection, HMAC signing).
- **Stack:** Python 3.12+ · FastAPI · FastMCP (mcp + fastmcp) · httpx · aioodbc · sqlglot · Pydantic v2 · Azure SDKs (Identity, KV, Cosmos, Blob) · APIM policies (XML)
- **Architecture proposal:** `C:\repos\copilotCLIContainer\propuesta-arquitectura-modernizada.md`
- **Repo layout (§9.5):** monorepo con `apps/agent-host/`, `apps/mcp-schema/`, `apps/mcp-sqlexec/`
- **Created:** 2026-05-19
- **Universe:** The Matrix

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-05-21T21:15:56.578+02:00: APIM CORS ownership moved to API-level policy
- Operation-level policies for `/chat`, `/health`, and `/ready` should not implement manual `OPTIONS` preflight responses.
- CORS response headers must not be reflected in operation outbound policies when APIM built-in API-level CORS is enabled.
- Keep operation policies focused on auth, routing, throttling, and header hygiene to avoid policy conflicts.
### 2026-05-21T21:06:37.593+02:00: Local Docker Azure auth should reuse host Azure CLI cache
- For local Docker workflows, both `agent-host` and `mcp-wfm` must mount `${USERPROFILE}/.azure` into `/root/.azure` read-only so `DefaultAzureCredential` can resolve `AzureCliCredential`.
- Keep service-principal variables optional (`AZURE_CLIENT_ID`/`AZURE_CLIENT_SECRET`) because local auth now relies on `az login`, while ACA production still uses managed identity automatically via the same credential chain.
- Local onboarding docs should explicitly require `az login` before `docker compose up` to avoid silent credential failures.

### 2026-05-21T20:59:26.105+02:00: APIM CORS preflight must bypass auth
- APIM operation policies that enforce JWT on secured endpoints must short-circuit `OPTIONS` in `<inbound>` with `<return-response>` before `<validate-jwt>`.
- Preflight responses should reflect `Origin` and return `Access-Control-Allow-Methods`, `Access-Control-Allow-Headers`, `Access-Control-Allow-Credentials`, and `Access-Control-Max-Age` to unblock browser CORS.
- Adding the same `OPTIONS` handler to health/readiness policies keeps CORS behavior consistent across operations, even for GET-only routes.

### 2026-05-21T16:32:07.373+02:00: Workflow hardening for Foundry chat wiring
- SQL guardrails must validate that `WHERE bu_id` matches the requested session BU value, not just that a BU predicate exists.
- Frontend-facing `/chat` JSON and SSE errors must stay sanitized (`internal_error` + generic message); detailed exception text is server-log only.
- `WFMWorkflow._known_agents` uses a lock because the workflow singleton is shared across concurrent requests.

### 2026-05-21T15:31:03.551+02:00: APIM Host header derivation should follow API Settings service URL
- Operation policies for `/health`, `/ready`, and `/chat` should derive `Host` from `context.Api.ServiceUrl` so routing follows the API Web service URL configured per environment.
- Keep `backend-url` Named Value and API Web service URL aligned to the same DevTunnel port URL; this keeps per-developer setup to a single URL value.
- Health/readiness probes should remain unauthenticated pass-through policies with short timeouts and no backend override policy.

### 2026-05-21T15:24:47.327+02:00: DevTunnel/APIM routing invariant for local E2E
- APIM must target the DevTunnel **port URL** (from `devtunnel show` Ports output), not the friendly tunnel URL.
- DevTunnel request routing depends on the HTTP `Host` header; APIM operation policies must set `Host` from `{{backend-url}}` dynamically using `@(new System.Uri("{{backend-url}}").Host)`.
- Keeping backend target in APIM Named Value `backend-url` allows each developer to swap local tunnel endpoints without editing policy XML logic.

### 2026-05-19: Initial context
- 3 Managed Identities separadas (§9.2): `mi-agent-host`, `mi-mcp-schema`, `mi-mcp-sqlexec`. Cada una con permisos mínimos.
- MCP Schema Provider: schemas en Blob, caché en memoria, invalidación por Event Grid. RBAC filtra vistas por rol del usuario (lee `x-user-context`).
- MCP SQL Executor: **4 capas de guardrail en orden** — (1) whitelist de vistas, (2) sqlglot AST validation, (3) HMAC verify del SqlPlan, (4) parameterized exec con timeout 30s y row limit 1000.
- APIM debe firmar `x-user-*` headers con HMAC compartido con Agent Host (§2.5.1).
- `httpx` con event hook + ContextVar es el patrón para inyectar `x-user-context` por request en los clientes MCP (§2.5.3).

### 2026-05-19: Team update — DevOps foundations in flight
- Switch completed DevOps bootstrap (PR #1 on `squad/0-devops-foundations`).
- **Issue templates:** 🐛 bug · ✨ feature · 🔐 security · 🧪 test · 📚 docs · 🏗️ infra · 🔍 spike · 🔧 chore · 🚀 release
- **Labels:** `area:*` (technical domain) + `phase:0a-spike` through `phase:8-tuning`
- **CODEOWNERS auto-routing** now active. GitHub assigns reviewers per path.
- All team PRs now follow Conventional Commits + branch protection on `master` and `develop`.
- Reference: `.squad/decisions.md` § "Switch — DevOps Foundations Bootstrap"

### 2026-05-19: Team update — Sprint 0 planning delivered
- Morpheus delivered Sprint 0 plan (PR #10, `squad/sprint-0-planning` branch) with 8 spike issues (#2–#9).
- **Sprint 0 gate:** 5 working days, target 2026-05-26. Validates 8 assumptions before committing design (§9.6).
- **Tank's queue:** #6 (S5 traceparent E2E) · #9 (S8 AOAI Private Endpoint)
- **Spike-results.md** tracker committed; verdicts logged as spikes complete.
- **4 ambiguities flagged for Kiko** (recorded in `.squad/decisions.md`): owner confirmation, S8 sandbox approval, S5 APIM stub, Sprint 0 duration.
- Reference: `.squad/orchestration-log/2026-05-19T133800Z-morpheus.md`

### 2026-05-19: Coordinator clarification (post-rename)

Earlier entry above ("All team PRs now follow Conventional Commits + branch protection on `master` and `develop`") was written before the same-day rename. Current state: branch protection on `main` + `develop`. See `switch/history.md` section "Default branch rename master → main" for the rename evidence.

### 2026-05-20: WFM SQL baseline for dynamic schema discovery
- Sprint 1 data foundation is now modeled in SQL Server with 4 operational schemas (`wfm`, `absence`, `overtime`, `scheduling`) plus `_metadata` for LLM-driven schema discovery.
- `analytics` views were treated as the canonical query surface for LLMs, with stable naming and `bu_id` scoping in each view.
- Seed strategy is deterministic and idempotent: one demo BU, 50 agents, realistic distributions for absence/overtime/shift activity, and metadata catalog entries describing tables, columns, and joins.
- UAI access is now read-only by policy (`db_datareader` + SELECT on `analytics` and `_metadata`, explicitly removing `db_datawriter` membership).

### 2026-05-21: Sprint 2 APIM policy baseline
- `/chat` is now policy-driven at APIM with Entra multi-tenant JWT validation (`/common/v2.0` metadata), user-claim header injection, per-user throttling (60 req/min), and backend routing via Named Value `{{backend-url}}`.
- `/health` and `/ready` stay unauthenticated at APIM but still route through the same `backend-url` switch, enabling seamless DevTunnel/ACA environment flips without XML edits.
- HMAC signing remains intentionally deferred as a TODO until Key Vault-backed secret wiring is available.

## Team Update — 2026-05-21T000500Z

**Sprint 1 Batch 2 Complete:** Mouse, Tank, Apoc coordination checkpoint.

### Cross-Agent Dependencies (Sprint 1 Batch 2)

**Tank → Mouse (PR #18 → PR #20):**
- Tank's `foundry_client.py` wrapper provides the `FoundryAgentClient` class that Mouse's `workflow.py` imports and uses for agent orchestration.
- Tank's updated `pyproject.toml` adds `azure-ai-projects>=2.0.0` required for Mouse's provisioning script.
- Integration point: Mouse's workflow invokes `foundry_client.get_agent(agent_id)` and calls agent chat via the wrapped client.

**Mouse → Tank (PR #20 feedback on PR #18):**
- Mouse's schemas in `schemas.py` define the structured contracts that Tank's `/chat` endpoint responses must satisfy.
- Tank's `models.py` (ChatRequest, ChatResponse) now aligns with Mouse's schema expectations for workflow consumption.

**Tank → Apoc (PR #18 → PR #19):**
- Apoc's `test_foundry_client.py` mocks `AIProjectsClient` behavior to validate Tank's wrapper error paths, retry logic, and credential resolution.
- Apoc's `test_chat_endpoint.py` validates Tank's FastAPI `/chat` endpoint contract and HTTP model serialization.
- Apoc's tests confirm Tank's client works correctly with mocked Foundry responses matching Mouse's schema shapes.

### Decisions Merged (2026-05-21)

From decisions/inbox → decisions.md:
- Sprint 1 Foundry agent provisioning + workflow skeleton (Mouse, PR #20)
- Sprint 1 MAF workflow design: dynamic metadata + three specialized agents (Mouse, PR #20)
- Sprint 1 WFM database baseline (Tank, PR #18)
- Sprint 1 query validation pack (Apoc, PR #19)

Plus DevOps + branch rename decisions from Sprint 0 wrap-up (Switch).

### Structured I/O Refactor (2026-05-21T09:30:00Z)

**By:** Mouse on PR #20 (commit f226d45)  
**For Tank:** Agent definitions and workflow contracts are now typed via Foundry `structured_inputs` and MAF `response_format`.

- Intent Classifier now propagates `language_hint` for multilingual workflows.
- SQL Builder agent definition declares structured inputs (`intentResult`, `tableSchemas`, `buId`, `userQuestion`) + receives typed outputs.
- Query Executor agent definition declares structured inputs (`sqlPlan`, `executionResult`, `userLanguage`) + enforces contract at MCP boundary.
- All inter-agent handoffs now use SDK-native contracts instead of JSON-in-message.

**Tank integration:** Your `/chat` endpoint should continue to work as-is; the workflow consumer (Mouse's `workflow.py`) now has stricter type expectations from the returned ChatResponse shapes. Verify your models align with `IntentResult` and `SqlPlan` in Mouse's `schemas.py`.

### Next Phase (Phase 1 Batch 3)

**Unblocked once all Batch 2 PRs merge:**
- Tank: Add Dockerfile + docker-compose orchestration (dep on Switch's container-build CI gate).
- Tank (with Oracle): Wire end-to-end traceparent propagation for S5 spike validation.
- Tank: Prepare Agent Host for native MAF `WorkflowBuilder` consumption of provisioned agents.
## Team Update — 2026-05-20T18:21:00Z

**Orchestration Complete:** Sprint 1 kickoff successful.

- Mouse: MAF workflow design + MCP tools → PR #16 ✓
- Tank: Database DDL + views + seed data → PR #15 ✓  
- Apoc: Query validation + KPI targets → PR #17 ✓

Status: All agents delivered on scope.

### 2026-05-20: Agent Host wiring baseline for Sprint 1 Batch 2
- Agent Host now includes a Foundry SDK manager (`FoundryClientManager`) with lazy client initialization, timeout-wrapped calls, structured logging, and health checks.
- `/chat` now accepts `bu_id` and `conversation_id`, creates a Foundry conversation when absent, and forwards `message + bu_id + session_context` into the workflow integration point.
- `/ready` now verifies both Foundry endpoint configuration and live connectivity, while request/response models include intent/sql/answer payload fields for workflow outputs.

## Team Update — 2026-05-21T11:25:00Z

**Sprint 2 Batch 1:** Real-time streaming architecture delivery.

### Tank Work (PR #25)

**Issue:** #25 — SSE endpoint with Accept-header negotiation  
**Branch:** feature/sprint2-sse-endpoint  
**Status:** 47 tests pass, 2 xfailed

**Delivered:**
- Implemented SSE streaming on `POST /chat` with HTTP `Accept` header negotiation:
  - `Accept: text/event-stream` → `StreamingResponse` (text/event-stream)
  - Any other Accept value → existing JSON `ChatResponse` (backward compatible)
- Added `_stream_chat()` async generator in `app/main.py`:
  - Resolves workflow and conversation id via `asyncio.to_thread(...)`
  - Calls blocking `workflow.run_streaming(message, bu_id, session_context)` via thread offloading
  - Iterates events safely and emits `data: {json}\n\n`
  - Stops on client disconnect
  - Emits terminal SSE error event on workflow failure
- Added `WorkflowEventResponse` API model in `app/models.py` for SSE payload shape
- Configured CORS middleware for Angular dev origins (`http://localhost:4200`, `http://127.0.0.1:4200`) and exposed SSE-related headers
- Added endpoint tests in `tests/test_sse_endpoint.py`:
  - SSE happy-path stream payloads
  - Accept negotiation (SSE vs JSON)
  - SSE error event when streaming workflow fails
  - Backward-compatible JSON behavior

**Integration points:**
- Consumes Mouse's `WorkflowEvent` schema and `run_streaming()` generator (PR #26)
- Provides SSE transport for Trinity's Angular chat service (PR #27)
- Maintains backward-compatible JSON response for non-SSE clients

**Implementation notes:**
- No external SSE library required (raw FastAPI `StreamingResponse` sufficient)
- Temporary fallback for `WorkflowEvent` import until Mouse's streaming schema merge lands
- Thread-safe workflow execution allows blocking MAF workflow to integrate with FastAPI async

### User Directives Captured

**Time:** 2026-05-21T11:15–11:21Z  
**Source:** Kiko de Ángel

Three critical architecture directives:
1. **ACA infra ready** (11:15Z): Container Registry (calabriomafpocacr), Container Environment, and Container App exist in rg-Calabriomafpoc. Running dummy image; ready for agent host Dockerfile deployment.
2. **Frontend → APIM routing** (11:16Z): Frontend NEVER talks directly to backend. All traffic through APIM (calabriomafpoc-apim). APIM handles JWT validation, claim extraction, header injection, HMAC signing, rate limiting.
3. **Calabrio UI reference** (11:21Z): Frontend must visually match existing Calabrio Supervisor Assist UI (not generic chatbot).

All directives recorded in `.squad/decisions.md`.
## 2026-05-21T11:19:14.8425899Z � APIM Policies Complete (PR #33)

Delivered APIM policies XML with JWT validation, claim extraction, rate limiting. Scribe recorded in orchestration log and archived 2 old decisions.

