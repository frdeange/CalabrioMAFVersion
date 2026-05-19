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
