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
