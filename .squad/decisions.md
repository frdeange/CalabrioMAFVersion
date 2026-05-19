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
**What:** GitHub issue templates (9 types + config.yml), PR template with reviewer lockout reminder, CODEOWNERS from `.squad/routing.md`, label sync script, branch protection for `master` and `develop`, CI/CD scaffolding (pr-validation, secret-scan, commitlint workflows), Dependabot, triage helper script, and secret scanning enabled.
**Why:** Foundation for audit trail, CODEOWNERS automation, required reviewer routing, Conventional Commits enforcement, and supply-chain security before team opens first PRs.
**Status:** PR #1 (draft) on `squad/0-devops-foundations`

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here (append-only — never edit past entries to change meaning)
- Agents propose decisions via `.squad/decisions/inbox/{agent}-{slug}.md`; Scribe merges into this file after each work batch
- Keep history focused on work; decisions focused on direction
