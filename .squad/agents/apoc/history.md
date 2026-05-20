# Project Context

- **Owner:** Kiko de Ángel
- **Project:** WFM Supervisor Assist — Tests unit ≥80%, 10 escenarios E2E canónicos, tests por capa de guardrail con sqlglot assertions, corpus adversarial de prompt injection, soporte de pentest interno (con Oracle).
- **Stack:** pytest · pytest-asyncio · hypothesis · sqlglot · Faker · Cypress / Playwright · `pytest-cov` · GitHub Actions
- **Architecture proposal:** `C:\repos\copilotCLIContainer\propuesta-arquitectura-modernizada.md` (§3 Defense in Depth, §10.2 DoD por fase)
- **Repo path:** `tests/unit/`, `tests/e2e/`, `tests/corpora/`
- **Created:** 2026-05-19
- **Universe:** The Matrix

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-05-19: Initial context
- **10 escenarios E2E canónicos** son requisito de Fase 4 DoD — bloqueantes para cierre de fase.
- **Coverage ≥80%** medido con `pytest --cov`, gate en CI gestionado por Switch.
- **RED + GREEN tests por capa de guardrail** — no se acepta una capa con sólo tests felices. Cada capa de las 4 del MCP SQL Executor tiene tests dedicados.
- **SQL parsed assertions** — sqlglot para verificar que `WHERE TeamName IN (...)` se inyecta correctamente y que vistas no whitelisted son rechazadas en AST, no en runtime SQL.
- **Corpus adversarial versionado** en `tests/corpora/` — prompt injection, SQL injection, PII leak vectors. Mantenido como artefacto, no como código volátil.
- **Pentest interno** (Fase 7) coordinado con Oracle. Mi rol: convertir findings en tests reproducibles.

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
- **Apoc action:** Begin drafting adversarial test corpus for spikes that produce contracts (pending spike body details from Mouse/Tank).
- **Spike-results.md** tracker committed; verdicts logged as spikes complete.
- **4 ambiguities flagged for Kiko** (recorded in `.squad/decisions.md`): owner confirmation, S8 sandbox approval, S5 APIM stub, Sprint 0 duration.
- Reference: `.squad/orchestration-log/2026-05-19T133800Z-morpheus.md`

### 2026-05-19: Coordinator clarification (post-rename)

Earlier entry above ("All team PRs now follow Conventional Commits + branch protection on `master` and `develop`") was written before the same-day rename. Current state: branch protection on `main` + `develop`. See `switch/history.md` section "Default branch rename master → main" for the rename evidence.

### 2026-05-20: Query validation pack learnings
- Production evidence gathered so far is strongly **absence-first**: the most realistic anchor prompts are absence ranking, absence summary, and start/end/status follow-ups.
- For dynamic schema discovery, **BU/team scoping is a hard pass/fail rule**, not a nice-to-have optimization. A correct-looking answer without supervisor scope is still a failed test.
- The most meaningful PoC KPI is **input-token compression under controlled schema calls** (warm `listTables`, then 1-3 `getSchema` calls), because output size stays roughly comparable to the Calabrio baseline.
## Team Update — 2026-05-20T18:21:00Z

**Orchestration Complete:** Sprint 1 kickoff successful.

- Mouse: MAF workflow design + MCP tools → PR #16 ✓
- Tank: Database DDL + views + seed data → PR #15 ✓  
- Apoc: Query validation + KPI targets → PR #17 ✓

Status: All agents delivered on scope.
