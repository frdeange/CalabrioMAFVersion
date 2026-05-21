# Session Log — Sprint 0 Resolutions Consolidation

**Date:** 2026-05-19  
**Time:** 2026-05-19T17:25:00Z (Coordinator dispatch)  
**Agent:** Scribe (documentation specialist)  
**Session:** Consolidate Sprint 0 user resolutions + ADR-001 + Docker Desktop into `.squad/decisions.md` + agent histories + commit  

---

## What was decided

### 1. Sprint 0 User Resolutions (Q1–Q4)

Kiko de Ángel resolved all 4 ambiguities from the Sprint 0 planning gate on 2026-05-19T16:33:00Z:

- **Q1 — Ownership split:** Confirmed. Mouse (6 spikes: S1–S4, S6–S7). Tank (2 spikes: S5, S8). Oracle co-reviews S2, S3, S8.
- **Q2 — S8 reformulation:** Private Endpoint dropped from PoC. Public endpoint + Managed Identity (Entra ID) + `disableLocalAuth=true` + 8 mandatory mitigations (Oracle's binding list). S8-bis (PE validation) deferred to Phase 7 (Hardening). Cross-link: ADR-001.
- **Q3 — S5 gateway:** APIM Standard v2 real, manually provisioned in Kiko's sandbox. No reverse-proxy stub. Public-endpoint exception per ADR-001.
- **Q4 — Sprint 0 duration:** Flexible, no hard deadline. Best-effort parallelization. User verbatim: *"No te preocupes por la duración, es una PoC que podemos hacer poco a poco. Haremos todo lo posible y si paralelizamos tareas conseguiremos eficientar."*

**Applied to:**
- Issues #2–#9: deadline language updated (flexible, no hard calendar date).
- Issue #6 (S5): Dependencies/Blockers; Inputs/Artifacts; ADR-001 link.
- Issue #9 (S8): full rewrite; 8 mitigations listed; binding compliance before greenlight.
- `docs/spike-results.md` (commit 541725a by Morpheus): Verdict Summary, S5/S8 per-spike sections, Exit Criteria, User resolutions log (Q1–Q4 table).

### 2. Security Decision: ADR-001

Oracle (Security/Compliance) drafted ADR-001 on 2026-05-19. Status: Accepted. Deciders: Kiko + Oracle + Morpheus.

**Scope:**
- PoC only (Sprint 0 / Fase 0a). Expires at sprint close.
- Resources: AOAI + APIM. Spikes: S5 + S8.
- PoC constraints: Synthetic data only, single-tenant (Kiko's sandbox), time-limited.
- Production architecture unchanged: PE mandatory per §3 and Fase 7 DoD (§10.2).

**8 mandatory mitigations (binding):**
1. Key Vault for all secrets (no keys in `.env`, code, logs).
2. Entra ID + Managed Identity on AOAI; `disableLocalAuth=true`.
3. Network ACL / IP allowlist on AOAI (Foundry + dev workstations only).
4. Budget cap + alert (€200/month).
5. Diagnostic settings → Log Analytics (all AOAI/APIM audit events).
6. Content Safety / Prompt Shields activated.
7. Synthetic/anonymized data only (strict).
8. Scope statement in spike READMEs + ADR: *"Public endpoint = justified exception for PoC. Production requires PE."*

**Reversion trigger:** End of Sprint 0, any non-synthetic data, or external demo → sandbox deleted, PE re-introduced.

**Document:** `docs/adr/ADR-001-poc-aoai-apim-public-endpoint.md` (branch `squad/oracle-adr-001-public-endpoint-exception`, PR #11 pending)

### 3. Transversal Decision: Docker Desktop

Kiko de Ángel directive (embedded in sandbox-deployment-checklist.md + verbatim in user quote):

**Decision:** Docker Desktop + `docker-compose` for all Python components (Agent Host + 2 MCPs).

**Rationale:**
- Fidelity with production (ACA uses containers in Fase 1+).
- Orchestration capability (one `docker-compose.yml` vs. scattered `uvicorn` processes).
- Early OTel validation inside containers (critical for S5 `traceparent` end-to-end).

**Scope:**
- Agent Host, MCP-WFM, MCP-Forecast, test harnesses.
- Tank delivers `Dockerfile` + `docker-compose.yml` as S1/S5 artifact (reusable through Fase 1).
- Mouse uses same containers for S1–S4/S6/S7 local dev.
- Apoc uses same containers for adversarial tests.
- Trinity's SPA dev server unaffected (separate concern).

**Local dev chain:**
```
Browser → APIM (Azure) → Agent Host (Docker) → MCP (Docker) → SQL (Azure)
```

**User quote verbatim:** *"De forma local podemos probar las aplicaciones que desarrolles usando del Docker Desktop que tengo."*

---

## What changed in the repository

### `.squad/decisions.md`
- **Added:** Section "Sprint 0 user resolutions (Q1–Q4)" (4 rows resolved + impact table).
- **Added:** Section "Security decisions: ADR-001" (scope, decision, 8 mandatory mitigations, reversion trigger).
- **Added:** Section "Transversal decisions: Docker Desktop" (rationale, scope, local dev chain, user quote).

### Agent history files (NEW)
- `.squad/agents/morpheus/history.md` — Q1–Q4 resolutions author; spike-results.md updates.
- `.squad/agents/tank/history.md` — S5 + S8 owner; Docker artifact deliverable.
- `.squad/agents/mouse/history.md` — 6 spikes confirmed; Docker containers for local dev.
- `.squad/agents/oracle/history.md` — ADR-001 author; co-review S2/S3/S8; 8 mitigations binding.
- `.squad/agents/trinity/history.md` — Context update; SPA dev unaffected.
- `.squad/agents/apoc/history.md` — Docker containers for adversarial tests; ADR-001 compliance validation.
- `.squad/agents/switch/history.md` — ADR-001 awareness; future DevOps scope (Fase 0b+ PE enforcement).

### Orchestration + session logs (NEW)
- `.squad/orchestration-log/2026-05-19T172500Z-coordinator-sprint0-resolutions.md` — spawned agents + status.
- `.squad/log/2026-05-19T172500Z-sprint0-resolutions.md` — this file (narrative of decisions + changes).

---

## Cleanup

- `.squad/decisions/inbox/morpheus-sprint0-user-resolutions.md` — marked for deletion (gitignored, local-only).
- `.squad/decisions/inbox/oracle-adr-001-public-endpoint-exception.md` — marked for deletion (gitignored, local-only).

Both files merged into `.squad/decisions.md` and agent histories. Deletion is safe (no git impact).

---

## Next steps (Coordinator / agents)

1. **Commit:** `docs(squad): consolidate Sprint 0 user resolutions + ADR-001 + Docker Desktop directive`
   - Include trailer: `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>`
   - Sign commit body: `📋 Scribe`

2. **Push:** `squad/sprint-0-planning` branch.

3. **PR #10 comment:** Post commit SHA + brief summary of merged decisions.

4. **Inbox cleanup:** Delete local-only inbox files (optional; no git impact).

5. **Fase 0a kickoff:** All 8 spikes confirmed in parallel. No hard deadline. Parallelization expected.

---

## Surprises / Coordinator attention

- ✅ **All 4 ambiguities resolved in one user session** — Kiko made decisive calls on ownership, S8 reformulation, APIM real provisioning, and Sprint 0 duration flexibility.
- ✅ **ADR-001 cleanly captures the PoC exception** — 8 mitigations are binding; reversion trigger is automatic (sprint close). Production architecture untouched.
- ✅ **Docker Desktop decision is pragmatic** — Gives fidelity with production (ACA) + early OTel validation (critical for S5) without blocker. Tank deliverable in S1/S5 spike window.
- ⚠️ **Sprint 0 has NO hard deadline** — Parallelization is the mitigation; Coordinator should monitor wall-clock time vs. agent velocity and escalate if issues stack up (RED verdicts, blocked spikes).
- ⚠️ **APIM Standard v2 cost:** ~€580/month (dominated by APIM tier). Budget cap €200/month per resource in sandbox checklist; Kiko should verify subscription allowance.

---

**Signed:** 📋 Scribe  
**Timestamp:** 2026-05-19T17:25:00Z
