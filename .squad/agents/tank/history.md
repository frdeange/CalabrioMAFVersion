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
