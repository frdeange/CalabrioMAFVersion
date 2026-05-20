# Decisions Log

**Last updated:** 2026-05-19T13:38:00Z

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
