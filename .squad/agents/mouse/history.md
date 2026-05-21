# Project Context

- **Owner:** Kiko de Ángel
- **Project:** WFM Supervisor Assist — MAF Workflow secuencial con routing condicional, 3 FoundryAgent clients, middleware (PII / PromptShields / HMAC / SQL pre-val / audit), MCP local binding con `MCPStreamableHTTPTool`, OTel a App Insights.
- **Stack:** Python 3.12+ · `agent-framework>=1.0` · `agent-framework-foundry>=1.0` · `mcp>=1.0` · Pydantic v2 · httpx · `azure-monitor-opentelemetry` · `azure-ai-contentsafety`
- **Architecture proposal:** `C:\repos\copilotCLIContainer\propuesta-arquitectura-modernizada.md`
- **Repo path:** `apps/agent-host/src/` — `main.py`, `agents_factory.py`, `workflow_factory.py`, `middleware/`, `models.py`, `observability.py`
- **Created:** 2026-05-19
- **Universe:** The Matrix

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-05-20: Dynamic metadata-first Sprint 1 workflow
- The WFM Supervisor prompt stays fixed and domain-neutral; new data domains must be onboarded through `_metadata.catalog_tables`, `_metadata.catalog_columns`, and `_metadata.catalog_joins`, not by editing prompt text.
- The Router should cache `listTables()` once per session and pass only shortlisted tables to the SQL Builder to keep normal turns under the 10k input-token target.
- `executeQuery()` is the final enforcement point: MI-only SQL auth, `sqlglot` SELECT-only validation, active-table whitelist, 30s timeout, and a 1000-row cap all belong in the MCP layer.

### 2026-05-19: Initial context
- **Decisión clave:** Local MCP (no Hosted) — MAF orquesta el bucle de tool calls. Esto habilita `FunctionMiddleware` y propagación controlada de `x-user-context` (§2.4).
- **3 FoundryAgent clients:** Intent (sin tools), SqlBuilder (Schema MCP), Executor (SqlExec MCP). Principio de mínimo privilegio (§2.1).
- **Structured outputs strict** — `response_format: json_schema` en Foundry; `.structured_output(Model)` deserializa en MAF. Spike S4 valida.
- **Conditional routing** — `WorkflowBuilder.add_edge(intent, sqlbuilder, condition=lambda r: r.intent_type == "DataQuery")`. Spike S6 valida.
- **OTel atributos custom obligatorios** — `agent.name`, `tool.name`, `user.oid`, `guardrail.layer`, `guardrail.outcome`, `correlation.id`.
- **Sprint 0 prioridad:** S1, S2, S3 son **bloqueantes**. Sin S1 verde, no se construye nada más del Agent Host.

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
- **Mouse's queue:** #2 (S1 FoundryAgent + MCP) · #3 (S2 middleware) · #4 (S3 x-user-context) · #5 (S4 structured outputs) · #7 (S6 conditional routing) · #8 (S7 SSE streaming)
- **Spike-results.md** tracker committed; verdicts logged as spikes complete.
- **4 ambiguities flagged for Kiko** (recorded in `.squad/decisions.md`): owner confirmation, S8 sandbox approval, S5 APIM stub, Sprint 0 duration.
- Reference: `.squad/orchestration-log/2026-05-19T133800Z-morpheus.md`

### 2026-05-19: Coordinator clarification (post-rename)

Earlier entry above ("All team PRs now follow Conventional Commits + branch protection on `master` and `develop`") was written before the same-day rename. Current state: branch protection on `main` + `develop`. See `switch/history.md` section "Default branch rename master → main" for the rename evidence.

### 2026-05-21: Prefer SDK-native contracts over prompt-formatted JSON
- Foundry Agent Service structured inputs (`{{variableName}}` + `structured_inputs`) should carry inter-agent context instead of serializing JSON blobs into the message body.
- MAF/agent SDK structured outputs via `options={"response_format": PydanticModel}` are the durable contract for Intent and SQL planning; prompt text should describe behavior, not JSON syntax.
- When the intent step still uses JSON text as its free-text payload, session context must be converted to JSON-safe primitives before serialization because cached Pydantic models can otherwise break later turns.

## Team Update — 2026-05-20T18:21:00Z

**Orchestration Complete:** Sprint 1 kickoff successful.

- Mouse: MAF workflow design + MCP tools → PR #16 ✓
- Tank: Database DDL + views + seed data → PR #15 ✓  
- Apoc: Query validation + KPI targets → PR #17 ✓

Status: All agents delivered on scope.

### 2026-05-20: Foundry provisioning + pre-MAF workflow shell
- Foundry Agent Service creation must stay outside the runtime workflow; a standalone Python provisioner using `AIProjectClient.agents.create_version(...)` is the correct bootstrap path before MAF consumes persisted agents.
- Prompt ownership is cleanly split: three small YAML prompts map 1:1 to Intent, SQL Builder, and Query Executor, while the workflow shell owns catalog caching, schema fan-out, and safe failure behavior.
- Until native MAF packages are wired into `agent_host`, the most compatible interim pattern is: Foundry chat via `project.get_openai_client()`, local MCP invoked by the host, and explicit TODO seams for middleware, HMAC, SQL pre-validation, and OTel.

## Team Update — 2026-05-21T000500Z

**Sprint 1 Batch 2 Complete:** Mouse, Tank, Apoc coordination checkpoint.

### Cross-Agent Dependencies (Sprint 1 Batch 2)

**Tank → Mouse (PR #18 → PR #20):**
- Tank's `foundry_client.py` wrapper provides the `FoundryAgentClient` class that Mouse's `workflow.py` now imports and uses for agent orchestration.
- Tank's updated `pyproject.toml` adds `azure-ai-projects>=2.0.0` required for Mouse's provisioning script.
- Integration point: Mouse's workflow invokes `foundry_client.get_agent(agent_id)` and calls agent chat via the wrapped client.

**Mouse → Apoc (PR #20 → PR #19):**
- Apoc's test suite imports and validates Mouse's Pydantic schemas from `schemas.py` (IntentResponse, SQLPlanEnvelope, ExecutionResult, etc.).
- Apoc's `test_schemas.py` ensures schema coercion and validation work for all orchestration contracts.
- Apoc's `test_workflow.py` uses Mock Foundry agents returning shaped responses matching Mouse's schemas.

**Tank → Apoc (PR #18 → PR #19):**
- Apoc's `test_foundry_client.py` mocks `AIProjectsClient` behavior to validate Tank's wrapper error paths, retry logic, and credential resolution.
- Apoc's `test_chat_endpoint.py` validates Tank's FastAPI `/chat` endpoint contract and HTTP model serialization.

### Decisions Merged (2026-05-21)

From decisions/inbox → decisions.md:
- Sprint 1 Foundry agent provisioning + workflow skeleton (Mouse, PR #20)
- Sprint 1 MAF workflow design: dynamic metadata + three specialized agents (Mouse, PR #20)
- Sprint 1 WFM database baseline (Tank, PR #18)
- Sprint 1 query validation pack (Apoc, PR #19)

Plus DevOps + branch rename decisions from Sprint 0 wrap-up (Switch).

### Next Phase (Phase 1 Batch 3)

**Unblocked once all Batch 2 PRs merge:**
- Mouse: Wire native MAF `WorkflowBuilder` + `MCPStreamableHTTPTool` to replace pre-MAF skeleton (depends on `agent-framework>=1.0` landing in `pyproject.toml`).
- Tank: Add Dockerfile + docker-compose orchestration (dep on Switch's container-build CI gate).
- Apoc: Expand adversarial corpus and profile query performance under load.

## Team Update — 2026-05-21T11:25:00Z

**Sprint 2 Batch 1:** Real-time streaming architecture delivery.

### Mouse Work (PR #26)

**Issue:** #26 — WorkflowEvent schema + run_streaming() generator  
**Status:** 48 tests pass, 2 xfailed

**Delivered:**
- Implemented `WorkflowEvent` schema with per-executor event types:
  - `intent_start`, `intent_done` (Intent classifier execution)
  - `sql_start`, `sql_done` (SQL builder execution)
  - `executing_start`, `executing_done` (Query executor execution)
  - `workflow_complete` (successful workflow completion)
  - `workflow_error` (workflow failure with error details)
- Added `workflow.run_streaming()` generator method for SSE backend support
- Updated workflow orchestration to emit events at each executor boundary
- Added streaming workflow test coverage

**Integration points:**
- Schema referenced by Tank's SSE endpoint implementation (PR #25)
- Streaming generator consumed by Tank's `_stream_chat()` async wrapper
- Event model consumed by Trinity's Angular SSE chat service (PR #27)

**Design notes:**
- Events designed for direct Angular SSE consumption with per-executor status tracking
- Generator pattern allows blocking workflow to integrate cleanly with FastAPI async streaming
- Event types map 1:1 to UI progress states (Intent → SQL → Executing → Result)

### Foundry Agents Provisioned

**Completed:** Prior to Sprint 2 Batch 1

Coordinator provisioned 3 Foundry agents:
- `wfm-intent-classifier` (gpt-5.2, v1)
- `wfm-sql-builder` (gpt-5.2, v1)
- `wfm-query-executor` (gpt-5.2, v1)

Issue #21 closed.
