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
