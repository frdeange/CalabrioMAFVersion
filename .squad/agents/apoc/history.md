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

## Team Update — 2026-05-21T000500Z

**Sprint 1 Batch 2 Complete:** Mouse, Tank, Apoc coordination checkpoint.

### Cross-Agent Dependencies (Sprint 1 Batch 2)

**Mouse → Apoc (PR #20 → PR #19):**
- Apoc's test suite imports and validates Mouse's Pydantic schemas from `schemas.py` (IntentResponse, SQLPlanEnvelope, ExecutionResult, etc.).
- Apoc's `test_schemas.py` ensures schema coercion and validation work for all orchestration contracts.
- Apoc's `test_workflow.py` uses Mock Foundry agents returning shaped responses matching Mouse's schemas.
- Apoc's `test_query_kpis.py` validates Mouse's catalog caching and three-agent pipeline sequencing against the canonical 22-query validation pack.

**Tank → Apoc (PR #18 → PR #19):**
- Apoc's `test_foundry_client.py` mocks `AIProjectsClient` behavior to validate Tank's wrapper error paths, retry logic, and credential resolution.
- Apoc's `test_chat_endpoint.py` validates Tank's FastAPI `/chat` endpoint contract and HTTP model serialization.
- Apoc's integration tests confirm Tank's client and Mouse's schemas work together under adversarial and edge-case conditions.

**Apoc → Future Phases:**
- Apoc's 22-query validation pack (`tests/query-validation/`) becomes the canonical acceptance suite for all Sprint 2+ dynamics schema discovery iterations.
- Adversarial corpus (Q21/Q22) is the foundation for Fase 7 pentest readiness (with Oracle).

### Decisions Merged (2026-05-21)

From decisions/inbox → decisions.md:
- Sprint 1 Foundry agent provisioning + workflow skeleton (Mouse, PR #20)
- Sprint 1 MAF workflow design: dynamic metadata + three specialized agents (Mouse, PR #20)
- Sprint 1 WFM database baseline (Tank, PR #18)
- Sprint 1 query validation pack (Apoc, PR #19)

Plus DevOps + branch rename decisions from Sprint 0 wrap-up (Switch).

### Structured I/O Refactor (2026-05-21T09:30:00Z)

**By:** Mouse on PR #20 (commit f226d45)  
**For Apoc:** Test contracts now enforce typed schemas via Foundry `structured_inputs` and MAF `response_format`.

- Intent Classifier now propagates `language_hint` for multilingual test scenarios.
- SQL Builder agent definition declares structured inputs (`intentResult`, `tableSchemas`, `buId`, `userQuestion`) + strict Pydantic outputs.
- Query Executor agent definition declares structured inputs (`sqlPlan`, `executionResult`, `userLanguage`) + enforces contract at MCP boundary.

**Apoc integration:** Your mock Foundry agents in `test_workflow.py` and `test_schemas.py` should return shapes matching the new typed contracts. The 22-query validation pack now has stricter contract validation; regenerate fixtures if needed to ensure `IntentResult.language_hint` and `SqlPlan` typing align with the new workflow expectations.

### Next Phase (Phase 1 Batch 3)

**Unblocked once all Batch 2 PRs merge:**
- Apoc: Expand adversarial query corpus (>2 injection attempts; Fase 7 readiness).
- Apoc: Profile query performance end-to-end (token counts, latencies) against live Foundry + SQL baseline (deferred to Fase 0b provisioning).
- Apoc: Collaborate with Oracle on pentest harness for S2/S3/S8 spike validation.
## Team Update — 2026-05-20T18:21:00Z

**Orchestration Complete:** Sprint 1 kickoff successful.

- Mouse: MAF workflow design + MCP tools → PR #16 ✓
- Tank: Database DDL + views + seed data → PR #15 ✓  
- Apoc: Query validation + KPI targets → PR #17 ✓

Status: All agents delivered on scope.
