# Project Context

- **Owner:** Kiko de Ángel
- **Project:** WFM Supervisor Assist — Threat modeling de defense-in-depth de 4 capas, HMAC key lifecycle, RBAC matrix, Prompt Shields tuning, PII/DLP strategy, pentest interno (Fase 7), compliance docs partner-facing.
- **Stack:** Azure Key Vault · Managed Identity · Private Endpoint · Azure Content Safety (Prompt Shields) · Presidio (PII opcional) · STRIDE · OWASP LLM Top 10
- **Architecture proposal:** `C:\repos\copilotCLIContainer\propuesta-arquitectura-modernizada.md` (§2.1, §2.5, §3, §9.2)
- **Created:** 2026-05-19
- **Universe:** The Matrix

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-05-19: Initial context
- **Principio de mínimo privilegio** entre agentes (§2.1): Intent sin tools, SqlBuilder sólo Schema MCP, Executor sólo SqlExec MCP. Si un agente sufre prompt injection, el blast radius está acotado.
- **Delegación con header firmado (no impersonation)** (§2.5.2): identidad del usuario viaja como `x-user-context` HMAC-firmado. APIM firma, Agent Host verifica, MCP confía en el perímetro VNET.
- **HMAC del SqlPlan** entre SqlBuilder y Executor — Mouse implementa middleware; yo reviso el lifecycle de la key (KV, rotación 90d, alertas de acceso anómalo).
- **Defense in Depth 4 capas** (§3) en MCP SQL Executor: whitelist views → sqlglot AST → HMAC verify → parameterized exec. Cada capa con threat entry + test adversarial.
- **Pentest interno Fase 7** — coordinar con Apoc para reproducibilidad de findings.
- **Required reviewer** en PRs que toquen: middleware seguridad, APIM JWT, MCP guards, KV/MI/PE, identity headers.

### 2026-05-19: Team update — DevOps foundations in flight
- Switch completed DevOps bootstrap (PR #1 on `squad/0-devops-foundations`).
- **Issue templates:** 🐛 bug · ✨ feature · 🔐 security · 🧪 test · 📚 docs · 🏗️ infra · 🔍 spike · 🔧 chore · 🚀 release
- **Labels:** `area:*` (technical domain) + `phase:0a-spike` through `phase:8-tuning`
- **CODEOWNERS auto-routing** now active. GitHub assigns reviewers per path.
- All team PRs now follow Conventional Commits + branch protection on `master` and `develop`.
- Reference: `.squad/decisions.md` § "Switch — DevOps Foundations Bootstrap"
