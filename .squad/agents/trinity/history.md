# Project Context

- **Owner:** Kiko de Ángel
- **Project:** WFM Supervisor Assist — Angular UI con chat conversacional, SSE streaming, MSAL JWT acquisition contra Entra ID, manejo transparente de rechazos guardrail.
- **Stack:** Angular + TypeScript (strict) · RxJS · EventSource (SSE) · MSAL.js · Cypress / Playwright · Shared TS types con backend Pydantic
- **Architecture proposal:** `C:\repos\copilotCLIContainer\propuesta-arquitectura-modernizada.md`
- **Backend contract source of truth:** `apps/agent-host/src/models.py` (Pydantic) — TS types se generan / mantienen sincronizados
- **Created:** 2026-05-19
- **Universe:** The Matrix

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-05-19: Initial context
- Calabrio supervisors usan tablets en operaciones → mobile-first.
- `POST /chat` devuelve **SSE** con eventos por executor (Intent → SqlBuilder → Executor → Result → Done). UI muestra progreso por executor en tiempo real (§7 del doc).
- MSAL.js obtiene JWT contra Entra ID; APIM lo valida e inyecta `x-user-*` headers internos. El frontend NUNCA debe ver los headers internos.
- Rechazos de guardrail (PII, PromptShields, RBAC, SQL pre-val) deben renderizarse con nombre de capa + razón accionable, no como error genérico.

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
- **Spike assignments:** Mouse (#2 S1, #3 S2, #4 S3, #5 S4, #7 S6, #8 S7) · Tank (#6 S5, #9 S8) · Oracle co-reviews on #3, #4, #9
- **Spike-results.md** tracker committed; verdicts logged as spikes complete.
- **4 ambiguities flagged for Kiko** (recorded in `.squad/decisions.md`): owner confirmation, S8 sandbox approval, S5 APIM stub, Sprint 0 duration.
- Reference: `.squad/orchestration-log/2026-05-19T133800Z-morpheus.md`

### 2026-05-19: Coordinator clarification (post-rename)

Earlier entry above ("All team PRs now follow Conventional Commits + branch protection on `master` and `develop`") was written before the same-day rename. Current state: branch protection on `main` + `develop`. See `switch/history.md` section "Default branch rename master → main" for the rename evidence.
