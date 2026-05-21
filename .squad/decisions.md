# Decisions Log

**Last updated:** 2026-05-21T15:24:47Z

---

## 2026-05-19 — Sprint 0 Plan — 8 Spikes (S1–S8)

**By:** Morpheus (Lead / Architect)  
**Recorded:** 2026-05-19T13:38:00Z (via Scribe merge from inbox)

### What

Sprint 0 (Fase 0a) is the 8-spike validation gate defined in §9.6 of `propuesta-arquitectura-modernizada.md`. Each spike validates one technical assumption that — if wrong — would force an architecture pivot. RED on any spike triggers the documented Plan B (also defined in §9.6, column "Plan B si falla").

### Why

§9.6 is explicit: *"NO empieces a construir sin haber validado los spikes. Si algún spike sale RED, ajusta el diseño antes de avanzar."* (§9.6, §11 closing recommendations). We commit to the gate before committing to the design.

### The 8 spikes

| # | Title | Owner | Reviewer | Issue | Plan B (from §9.6) |
|---|-------|-------|----------|-------|--------------------|
| S1 | FoundryAgent + MCPStreamableHTTPTool (Local MCP) | mouse | morpheus | [#2](https://github.com/frdeange/CalabrioMAFVersion/issues/2) | `Agent(client=FoundryChatClient(...))` in code (lose Foundry Studio UI) |
| S2 | AgentMiddleware + FunctionMiddleware on FoundryAgent | mouse | morpheus + oracle | [#3](https://github.com/frdeange/CalabrioMAFVersion/issues/3) | Move per-tool checks to custom executor wrappers in the Workflow |
| S3 | Custom HTTP headers in MCPStreamableHTTPTool (`x-user-context`) | mouse | morpheus + oracle | [#4](https://github.com/frdeange/CalabrioMAFVersion/issues/4) | Subclass MCPStreamableHTTPTool or use MCP SDK directly |
| S4 | Structured outputs (`json_schema` strict) on FoundryAgent | mouse | morpheus | [#5](https://github.com/frdeange/CalabrioMAFVersion/issues/5) | `json_object` + defensive Pydantic validation in middleware |
| S5 | W3C `traceparent` propagation end-to-end | tank | morpheus | [#6](https://github.com/frdeange/CalabrioMAFVersion/issues/6) | Manual `traceparent` injection at each hop after Foundry; document gap |
| S6 | WorkflowBuilder conditional edges with FoundryAgent | mouse | morpheus | [#7](https://github.com/frdeange/CalabrioMAFVersion/issues/7) | Custom Python executor that receives output and invokes next agent |
| S7 | Streaming SSE end-to-end (`workflow.run_stream`) | mouse | morpheus | [#8](https://github.com/frdeange/CalabrioMAFVersion/issues/8) | Polling fallback (client polls status endpoint) |
| S8 | Foundry consuming AOAI via Private Endpoint | tank | morpheus + oracle | [#9](https://github.com/frdeange/CalabrioMAFVersion/issues/9) | Restricted public access on AOAI with IP allowlist scoped to Foundry |

**Decision deadline (per spike):** End of Sprint 0 — target 2026-05-26 (≈ 5 working days from 2026-05-19 kickoff per §10.1).

### Ownership split actually used

- **Mouse:** S1, S2, S3, S4, S6, S7 (all MAF / FoundryAgent / Workflow / MCP-client surface area)
- **Tank:** S5, S8 (cross-hop OTel propagation through APIM; Foundry ↔ AOAI Private Endpoint network primitive)

§9.6 *does not* explicitly assign owners — it only lists spike, hypothesis, validation, Plan B. The split above therefore matches the prior coordinator analysis verbatim. Recording it here so it's the canonical Sprint-0 assignment.

### Plan B options

Plan B is **defined per spike in §9.6** (column 5) and copied into the table above. No spike is missing a Plan B definition.

### Exit criteria for Sprint 0

- All 8 spikes resolved (GREEN, or AMBER with mitigation in `.squad/decisions.md`, or RED with Plan B activated + arch-pivot proposal merged).
- 0 unmitigated RED verdicts.
- Morpheus signs off in `.squad/decisions.md` to authorize Fase 0b kickoff (§10.2 — Fase 0a DoD: *"Todos los spikes S1–S8 con veredicto documentado en `spike-results.md`. Cualquier RED tiene plan B aplicado y aprobado por el tech lead."*).

### Ambiguities for Kiko to resolve

These do **not** block the planning gate — but they do affect spike execution. Flagging now:

1. **§9.6 silent on ownership.** §9.6 lists the 8 spikes but does not name owners. I've used the prior coordinator split (Mouse vs Tank as above). Confirm or correct.
2. **S8 vs Infra deferral.** Active decision *"Infra / IaC diferido"* defers IaC until Fase 0b. S8 (Foundry + AOAI PE) requires at least manual provisioning (AOAI + PE in a sandbox VNET) inside Sprint 0. Options for Kiko:
   - **(a)** Approve manual sandbox provisioning for S8 in Sprint 0 (Tank executes; no IaC commitment).
   - **(b)** Defer S8 to Fase 0b along with IaC — then Sprint 0 ships with 7/8 spikes resolved and S8 becomes a Fase 0b gate.
3. **S5 dependency on APIM.** Full E2E `traceparent` validation ideally goes through APIM. APIM provisioning is also part of the deferred IaC. Spike body proposes a reverse-proxy stub as an acceptable substitute; confirm that satisfies the "end-to-end" intent of §9.6 / §6.
4. **Sprint 0 duration.** §10.1 says 5 working days; the task brief mentioned "~10 working days". Issues use 5 days (matches §10.1, target 2026-05-26). Confirm we want to stick to 5.

### Status

Sprint 0 is **planned**. 8 issues open (#2–#9). `docs/spike-results.md` template committed. Mouse owns 6 spikes; Tank owns 2. Plan B options are defined per §9.6 for every spike. No RED verdicts can be acted on until ambiguities above are resolved (specifically the S8 manual-provisioning question if S8 goes RED).

Reviewer protocol reminder: on any spike-PR rejection, a different agent revises (per "Reviewer protocol — strict lockout" decision).

---


 ## 2026-05-19 — Sprint 0 user resolutions (Q1–Q4)

**By:** Kiko de Ángel (user / product owner); recorded by Morpheus  
**Resolved:** 2026-05-19T16:33:00Z  
**Recorded in ledger:** 2026-05-19T17:25:00Z (via Scribe)

All 4 ambiguities from the Sprint 0 plan have been resolved by the project lead. The resolutions are now active across issues #2–#9 and supporting documentation.

| # | Ambiguity | Resolution | Impact |
|---|-----------|-----------|--------|
| **Q1** | Spike ownership (§9.6 silent) | **Confirmed as-is.** Mouse owns S1, S2, S3, S4, S6, S7 (6 spikes). Tank owns S5, S8 (2 spikes). Oracle co-reviews S2, S3, S8. | Canonical assignment now recorded. No issue changes needed. |
| **Q2** | S8 feasibility (PE vs public) | **S8 reformulated: Public endpoint + Managed Identity (Entra ID).** Private Endpoint dropped from PoC scope. New hypothesis: `disableLocalAuth=true` + 8 mandatory mitigations sufficient for GREEN. S8-bis (PE validation) deferred to Phase 7 (Hardening). Cross-reference: ADR-001. | Issue #9 title + body rewritten; `docs/spike-results.md` Verdict Summary and S8 per-spike section updated. Applied to all 8 issues: deadline line rewritten. |
| **Q3** | S5 gateway (stub vs real) | **APIM Standard v2 real, manually provisioned** in Kiko's PoC sandbox. No reverse-proxy stub. Public-endpoint exception documented in ADR-001. | Issue #6 Dependencies/Blockers and Inputs/Artifacts sections updated. ADR-001 cross-reference added. |
| **Q4** | Sprint 0 duration | **Flexible, no hard deadline.** Best-effort, parallelization expected. User verbatim: *"No te preocupes por la duración, es una PoC que podemos hacer poco a poco. Haremos todo lo posible y si paralelizamos tareas conseguiremos eficientar."* | All 8 issues (#2–#9): deadline line updated. `docs/spike-results.md` header + Exit Criteria + User resolutions log updated. |

**Applied to:**
- Issues #2–#9: deadline language updated across all spike issues.
- Issue #6 (S5): Dependencies/Blockers; Inputs/Artifacts; ADR-001 cross-link.
- Issue #9 (S8): full title + body rewrite; 8 mitigations listed; ADR-001 binding scope.
- `docs/spike-results.md`: Verdict Summary (gate reformulation), per-spike S5/S8 sections, Exit Criteria, User resolutions log (Q1–Q4 table).

---


 ## 2026-05-19 — Security decisions: ADR-001 (PoC AOAI + APIM public-endpoint exception)

**By:** Oracle (Security / Compliance); Kiko de Ángel + Morpheus (deciders)  
**Status:** Accepted  
**Branch:** `squad/oracle-adr-001-public-endpoint-exception` (PR #11 pending)  
**Full text:** `docs/adr/ADR-001-poc-aoai-apim-public-endpoint.md`

### Scope

- **Sprint 0 only** (Fase 0a, expires at phase close).
- **Resources:** Azure OpenAI + API Management.
- **Applies to spikes:** S5 (end-to-end `traceparent` via APIM), S8 (Foundry → AOAI auth).
- **PoC constraint:** Synthetic/anonymized data only; single-tenant (Kiko's sandbox); time-limited ≤ 5 working days.
- **Production unchanged:** Private Endpoint remains mandatory per §3 and Fase 7 DoD (§10.2). No deviation authorized for production.

### Decision

- **Azure OpenAI:** Public endpoint + Entra ID via Managed Identity (no local key auth) + `disableLocalAuth=true`.
- **API Management:** Standard v2 tier, public endpoint, JWT validation enforced.
- **Provisioning:** Manual by Kiko in sandbox subscription. No Bicep/IaC committed (consistent with IaC-deferral decision).
- **Reversion trigger:** End of Sprint 0, any non-synthetic data, any external demo → sandbox deleted, PE re-introduced in Fase 0b+.

### 8 mandatory mitigations (all binding — required before S5/S8 execution)

1. **Key Vault for all secrets** — no keys in `.env`, code, CI logs, or chat. Managed Identity resolution at runtime.
2. **Entra ID + Managed Identity** on AOAI with `disableLocalAuth=true` to eliminate key-auth attack vector.
3. **Network ACL / IP allowlist on AOAI** — restricted to Foundry's outbound IPs and dev workstations only.
4. **Budget cap + alert** — hard cap €200/month per resource; alert at 80%.
5. **Diagnostic settings → Log Analytics** on AOAI and APIM — capture all request/response audit events (30-day retention).
6. **Content Safety / Prompt Shields** activated on every AOAI call (even PoC). Validates production integration pattern early.
7. **Synthetic / anonymized data only** — strict, no real Calabrio customer data, no exfiltrated production samples.
8. **Scope statement** in spike S5/S8 READMEs and this ADR: *"Public endpoint = justified exception for PoC. Production requires Private Endpoint per Phase 7 DoD (§10.2)."*

---


 ## 2026-05-19 — Transversal decisions: Local dev runtime (Docker Desktop)

**By:** Kiko de Ángel (user); Coordinator dispatch; Scribe record  
**Decision:** Docker Desktop + `docker-compose` for **all Python components** of the PoC.

### Rationale

- **Fidelity with production:** Agent Host + MCPs will run in Azure Container Apps (Fase 1+). Local containers validate the same image layers, orchestration patterns, and OTel SDK behavior that production uses.
- **Orchestration capability:** `docker-compose.yml` allows Agent Host + 2 MCP servers + optional local SQL database in one command (vs. scattered `uvicorn` processes).
- **Early validation:** OTel SDK behavior inside containers + network propagation through container bridge + S5 `traceparent` chain can be validated in Sprint 0 (blocking discovery that would otherwise fail in Fase 1).

### Scope

- **Applies to:** FoundryAgent host, WFM MCP, Forecast MCP, any Python test harnesses.
- **Agent ownership:** Tank delivers `Dockerfile` + `docker-compose.yml` as reusable artifact during S1/S5 spike execution.
- **Reuse:** Mouse uses Tank's containers for local dev on S1–S4, S6, S7. Apoc uses same containers for adversarial testing.
- **Not affected:** Trinity's frontend SPA dev server remains as-is (Vite or equivalent — separate concern).
- **Azure resources:** APIM (S5) and AOAI (S8) remain on Azure public endpoints (not containerized) per ADR-001.

### Local dev chain for reference

```
Browser (local)
  ↓
APIM (Azure public endpoint)
  ↓
Agent Host (Docker Desktop container)
  ↓
MCP-WFM (Docker Desktop container)
  ↓
Azure SQL (remote Azure endpoint)
```

**User quote (verbatim):** *"De forma local podemos probar las aplicaciones que desarrolles usando del Docker Desktop que tengo."*

---
# Squad Decisions

## Active Decisions

### 2026-05-19: Universe casting — The Matrix
**By:** Kiko de Ángel (via Squad)
**What:** Equipo de 7 agentes + Scribe + Ralph, cast de The Matrix: Morpheus (Lead), Trinity (Frontend), Tank (Backend APIs/MCP), Mouse (MAF Orchestrator), Apoc (Tester), Oracle (Security), Switch (DevOps). Inception fue propuesto inicialmente pero no está en el allowlist; The Matrix encaja mejor por la analogía multi-agente + defense-in-depth + capas de realidad.
**Why:** El proyecto necesita Lead + Tester + Security dedicados además del equipo técnico base (Frontend, Backend, MAF, DevOps). 5 roles activos inicialmente propuestos por el owner se expandieron a 7 tras evaluación de complejidad.

### 2026-05-19: Per-agent model preferences
**By:** Kiko de Ángel (via Squad)
**What:** Asignación de modelos por agente (detalle en cada `charter.md → ## Model`):
- 🏗️ Morpheus (Lead): `claude-opus-4.7` → bump a `claude-opus-4.7-high` para Sprint 0 RED → Plan B
- ⚛️ Trinity (Frontend): `gpt-5.3-codex` → bump a `claude-sonnet-4.6` para state management complejo, o `claude-opus-4.5` para vision
- 🔧 Tank (Backend): `gpt-5.3-codex` → bump a `claude-sonnet-4.6` para async/error edge cases
- 🧠 Mouse (MAF): `claude-sonnet-4.6` (NO codex porque MAF es novel y necesita razonamiento general) → bump a `claude-opus-4.7` para middleware tricky
- 🧪 Apoc (Tester): `gpt-5.3-codex` → bump a `claude-opus-4.7` para corpus adversarial
- 🔒 Oracle (Security): `claude-opus-4.7` → bump a `claude-opus-4.7-high` para threat models completos
- ⚙️ Switch (DevOps): `gpt-5.3-codex` → bump down a `claude-haiku-4.5` para markdown templates
- 📋 Scribe: `claude-haiku-4.5` (fijo, nunca bump)
**Why:** Cost-first salvo cuando se escribe código (Sonnet/codex) o cuando hay decisión de alto impacto arquitectura/seguridad (Opus). `gpt-5.3-codex` como default en 4 agentes code-heavy (Trinity, Tank, Apoc, Switch) ahorra significativamente sin sacrificar calidad — su talón de Aquiles es framework novelty, por eso Mouse se queda en Sonnet.

### 2026-05-19: Infra / IaC diferido
**By:** Kiko de Ángel (via Squad)
**What:** El rol de Infra / IaC (Bicep, VNET, ACA env, Private Endpoints, APIM provisioning, KV, Cosmos, Foundry project provisioning) se contrata cuando arranque la **Fase 0b** del plan. Hasta entonces, queda explícitamente diferido.
**Why:** PoC prioriza app development; la infra se levanta cuando hay app code listo para deploy. Switch puede preparar los Dockerfiles y pipelines de CI sin que IaC esté lista todavía.

### 2026-05-19: DevOps estricto desde día 1
**By:** Kiko de Ángel (via Squad)
**What:** Todo trabajo pasa por GitHub Issue → branch `squad/{issue-number}-{kebab-slug}` → PR con required reviewers automáticos (CODEOWNERS) según área → merge a `develop`. Issue templates con emoji + tags (🐛 ✨ 🔐 🧪 📚 🏗️ 🔍 🔧 🚀). Labels duales: `area:*` (dominio técnico) + `phase:0a-spike` … `phase:8-tuning`. Branch protection en `main` y `develop`. Conventional commits enforced. Actions pinneadas a SHA. Switch monta esta infra de DevOps como **primera tarea**, antes de que el resto del equipo abra un solo PR.
**Why:** Auditabilidad, trazabilidad PR↔Issue, enforcement automático de reviewers de seguridad (Oracle obligatorio en cualquier path security-relevant), supply-chain hygiene.

### 2026-05-19: Reviewer protocol — strict lockout
**By:** Kiko de Ángel (via Squad)
**What:** Si un reviewer rechaza un PR, el autor original **NO** puede ser quien lo arregle. El coordinator nombra a otro agente (o uno nuevo) para la revisión. Lockout aplica al artefacto rechazado durante ese ciclo de revisión. Si la revisión también se rechaza, el revisor de la revisión también queda lockout, y un tercer agente revisa.
**Why:** Calidad, diversidad de perspectiva, evitar que un mismo agente itere infinitamente sobre su propio código rechazado. Política estándar Squad.

### 2026-05-19: Decisión clave de arquitectura — Local MCP (no Hosted)
**By:** Kiko de Ángel (vía propuesta de arquitectura §2.4)
**What:** Los MCP servers se llaman desde **MAF en el Agent Host** (Local MCP), no desde Foundry (Hosted MCP). Foundry declara las tools por nombre + schema sin URL; MAF orquesta el bucle de tool calls.
**Why:** Habilita `FunctionMiddleware` por tool call (Hosted no lo permite), propagación controlada de `x-user-context` con HMAC, RBAC por usuario en el MCP, observabilidad OTel completa intra-VNET, superficie de ataque mínima (MCP nunca expuesto fuera de la VNET). Trade-off aceptado: +1 hop de latencia (~20ms intra-VNET).

### 2026-05-19: Decisión clave de arquitectura — 3 agentes especializados con mínimo privilegio
**By:** Kiko de Ángel (vía propuesta de arquitectura §2.1)
**What:** 3 FoundryAgent clients separados: Intent (sin tools), SqlBuilder (sólo Schema MCP), Executor (sólo SqlExec MCP). HMAC firma el SqlPlan entre SqlBuilder y Executor para integridad inter-agente.
**Why:** Si un agente sufre prompt injection, el blast radius está acotado por sus tools. Auditoría granular por salto entre agentes. SqlBuilder no puede ejecutar; Executor no puede inventar SQL.

### 2026-05-19: Switch — DevOps Foundations Bootstrap
**By:** Switch (for Kiko de Ángel)
**What:** GitHub issue templates (9 types + config.yml), PR template with reviewer lockout reminder, CODEOWNERS from `.squad/routing.md`, label sync script, branch protection for `main` and `develop` (initially `master`, renamed to `main` as part of this same bootstrap), CI/CD scaffolding (pr-validation, secret-scan, commitlint workflows), Dependabot, triage helper script, and secret scanning enabled.
**Why:** Foundation for audit trail, CODEOWNERS automation, required reviewer routing, Conventional Commits enforcement, and supply-chain security before team opens first PRs.
**Status:** PR #1 (draft) on `squad/0-devops-foundations`

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here (append-only — never edit past entries to change meaning)
- Agents propose decisions via `.squad/decisions/inbox/{agent}-{slug}.md`; Scribe merges into this file after each work batch
- Keep history focused on work; decisions focused on direction

---


 ## 2026-05-19 — DevOps Bootstrap Detail

**By:** Switch (for Kiko de Ángel)  
**Date:** 2026-05-19T12:55:46Z  
**Branch:** `squad/0-devops-foundations`

### What was created

- GitHub issue templates in `.github/ISSUE_TEMPLATE/` for bug, feature, security, test, docs, infra, spike, chore, and release; plus `config.yml` with blank issues disabled.
- PR checklist template at `.github/pull_request_template.md`, including reviewer lockout reminder from decision #5.
- CODEOWNERS at `.github/CODEOWNERS`, materialized from `.squad/routing.md` with repo-owner fallback and squad reviewer comments.
- Label automation script at `.github/scripts/sync-labels.ps1` and labels synchronized via `gh label create --force`.
- Branch protection payloads in `.github/branch-protection.main.json` and `.github/branch-protection.develop.json`, applied through `gh api` to `main` and `develop`.
- CI/CD scaffolding with pr-validation, secret-scan, and commitlint workflows.
- Dependabot baseline and triage helper script.

### Status

PR #1 on `squad/0-devops-foundations` carrying full DevOps bootstrap with reviewed + approved changes.

---


 ## 2026-05-19 — Branch Rename: `master` → `main`

**By:** Switch (for Kiko de Ángel)

### What changed

- Default branch renamed atomically from `master` to `main` via GitHub API.
- Open PRs auto-retargeted by GitHub (notably PR #10 to `main`).
- PR #1 updated to remove hardcoded `master` references in governance artifacts.

### Why

Modernization and alignment with GitHub's post-2020 default branch convention.

### Impact

- All branch protection and workflow filters now reference `main`.
- All new branches should be created from `main` (or `develop` per GitFlow).

---


 ## 2026-05-19 — PR #1 Copilot Review Round 2 Resolution

**By:** Switch (for Kiko de Ángel)

**What:** Addressed 17 net-new Copilot review comments on PR #1. Unified actions/checkout SHA to v6.0.2 across all workflows, added container-build to required_status_checks, staged .squad/routing.md, applied master→main fixes, and used append pattern for orchestration-log and cross-agent histories.

**Why:** Maintain factual consistency while respecting append-only governance and supply-chain hygiene.

**Status:** Committed to squad/0-devops-foundations, all 17 threads replied.

---


 ## 2026-05-19 — PR #1 Copilot Review Round 3 Resolution

**By:** Switch (for Kiko de Ángel)  
**When:** 2026-05-19T20:04:40Z–20:04:41Z

**What:** Addressed 2 net-new Copilot comments (sync-labels.ps1 and squad-issue-assign.yml).
- **Fix A:** Removed `squad` + `squad:*` entries from `.github/scripts/sync-labels.ps1`. PS1 owns only static taxonomy (`kind:*`, `area:*`, `phase:*`). `.github/workflows/sync-squad-labels.yml` is authoritative for governance labels.
- **Fix B:** In squad-issue-assign.yml, promoted `COPILOT_ASSIGN_TOKEN` to job-level env; gated acknowledgment step; added token guard; added remediation warning comment.

**Bootstrap note:** After PR #1 merge, run `Sync Squad Labels` workflow via `workflow_dispatch` to ensure squad:* labels exist.

**Status:** Committed on `squad/0-devops-foundations`, both threads replied.

---


 ## 2026-05-20 — Sprint 1 Foundry Agent Provisioning + Workflow Skeleton

**By:** Mouse  
**Requested by:** Kiko de Ángel  
**Timestamp:** 2026-05-20T23:53:36Z

### What

Implemented Foundry-side bootstrap and Agent Host workflow skeleton:

1. **`scripts/provision_agents.py`** — provisions three persisted Foundry agents (`wfm-intent-classifier`, `wfm-sql-builder`, `wfm-query-executor`) from YAML prompts using `azure-ai-projects>=2.0.0`.
2. **Foundry prompts** under `src/agent_host/prompts/` for intent classification, SQL planning, and execution/result formatting.
3. **`src/agent_host/app/schemas.py`** — strict Pydantic v2 workflow contracts for intent routing, SQL plans, execution formatting.
4. **`src/agent_host/app/workflow.py`** — pre-MAF skeleton with Foundry agent orchestration, catalog caching, conditional pipeline, error handling, and TODO hooks for middleware, HMAC, Prompt Shields, SQL pre-validation, OTel.

### Why

MAF cannot CRUD Foundry agents, so Sprint 1 needs separate provisioning. Skeleton locks in q14 metadata-first route while staying compatible with local-MCP decision and three-agent minimum-privilege split.

### Consequences

- Foundry agent creation repeatable and versioned from repo-managed prompts.
- Agent Host has explicit structured-output contracts and orchestration shell ready for native MAF/MCPStreamableHTTPTool wiring.
- Error handling and caching codified early, reducing prompt drift and integration ambiguity.

---


 ## 2026-05-20 — MAF Workflow Design: Dynamic Metadata + Three Specialized Agents

**By:** Mouse  
**Date:** 2026-05-20T18:13:00Z

### What

Sprint 1 workflow splits WFM Supervisor into three specialized agents:
1. Intent Classifier / Router
2. SQL Builder
3. Query Executor + Formatter

Workflow stays fully metadata-driven via three MCP tools:
- `listTables()` from `_metadata.catalog_tables`
- `getSchema(table_name)` from `_metadata.catalog_columns` and `_metadata.catalog_joins`
- `executeQuery(sql)` with SELECT-only validation, active-table whitelist, row cap, timeout

### Why

Preserves q14 (metadata-first) and minimum-privilege decision (§2.1):
- Prompts unchanged when new domains added
- Metadata carries schema knowledge, not prompt text
- Router caches lightweight catalog once per session
- SQL Builder reasons over only shortlisted tables
- Executor enforces final safety before SQL Server

### Consequences

- Token usage below target envelope (cached listTables(), shortlisted getSchema())
- Prompt maintenance cost flat as domains grow
- SQL execution read-only, MI-authenticated via UAI `calabriomaf-uais`
- Empty/failed metadata responses become first-class workflow outcomes

---


 ## 2026-05-20 — Sprint 1 WFM Database Baseline (Azure SQL)

**By:** Tank  
**Requested by:** Kiko de Ángel  
**Timestamp:** 2026-05-20T18:13:00Z

### What

Sprint 1 database deliverable — four idempotent SQL scripts under `database/`:

1. **`01-schemas-and-tables.sql`** — schemas (wfm, absence, overtime, scheduling, _metadata), tables (People, Absence, Overtime, Scheduling, metadata catalog), FK guards.
2. **`02-views.sql`** — analytics schema, LLM-facing views (vw_PersonDetail, vw_AbsenceRequest, vw_OvertimeRequest, vw_Scheduling).
3. **`03-seed-data.sql`** — one BU (CWFM-DEMO), 3 sites, 6 teams, 50 agents, 8 skills, 1000 absence requests, 200 overtime requests, 500 shifts, _metadata catalog deterministically seeded.
4. **`04-grant-readonly.sql`** — UAI user `[calabriomaf-uais]` with read-only role (db_datareader), SELECT on analytics and _metadata, verification queries.

### Why

Establishes minimum secure, queryable WFM data platform for MCP SQL Executor and dynamic schema-discovery flow (q14/q15/q16), keeping tenant scoping and least-privilege explicit.

### Impact

- Backend has concrete Azure SQL baseline aligned with People/Absence/Overtime/Scheduling domains.
- LLM query surface stable and documented through metadata catalog.
- Security posture tightened by defaulting UAI to read-only.

---


 ## 2026-05-20 — Sprint 1 Query Validation Pack (Apoc)

**By:** Apoc  
**Recorded:** 2026-05-20T18:13:00Z  
**Scope:** Sprint 1 acceptance assets for q14 (dynamic schema discovery PoC)

### What

Created reusable validation pack under `tests/query-validation/`:
- 22 NL queries (20 safe + 2 adversarial)
- Expected analytics views and tool-call envelopes
- KPI targets (token, latency, cost, accuracy)
- Execution guidance for manual scoring

### Why

PoC needs stable, reviewable test set measuring the real promise of fully dynamic path: correct supervisor answers with much lower prompt/schema payload vs. Calabrio baseline.

### Decision Requested

Adopt `tests/query-validation/` as canonical Sprint 1 acceptance pack for dynamic schema discovery evaluations and regression checks.

### Consequences

- Future workflow runs compared against same KPI targets and rubric.
- BU-filter compliance is explicit pass/fail per safe business query.
- Q21/Q22 establish minimum adversarial guardrail smoke test per validation cycle.

---


 ## 2026-05-20 — Apoc Sprint 1 Batch 2 test strategy

**By:** Apoc  
**Recorded:** 2026-05-20T23:53:36Z  
**Scope:** `src/agent_host/tests/` and `tests/query-validation/`

### What

Adopted a **contract-first QA strategy** for Batch 2:
- Added schema, Foundry client, workflow, and `/chat` endpoint test scaffolding that runs even when implementation modules are not merged yet.
- Added explicit `@pytest.mark.integration` smoke tests for real implementation modules (`app.workflow`, `app.foundry_client`, and real `app.main` chat endpoint), skipped when unavailable.
- Added `tests/query-validation/test_query_kpis.py` to validate 22 canonical/adversarial query contracts with `sqlglot`, BU-filter checks, and analytics table whitelist patterns.

### Why

Mouse and Tank are delivering production code in parallel. QA needs immediate regression signal without blocking on merge order, while still preserving future integration gates.

### Consequences

- Test scaffolding can run now on `develop` with no Foundry/Azure runtime dependencies.
- Once implementation lands, integration markers provide direct hooks for turning on full contract verification.
- Query KPI validation is now executable and versioned as a repeatable guardrail suite.

---


 ## 2026-05-20 — Tank Agent Host wiring (Sprint 1 Batch 2)

**By:** Tank  
**Recorded:** 2026-05-20  
**Scope:** `src/agent_host`

### Decision

Implement a lightweight Foundry SDK wrapper in Agent Host and wire `/chat` to the workflow integration seam with defensive lazy-loading.

### Why

- The host needs a stable, testable abstraction over Foundry conversations/responses before full workflow orchestration lands.
- Mouse-owned `workflow.py` is not guaranteed to exist on this branch, so runtime-safe lazy import/error fallback is required to keep the host bootable.
- Sprint 1 requires `/chat` response fields (`intent`, `sql`, `answer`, `conversation_id`, timing) to support the 3-agent pipeline contract.

### Applied changes

1. Added runtime dependencies for Foundry + identity + MCP HTTP + YAML prompt loading in `src/agent_host/pyproject.toml`.
2. Extended `Settings` with:
   - `model_deployment`
   - `mcp_wfm_url`
   - `intent_agent_name`
   - `sql_builder_agent_name`
   - `query_executor_agent_name`
   - `default_bu_id`
3. Added `FoundryClientManager` singleton wrapper in `app/foundry_client.py`:
   - lazy init of `AIProjectClient` and OpenAI client
   - timeout-wrapped calls
   - `create_conversation`, `chat`, `chat_structured`, `health_check`
   - structured error logging
4. Updated `app/main.py`:
   - defensive workflow import seam with TODO note for Mouse merge timing
   - `/ready` now includes Foundry connectivity probe
   - `/chat` now accepts `bu_id` + `conversation_id`, builds session context, executes workflow, and returns enriched payload
5. Updated `app/models.py` request/response schemas for workflow payload shape.

### Consequences

- Agent Host now has an operational Foundry plumbing baseline without coupling to unfinished workflow code.
- Once Mouse's workflow implementation is merged, only adapter-level alignment may be needed (class name and output shape).

---


 ## 2026-05-21 — Tank SSE `/chat` endpoint negotiation

**By:** Tank  
**Recorded:** 2026-05-21  
**Issue:** #22  
**Branch:** `feature/sprint2-sse-endpoint`

### Decision

Implemented SSE streaming on `POST /chat` using HTTP `Accept` header negotiation:

- `Accept: text/event-stream` → `StreamingResponse` (`text/event-stream`)
- Any other accept value → existing JSON `ChatResponse` (backward compatible)

### Implementation details

1. Added `_stream_chat()` async generator in `app/main.py` that:
   - Resolves workflow and conversation id via `asyncio.to_thread(...)`
   - Calls blocking `workflow.run_streaming(message, bu_id, session_context)` via `asyncio.to_thread(...)`
   - Iterates events safely through thread offloading and emits `data: {json}\n\n`
   - Stops on client disconnect
   - Emits terminal SSE error event on workflow failure
2. Added `WorkflowEventResponse` API model in `app/models.py` for SSE payload shape.
3. Added CORS middleware for Angular dev origins (`http://localhost:4200`, `http://127.0.0.1:4200`) and exposed SSE-related headers.
4. Added endpoint tests in `tests/test_sse_endpoint.py` for:
   - SSE happy-path stream payloads
   - Accept negotiation (SSE vs JSON)
   - SSE error event when streaming workflow fails
   - Backward-compatible JSON behavior

### Notes

- No `sse-starlette` dependency added; raw FastAPI `StreamingResponse` is sufficient.
- `WorkflowEvent` import is wired to `app.schemas` with temporary fallback until Mouse's streaming schema merge lands.

---


 ## 2026-05-21 — Trinity Angular frontend scaffold (Issue #23)

**By:** Trinity  
**Recorded:** 2026-05-21  
**Branch:** (unknown)  
**Issue:** #23

### Decision

Scaffold the Angular 19 standalone frontend at `src/frontend` with a chat-first architecture: MSAL-based auth guard/interceptor, typed SSE chat streaming service, and per-executor progress UI components.

### Why

This keeps frontend contracts explicit for the backend workflow events, enforces strict TypeScript, and provides transparent UX states (Intent → SQL → Executing → Result) including guardrail rejection details.

### Implementation notes

- Added `@azure/msal-angular` and `@azure/msal-browser` to `src/frontend/package.json`.
- Implemented `core/auth` with `msal.config.ts`, `auth.guard.ts`, and `auth.interceptor.ts`.
- Implemented typed chat models/services and standalone chat UI components.
- Added environment configuration files and production file replacement.
- Added mobile-first responsive styles with light/dark theme variables and animated progress dots (no generic spinner).

---


 ## 2026-05-21 — User directives: ACA infra, APIM routing, Calabrio UI reference

**By:** Kiko de Ángel (via Copilot); recorded by Scribe  
**Recorded:** 2026-05-21T11:15–11:21:00Z

### Directive 1: ACA infrastructure ready

**Time:** 2026-05-21T11:15:00Z

**What:** Container Registry (calabriomafpocacr), Container Environment, and Container App have been created in rg-Calabriomafpoc. Currently running a dummy image. Update the image when the agent host Dockerfile is ready for deployment.

**Why:** User request — captured for team memory. Infra is no longer deferred for the container layer.

### Directive 2: Frontend routes through APIM

**Time:** 2026-05-21T11:16:00Z

**What:** The frontend NEVER talks directly to the backend. All traffic goes through APIM (calabriomafpoc-apim). This is part of the original architecture — APIM handles JWT validation, claim extraction, header injection, HMAC signing, and rate limiting.

**Why:** User request — captured for team memory. Security and architecture constraint.

### Directive 3: UI must match Calabrio reference design

**Time:** 2026-05-21T11:21:00Z

**What:** The frontend must visually match the existing Calabrio Supervisor Assist UI as closely as possible. Key design elements from the reference screenshots:
- Left sidebar with Calabrio branding (red logo, dark sidebar with navigation items)
- "Supervisor assist" header with info icon, "New chat" button (outlined, blue), Agent selector dropdown, green status dot + "Details" link
- Chat area: clean white background, centered greeting on empty state ("Hello, {Name}! What can I help you with today?")
- Message bubbles: user messages right-aligned (light purple/blue background), assistant messages left-aligned (light gray), no avatars
- Data tables rendered inline with blue header row (Calabrio brand blue), white alternating rows
- Input bar at bottom: "Type your message..." placeholder, blue send button (arrow icon), full width
- AI disclaimer footer: "Supervisor assist is a generative AI-based solution and may make mistakes"
- Overall: clean, professional, minimal — NOT a generic chatbot UI

**Why:** User request — the PoC should look like a real Calabrio product, not a prototype.

# Apoc — Sprint 1 Batch 2 test strategy

- **Recorded:** 2026-05-20T23:53:36Z
- **Agent:** Apoc
- **Scope:** `src/agent_host/tests/` and `tests/query-validation/`

## What
Adopted a **contract-first QA strategy** for Batch 2:
- Added schema, Foundry client, workflow, and `/chat` endpoint test scaffolding that runs even when implementation modules are not merged yet.
- Added explicit `@pytest.mark.integration` smoke tests for real implementation modules (`app.workflow`, `app.foundry_client`, and real `app.main` chat endpoint), skipped when unavailable.
- Added `tests/query-validation/test_query_kpis.py` to validate 22 canonical/adversarial query contracts with `sqlglot`, BU-filter checks, and analytics table whitelist patterns.

## Why
Mouse and Tank are delivering production code in parallel. QA needs immediate regression signal without blocking on merge order, while still preserving future integration gates.

## Consequences
- Test scaffolding can run now on `develop` with no Foundry/Azure runtime dependencies.
- Once implementation lands, integration markers provide direct hooks for turning on full contract verification.
- Query KPI validation is now executable and versioned as a repeatable guardrail suite.


### 2026-05-21T11:37:00Z: User directive — Separate ACA for frontend
**By:** Kiko de Ángel (via Copilot)
**What:** A new Container App `calabriomafpoc-acafrontend` has been created for the Angular frontend. The backend MAF orchestrator runs on the original ACA. Two separate Container Apps in the same Container Environment.
**Why:** User request — captured for team memory. Frontend and backend deployed independently.


### 2026-05-21T12:23:00Z: Architecture decision — Multi-tenant Entra ID
**By:** Kiko de Ángel (via Copilot)
**What:** The Entra ID App Registration must be multi-tenant (any organizational directory), not single-tenant. This enables users from different tenants to log in, demonstrating that the BU filter works per user/organization. Authority URL uses /common instead of /{tenantId}.
**Why:** PoC needs to show that different organizations see different data based on their identity claims (oid, tid → bu_id mapping).


### 2026-05-21T12:32:00Z: Entra ID App Registration complete
**By:** Kiko de Ángel (via Copilot)
**What:** App registration created in Entra ID:
- App Name: calabriomafpoc-supervisor-assist
- Client ID: 9dfbf018-d41b-4579-8b6c-e58d1a9a52be
- Tenant ID: 562029ef-9022-45a6-b255-40cd71ebb2ce
- Multi-tenant (any organizational directory)
- Application ID URI: api://9dfbf018-d41b-4579-8b6c-e58d1a9a52be
- Scope: access_as_user (admins and users consent)
- Authority: https://login.microsoftonline.com/common
- Redirect URIs: http://localhost:4200, http://localhost:8080
- SPA with PKCE (no client secret)
**Why:** Required for MSAL.js auth in frontend and JWT validation in APIM.


# Decision: Safety Middleware Stack for Agent Host

**Date:** 2026-05-21T12:52:42+02:00  
**Author:** Mouse (MAF Orchestrator Expert)  
**Issue:** #30  
**PR:** #34  
**Branch:** feature/sprint2-safety-middleware  

## Context

The Agent Host routes user natural-language queries through three Foundry agents (Intent ? SqlBuilder ? Executor). Without guardrails, a malicious user could inject prompts, leak PII, tamper with the SqlPlan between agents, or bypass SQL access controls.

## Decision

Implement a 4-layer defense-in-depth middleware stack in `app/middleware/`. Each layer is an independent, testable Python class with a standardized OTel span.

### Layer order (request path)

`
user input
  ? PromptShieldsMiddleware.check()      # Azure Content Safety, fail-closed
  ? PIIDetectorMiddleware.process()      # Presidio + regex, log/redact/block
  ? [Intent Agent call]
  ? [SqlBuilder Agent call]
  ? SQLValidator.validate_and_patch()    # sqlglot SELECT-only + analytics allowlist
  ? HMACSigner.sign()                    # Sign SqlPlan before Executor
  ? [Executor Agent call after verify]
  ? HMACSigner.verify_or_raise()         # Reject tampered plans
`

### Rejected alternatives

- **Hosted MCP middleware**: Not chosen � Local MCP gives us full middleware control inside the Agent Host Python process, enabling `FunctionMiddleware` and `ContextVar` propagation (see 2026-05-19 decision).
- **Single monolithic guardrail**: Not chosen � independent layers allow per-layer enable/disable via config and isolate failures.
- **Azure Content Safety for PII**: Not chosen as primary � Presidio runs locally without API latency; Azure CS is the fallback.

## Consequences

- Middleware is **not yet wired** into `workflow.py` � wiring happens next sprint.
- `GuardrailViolation` raised by any layer will propagate as a 422/403 to the API caller (wiring sprint decides HTTP mapping).
- `SQL_ALLOWED_VIEWS` must be kept in sync with Tank's view catalog � misconfiguration blocks all queries.
- Presidio SSN detection requires full spaCy model in production; regex fallback covers test environments.
- HMAC_SECRET rotation requires a coordinated deploy (both sign and verify use the same key).

## Test evidence

45 tests passing � `python -m pytest tests/test_middleware/ -v` (2026-05-21).

# 2026-05-21T12:52:42+02:00 — DevTunnel setup automation and local E2E guide

**By:** Switch  
**Requested by:** Kiko de Ángel  
**Branch:** `feature/sprint2-devtunnel-guide`

## Decision

Introduce a standard DevTunnel workflow for local E2E development behind APIM by adding:

1. A one-time setup script to create/reuse a persistent anonymous tunnel and port forwarding on `8000`.
2. A daily startup script to host the existing tunnel once local Docker services are running.
3. A local development guide documenting prerequisites, APIM named value wiring, daily workflow, environment switching, troubleshooting, and architecture.

## Why

- Keeps APIM as the single ingress and policy enforcement point (JWT, claims, CORS, rate limiting) while enabling local backend iteration.
- Reduces onboarding/ops friction by replacing manual CLI repetition with scripts.
- Makes local/cloud backend switching explicit through APIM Named Value `backend-url`.

## Implemented artifacts

- `scripts/devtunnel-setup.ps1`
- `scripts/devtunnel-start.ps1`
- `docs/local-dev-guide.md`
- `.env.example` (DevTunnel variables)


# 2026-05-21 — APIM policy strategy for Sprint 2 Issue #29

**By:** Tank  
**Requested by:** Kiko de Ángel  
**Scope:** `src/apim`

## Decision

Split APIM operation policies into two versioned XML artifacts:

1. `chat-api.xml` for `POST /chat` with security and traffic controls
2. `health-api.xml` for `GET /health` and `GET /ready` passthrough checks

Both use the APIM Named Value `{{backend-url}}` for backend target routing.

## Why

- `/chat` needs centralized API gateway enforcement (JWT validation, claim propagation, throttling) before backend execution.
- Health/readiness probes should remain lightweight and unauthenticated for platform diagnostics.
- Named Value routing allows instant DevTunnel ↔ ACA switching without policy rewrites.

## Applied details

- Entra validation uses multi-tenant OpenID metadata (`/common/v2.0/.well-known/openid-configuration`) with audience `api://9dfbf018-d41b-4579-8b6c-e58d1a9a52be`.
- User claims (`oid`, `tid`, `name`, `preferred_username`) are mapped to `x-user-*` headers for downstream context.
- Rate limiting set to `60` calls per `60` seconds keyed by `oid`.
- HMAC signing is documented as TODO pending Key Vault secret wiring.


# 2026-05-21 — Local Docker E2E stack (agent-host + mcp-wfm + frontend)

**By:** Tank  
**Requested by:** Kiko de Ángel  
**Branch:** `feature/sprint2-docker-local`

## Decision

Adopt a local Docker Compose topology with three services:

1. `agent-host` (FastAPI orchestrator, port `8000`)
2. `mcp-wfm` (FastAPI MCP server + ODBC driver 18, port `8001`)
3. `frontend` (Angular production build served by nginx, exposed on `8080`)

The frontend proxies `/api/*` traffic to `http://agent-host:8000`, and the orchestrator reaches MCP WFM at `http://mcp-wfm:8001/mcp` over the compose network.

## Why

- Enables `docker compose up` for local end-to-end workflows with cloud-backed Azure dependencies (Foundry, SQL, Key Vault).
- Keeps inter-service addresses stable through compose service names.
- Adds an explicit env template for local execution and optional service-principal auth inside containers.

## Implemented artifacts

- `src/agent_host/Dockerfile`
- `src/mcp_wfm/Dockerfile` (with `msodbcsql18`)
- `src/frontend/Dockerfile`
- `src/frontend/nginx.conf`
- `docker-compose.yml`
- `.env.example`
- `.dockerignore` files under each service directory


# Tank decision inbox — Agent Host wiring (Sprint 1 Batch 2)

**Date:** 2026-05-20  
**Author:** Tank  
**Scope:** `src/agent_host`

## Decision

Implement a lightweight Foundry SDK wrapper in Agent Host and wire `/chat` to the workflow integration seam with defensive lazy-loading.

## Why

- The host needs a stable, testable abstraction over Foundry conversations/responses before full workflow orchestration lands.
- Mouse-owned `workflow.py` is not guaranteed to exist on this branch, so runtime-safe lazy import/error fallback is required to keep the host bootable.
- Sprint 1 requires `/chat` response fields (`intent`, `sql`, `answer`, `conversation_id`, timing) to support the 3-agent pipeline contract.

## Applied changes

1. Added runtime dependencies for Foundry + identity + MCP HTTP + YAML prompt loading in `src/agent_host/pyproject.toml`.
2. Extended `Settings` with:
   - `model_deployment`
   - `mcp_wfm_url`
   - `intent_agent_name`
   - `sql_builder_agent_name`
   - `query_executor_agent_name`
   - `default_bu_id`
3. Added `FoundryClientManager` singleton wrapper in `app/foundry_client.py`:
   - lazy init of `AIProjectClient` and OpenAI client
   - timeout-wrapped calls
   - `create_conversation`, `chat`, `chat_structured`, `health_check`
   - structured error logging
4. Updated `app/main.py`:
   - defensive workflow import seam with TODO note for Mouse merge timing
   - `/ready` now includes Foundry connectivity probe
   - `/chat` now accepts `bu_id` + `conversation_id`, builds session context, executes workflow, and returns enriched payload
5. Updated `app/models.py` request/response schemas for workflow payload shape.

## Consequences

- Agent Host now has an operational Foundry plumbing baseline without coupling to unfinished workflow code.
- Once Mouse’s workflow implementation is merged, only adapter-level alignment may be needed (class name and output shape).

