# Sprint 0 — Spike Results

Last updated: 2026-05-19T16:33:00Z
Owner: Morpheus (verdict consolidation)

**Sprint 0 duration:** Best-effort, no hard deadline. Parallelization across agents is expected (per user directive 2026-05-19 — see "User resolutions log" below).

## Verdict Summary

| Spike | Title | Owner | Reviewer(s) | Issue | Verdict | Updated | Evidence |
|-------|-------|-------|-------------|-------|---------|---------|----------|
| S1 | FoundryAgent + MCPStreamableHTTPTool (Local MCP) | mouse | morpheus | [#2](https://github.com/frdeange/CalabrioMAFVersion/issues/2) | ⚪ Pending | — | — |
| S2 | AgentMiddleware + FunctionMiddleware on FoundryAgent | mouse | morpheus + oracle | [#3](https://github.com/frdeange/CalabrioMAFVersion/issues/3) | ⚪ Pending | — | — |
| S3 | Custom HTTP headers in MCPStreamableHTTPTool (`x-user-context`) | mouse | morpheus + oracle | [#4](https://github.com/frdeange/CalabrioMAFVersion/issues/4) | ⚪ Pending | — | — |
| S4 | Structured outputs (`json_schema` strict) on FoundryAgent | mouse | morpheus | [#5](https://github.com/frdeange/CalabrioMAFVersion/issues/5) | ⚪ Pending | — | — |
| S5 | W3C `traceparent` propagation end-to-end (APIM Standard v2 real, manually provisioned) | tank | morpheus | [#6](https://github.com/frdeange/CalabrioMAFVersion/issues/6) | ⚪ Pending | — | — |
| S6 | WorkflowBuilder conditional edges with FoundryAgent | mouse | morpheus | [#7](https://github.com/frdeange/CalabrioMAFVersion/issues/7) | ⚪ Pending | — | — |
| S7 | Streaming SSE end-to-end (`workflow.run_stream`) | mouse | morpheus | [#8](https://github.com/frdeange/CalabrioMAFVersion/issues/8) | ⚪ Pending | — | — |
| S8 | Foundry consuming AOAI via **public endpoint + Managed Identity (Entra ID)** — PoC only | tank | morpheus + oracle | [#9](https://github.com/frdeange/CalabrioMAFVersion/issues/9) | ⚪ Pending | — | — |

Legend: ⚪ Pending · 🟢 GREEN · 🟡 AMBER · 🔴 RED

**Ownership split (confirmed by Kiko 2026-05-19):** Mouse owns 6 spikes (S1, S2, S3, S4, S6, S7); Tank owns 2 (S5, S8); Oracle co-reviews S2, S3, S8.

**Deferred:** **S8-bis (validating Private Endpoint for AOAI) is deferred to Phase 7 (Hardening)** — see `propuesta-arquitectura-modernizada.md` §10.2. The S8 PoC scope is now public-endpoint + MI with the 8 mandatory mitigations enumerated in ADR-001 and in issue #9.

**Cross-reference for S5 and S8:** `docs/adr/ADR-001-poc-aoai-apim-public-endpoint.md` (drafted in parallel by Oracle on branch `squad/oracle-adr-001-public-endpoint-exception`).

## Sprint 0 Exit Criteria

- All 8 spikes resolved (GREEN, or AMBER with mitigation committed to `.squad/decisions.md`, or RED with Plan B activated and arch-pivot proposal merged).
- 0 unmitigated RED verdicts.
- Morpheus signs off in `.squad/decisions.md` to authorize Fase 0b kickoff.
- No hard calendar deadline — parallelization across agents is the expected mechanism for shortening wall-clock time.

## Per-Spike Detail

Owners append their verdict here with evidence links — code commits, test runs, log snippets, sequence diagrams. One section per spike.

### Spike S1: FoundryAgent + MCPStreamableHTTPTool (Local MCP)
**Owner:** mouse · **Issue:** [#2](https://github.com/frdeange/CalabrioMAFVersion/issues/2) · **Verdict:** ⚪ Pending

_To be filled by the owner._

### Spike S2: AgentMiddleware + FunctionMiddleware on FoundryAgent
**Owner:** mouse · **Issue:** [#3](https://github.com/frdeange/CalabrioMAFVersion/issues/3) · **Verdict:** ⚪ Pending

_To be filled by the owner._

### Spike S3: Custom HTTP headers in MCPStreamableHTTPTool (`x-user-context`)
**Owner:** mouse · **Issue:** [#4](https://github.com/frdeange/CalabrioMAFVersion/issues/4) · **Verdict:** ⚪ Pending

_To be filled by the owner._

### Spike S4: Structured outputs (`json_schema` strict) on FoundryAgent
**Owner:** mouse · **Issue:** [#5](https://github.com/frdeange/CalabrioMAFVersion/issues/5) · **Verdict:** ⚪ Pending

_To be filled by the owner._

### Spike S5: W3C `traceparent` propagation end-to-end
**Owner:** tank · **Reviewer:** morpheus · **Issue:** [#6](https://github.com/frdeange/CalabrioMAFVersion/issues/6) · **Verdict:** ⚪ Pending

**Plan note (per user directive 2026-05-19):** APIM Standard v2 will be provisioned manually in the PoC sandbox (no IaC, no reverse-proxy stub). The public-endpoint exception is documented in `docs/adr/ADR-001-poc-aoai-apim-public-endpoint.md`.

_To be filled by the owner._

### Spike S6: WorkflowBuilder conditional edges with FoundryAgent
**Owner:** mouse · **Issue:** [#7](https://github.com/frdeange/CalabrioMAFVersion/issues/7) · **Verdict:** ⚪ Pending

_To be filled by the owner._

### Spike S7: Streaming SSE end-to-end (`workflow.run_stream`)
**Owner:** mouse · **Issue:** [#8](https://github.com/frdeange/CalabrioMAFVersion/issues/8) · **Verdict:** ⚪ Pending

_To be filled by the owner._

### Spike S8: Foundry consuming AOAI via public endpoint + Managed Identity (Entra ID) — PoC only
**Owner:** tank · **Reviewers:** morpheus + oracle · **Issue:** [#9](https://github.com/frdeange/CalabrioMAFVersion/issues/9) · **Verdict:** ⚪ Pending

**Scope (per user directive 2026-05-19):** Private Endpoint is dropped from the PoC. This spike validates the public-endpoint + MI path with `disableLocalAuth=true` on AOAI, IP allowlist, budget cap, and App Insights audit logging. The 8 mandatory mitigations are listed in issue #9 and in `docs/adr/ADR-001-poc-aoai-apim-public-endpoint.md`. **S8-bis (PE validation) is deferred to Phase 7 (Hardening)** per `propuesta-arquitectura-modernizada.md` §10.2.

_To be filled by the owner._

---

## User resolutions log (2026-05-19)

Recorded by Morpheus. Decisions taken by Kiko de Ángel and applied across this file plus issues #2–#9.

| # | Ambiguity | Resolution | Applied to |
|---|-----------|------------|------------|
| Q1 | §9.6 silent on spike ownership | **Confirmed as-is.** Mouse owns S1, S2, S3, S4, S6, S7 (6). Tank owns S5, S8 (2). Oracle co-reviews S2, S3, S8. | Verdict Summary table (Reviewer column made explicit); no issue changes required. |
| Q2 | S8 vs Infra deferral / PE feasibility | **S8 reformulated.** Private Endpoint dropped from the PoC. Validate public endpoint + Managed Identity (Entra ID) with `disableLocalAuth=true`, 8 mandatory mitigations, ADR-001 cross-link. S8-bis (PE validation) deferred to Phase 7 (Hardening). | Issue #9 (title + body rewritten); S8 row + per-spike section in this file. |
| Q3 | S5 dependency on APIM (stub vs real) | **APIM Standard v2 real, manually provisioned** in Kiko's PoC sandbox. No reverse-proxy stub. Public-endpoint exception documented in ADR-001. | Issue #6 (Dependencies / Blockers and Inputs / Artifacts Needed sections updated; ADR-001 cross-reference added); S5 row + per-spike section in this file. |
| Q4 | Sprint 0 duration | **Flexible, no hard deadline.** Sprint 0 runs best-effort; parallelization across agents is expected. Quote: *"No te preocupes por la duración, es una PoC que podemos hacer poco a poco. Haremos todo lo posible y si paralelizamos tareas conseguiremos eficientar."* | All 8 issues (#2–#9): "Decision deadline" line rewritten. Verdict Summary header + Exit Criteria updated in this file. |

Cross-references:
- ADR drafted in parallel by Oracle: `docs/adr/ADR-001-poc-aoai-apim-public-endpoint.md` (branch `squad/oracle-adr-001-public-endpoint-exception`).
- Inbox entry pending Scribe merge into `.squad/decisions.md`: `.squad/decisions/inbox/morpheus-sprint0-user-resolutions.md`.
