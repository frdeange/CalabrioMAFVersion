# Project Context

- **Owner:** Kiko de Ángel
- **Project:** WFM Supervisor Assist — PoC de asistente conversacional para supervisores de Calabrio que traduce preguntas en lenguaje natural a SQL sobre vistas analíticas. Defense-in-Depth de 4 capas, 3 agentes especializados en Foundry, 2 MCP servers locales, identity propagation end-to-end.
- **Stack:** Microsoft Agent Framework (Python) · Foundry Agent Service · Azure Container Apps (ACA) · MCP (FastMCP) · Angular + SSE + MSAL · APIM · Azure SQL · Cosmos DB · Azure OpenAI · App Insights · Bicep (IaC diferido)
- **Architecture proposal:** `C:\repos\copilotCLIContainer\propuesta-arquitectura-modernizada.md`
- **Plan:** 8 fases (~62 días), Sprint 0 con 8 spikes críticos antes de comprometer diseño
- **Created:** 2026-05-19
- **Universe:** The Matrix

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-05-19: Initial context
- 3 agentes en Foundry (Intent / SqlBuilder / Executor) con principio de mínimo privilegio sobre tools MCP.
- Decisión clave: **Local MCP** (no Hosted). MAF orquesta el bucle de tool calls — esto habilita `FunctionMiddleware`, propagación controlada de `x-user-context`, RBAC per-user.
- HMAC firma el `SqlPlan` entre SqlBuilder y Executor (sección §2 del doc).
- Sprint 0 (5 días laborables) valida 8 suposiciones antes de comprometer el diseño completo.
- Reviewer obligatorio en PRs que toquen contratos cross-cutting, middleware de seguridad, o structured outputs.

### 2026-05-19: Team update — DevOps foundations in flight
- Switch completed DevOps bootstrap (PR #1 on `squad/0-devops-foundations`).
- **Issue templates:** 🐛 bug · ✨ feature · 🔐 security · 🧪 test · 📚 docs · 🏗️ infra · 🔍 spike · 🔧 chore · 🚀 release
- **Labels:** `area:*` (technical domain) + `phase:0a-spike` through `phase:8-tuning`
- **CODEOWNERS auto-routing** now active. GitHub assigns reviewers per path.
- All team PRs now follow Conventional Commits + branch protection on `master` and `develop`.
- Reference: `.squad/decisions.md` § "Switch — DevOps Foundations Bootstrap"

### 2026-05-19: Coordinator clarification (post-rename)

Earlier entry above ("All team PRs now follow Conventional Commits + branch protection on `master` and `develop`") was written before the same-day rename. Current state: branch protection on `main` + `develop`. See `switch/history.md` section "Default branch rename master → main" for the rename evidence.
