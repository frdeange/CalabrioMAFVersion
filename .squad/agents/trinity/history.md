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

## Team Update — 2026-05-21T11:25:00Z

**Sprint 2 Batch 1:** Real-time streaming architecture delivery.

### Trinity Work (PR #27)

**Issue:** #27 — Angular 19 scaffold with MSAL, SSE chat service, per-executor progress  
**Status:** In progress

**Delivered:**
- Scaffolded Angular 19 standalone application at `src/frontend`
- Implemented MSAL-based authentication:
  - `msal.config.ts` for Entra ID configuration
  - `auth.guard.ts` for route protection
  - `auth.interceptor.ts` for JWT token injection
- Created typed chat models and SSE streaming service:
  - Typed `WorkflowEvent` model matching Mouse's backend schema
  - `ChatService` with SSE `EventSource` integration
  - Per-executor progress tracking (Intent → SQL → Executing → Result)
- Built chat UI components:
  - Chat container with message history
  - Per-executor progress indicators (animated dots, not generic spinner)
  - Data table rendering for query results
  - Guardrail rejection display with layer + reason
- Added mobile-first responsive styles with light/dark theme variables
- Configured environment files and production file replacement

**Integration points:**
- Consumes Tank's SSE `/chat` endpoint (PR #25) via typed `ChatService`
- Receives Mouse's `WorkflowEvent` schema (PR #26) for per-executor progress UI
- Routes all API traffic through APIM (per user directive — never direct to backend)
- UI design matches Calabrio Supervisor Assist reference (per user directive)

**Design compliance:**
- Dark left sidebar with Calabrio branding (red logo)
- Clean white chat area with centered empty state greeting
- User messages right-aligned (light purple), assistant left-aligned (light gray)
- Inline data tables with blue header row (Calabrio brand blue)
- Bottom input bar with "Type your message..." placeholder and blue send button
- AI disclaimer footer: "Supervisor assist is a generative AI-based solution and may make mistakes"
- Animated progress dots during execution (no generic spinner)
- Mobile-first, responsive, professional appearance (not prototype UI)

**Architecture notes:**
- MSAL configuration requires environment-specific tenant ID and client ID values
- JWT flows through APIM for validation and claim extraction before reaching backend
- SSE service handles connection state, reconnection, and error events
- TypeScript strict mode enforced throughout
