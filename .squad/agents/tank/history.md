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
