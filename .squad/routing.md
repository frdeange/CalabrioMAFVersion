# Work Routing

How to decide who handles what.

## Routing Table

| Work Type | Route To | Examples |
|-----------|----------|----------|
| Arquitectura, decisiones cross-cutting, reviewer gates, Sprint 0 verdicts | 🏗️ Morpheus | Definir boundaries middleware ↔ workflow ↔ MCP, Sprint 0 spike verdicts (S1–S8), Plan B activation, dispute arbitration |
| Angular UI, SSE consumer, MSAL, UI streaming | ⚛️ Trinity | Chat component, EventSource handling, JWT acquisition contra Entra ID, progreso por executor, manejo transparente de rechazos guardrail |
| FastAPI Agent Host skeleton, FastMCP servers, APIM policies | 🔧 Tank | `POST /chat` con SSE, MCP Schema Provider (5 tools), MCP SQL Executor (4 capas), APIM JWT validation + header injection + HMAC signing |
| MAF Workflow, middleware, FoundryAgent, MCP binding, structured outputs | 🧠 Mouse | WorkflowBuilder con routing condicional, AgentMiddleware (PII/PromptShields/HMAC/SQL pre-val/audit), FunctionMiddleware (telemetry), Pydantic strict, OTel atributos custom, Spikes S1–S4/S6/S7 |
| Tests (unit ≥80%, E2E, guardrail por capa, sqlglot assertions, prompt injection) | 🧪 Apoc | pytest, Cypress/Playwright, coverage gates, corpus adversarial, 10 escenarios canónicos, soporte de pentest |
| Threat modeling, security review, HMAC key mgmt, RBAC, compliance docs | 🔒 Oracle | STRIDE, defense-in-depth review, Prompt Shields tuning, PII/DLP, RBAC matrix, pentest interno (Fase 7), partner-facing security docs |
| GitFlow, issues, PRs, branch policy, GitHub Actions, Docker, secrets pipelines | ⚙️ Switch | Issue templates con emoji, PR templates, labels (`area:*`, `phase:*`, `kind:*`), CODEOWNERS, GHA workflows reutilizables, Dockerfiles multi-stage |
| IaC (Bicep), networking, ACA, PE, KV, Cosmos provisioning | 🏛️ Diferido | Se contrata cuando arranque Fase 0b |
| Session logging | 📋 Scribe | Automático tras cada batch de trabajo |
| Backlog GitHub, untriaged issues, PR check-ins, CI failures | 🔄 Ralph | Cuando se active "Ralph, go" |

## Required Reviewers (CODEOWNERS-style)

Switch configurará un `.github/CODEOWNERS` que materialice esta tabla:

| Path / Concern | Required Reviewer(s) |
|----------------|----------------------|
| Cross-cutting arch, contratos, structured outputs Pydantic | 🏗️ Morpheus |
| Security middleware (PII, PromptShields, HMAC, SQL pre-val) | 🔒 Oracle + 🧠 Mouse |
| APIM policies (JWT validation, header injection, HMAC signing) | 🔒 Oracle + 🔧 Tank |
| MCP server guards (RBAC, SQL injection layers) | 🔒 Oracle + 🔧 Tank |
| Key Vault / Managed Identity / Private Endpoint / RBAC config | 🔒 Oracle + ⚙️ Switch |
| MAF Workflow, FoundryAgent, MCPStreamableHTTPTool binding | 🧠 Mouse + 🏗️ Morpheus |
| FastAPI app code (paths no-seguridad) | 🔧 Tank |
| Angular UI | ⚛️ Trinity |
| GHA workflows, branch protection, secrets pipelines | ⚙️ Switch + 🔒 Oracle |
| Tests | 🧪 Apoc |

## Issue Routing

| Label | Action | Who |
|-------|--------|-----|
| `squad` | Triage: analyze issue, assign `squad:{member}` label | Lead |
| `squad:{name}` | Pick up issue and complete the work | Named member |

### How Issue Assignment Works

1. When a GitHub issue gets the `squad` label, the **Lead** triages it — analyzing content, assigning the right `squad:{member}` label, and commenting with triage notes.
2. When a `squad:{member}` label is applied, that member picks up the issue in their next session.
3. Members can reassign by removing their label and adding another member's label.
4. The `squad` label is the "inbox" — untriaged issues waiting for Lead review.

## Rules

1. **Eager by default** — spawn all agents who could usefully start work, including anticipatory downstream work.
2. **Scribe always runs** after substantial work, always as `mode: "background"`. Never blocks.
3. **Quick facts → coordinator answers directly.** Don't spawn an agent for "what port does the server run on?"
4. **When two agents could handle it**, pick the one whose domain is the primary concern.
5. **"Team, ..." → fan-out.** Spawn all relevant agents in parallel as `mode: "background"`.
6. **Anticipate downstream work.** If a feature is being built, spawn the tester to write test cases from requirements simultaneously.
7. **Issue-labeled work** — when a `squad:{member}` label is applied to an issue, route to that member. The Lead handles all `squad` (base label) triage.
