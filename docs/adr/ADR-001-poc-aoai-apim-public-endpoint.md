# ADR-001: PoC AOAI + APIM exposed via public endpoint (Private Endpoint deferred to Hardening Phase)

- **Status:** Accepted
- **Date:** 2026-05-19
- **Deciders:** Kiko de Ángel (project lead), Oracle (security review), Morpheus (architectural review)
- **Consulted:** Tank (Backend, S5 + S8 owner)

---

## Context

The original architecture proposal (`propuesta-arquitectura-modernizada.md`, §3 *Defense in Depth*, §9.6 *spike definitions*, §10.2 *Fase 7 DoD*) mandates **Private Endpoint (PE)** for every data-plane and control-plane Azure resource in production:

- Azure OpenAI (AOAI)
- API Management (APIM)
- Azure SQL
- Key Vault
- Storage
- Cosmos DB

Sprint 0 spikes **S5** (W3C `traceparent` propagation end-to-end through APIM) and **S8** (Foundry consuming Azure OpenAI) were originally written assuming PE-fronted AOAI and APIM. Two facts pushed back on that assumption during planning:

1. The active decision *"Infra / IaC diferido hasta Fase 0b"* (recorded in `.squad/decisions.md`) defers all IaC — including PE + Azure Private DNS Zone wiring — until the next phase. Provisioning PE manually in Sprint 0 would either burn Tank's spike budget on infra plumbing or pre-empt the Infra Engineer's scope.
2. The PoC operates under three hard constraints that materially shrink the threat surface:
   - **Synthetic / anonymized data only** — no real Calabrio customer data is ever loaded.
   - **Time-limited** — Sprint 0 only; the sandbox is disposable.
   - **Single-tenant blast radius** — Kiko's personal Azure sandbox subscription.

The project lead therefore requested dropping PE from the PoC, accepting the trade-off explicitly and recording it as an exception so production is not silently degraded by precedent.

## Decision

For the **PoC scope only** (Sprint 0 / Fase 0a, S5 + S8):

- **Azure OpenAI**
  - Public endpoint enabled.
  - Authentication: **Entra ID via Managed Identity** only.
  - `disableLocalAuth=true` — key-based auth is eliminated as an attack vector.
- **API Management**
  - Tier: **Standard v2**.
  - Public endpoint enabled.
  - JWT validation policy enforced on every inbound route.
- **Provisioning:** Manual, performed by Kiko in his Azure sandbox subscription. **No Bicep / IaC** is committed for this configuration (consistent with the IaC-deferral decision).

The **production architecture is unchanged**: PE remains mandatory for AOAI, APIM, SQL, Key Vault, Storage, and Cosmos per §3 and the Fase 7 DoD in §10.2. This ADR does **not** authorize any deviation from production-target controls.

## Consequences

### Positive

- Unblocks S5 and S8 immediately without waiting for an Infra Engineer or for Fase 0b to start.
- Avoids manual PE + Azure Private DNS Zone provisioning in a sandbox that will be torn down in ≤ 5 working days.
- Keeps the **Foundry → AOAI integration code surface identical** to production — the only delta is the network path. No code rewrites are expected when PE is re-introduced.
- Sandbox cleanup at end of Sprint 0 is trivial (single resource group delete).

### Negative

- The PoC environment is more exposed than the production target. Mitigated by the 8 binding controls below — residual risk after mitigation is *Low* given the synthetic-data constraint.
- **Organizational risk:** someone may copy the PoC configuration into a production tenant "porque ya funcionaba". Mitigated by the explicit scope statement, the reversion trigger, and the binding scope note in spike READMEs.
- Slightly higher cost: APIM Standard v2 is more expensive than Developer tier. Accepted by the project lead (cost capped by mitigation #4).

## Mandatory Mitigations (binding — all 8 must be in place before S5/S8 execution)

These are not recommendations. The PoC may not exercise AOAI or APIM until every item below is verifiable.

1. **Key Vault for all secrets** — no keys in `.env`, source code, CI logs, or chat. All references resolve via Managed Identity at runtime.
2. **Entra ID + Managed Identity on AOAI**, with `disableLocalAuth=true` to eliminate the key-auth attack vector entirely.
3. **Network ACL / IP allowlist on AOAI**, restricted to:
   - Foundry's outbound IP range (or its egress NAT).
   - The static IPs of developer workstations (Kiko + team).
   - Default-deny for everything else.
4. **Budget cap + alert** on the sandbox subscription. Recommended hard cap: **€200/month per resource**, alert at **80%**. Spend over cap auto-disables non-essential resources.
5. **Diagnostic settings → Log Analytics** enabled on AOAI and APIM, capturing **all request/response audit events**. Retention ≥ **30 days** in the PoC.
6. **Content Safety / Prompt Shields** activated on every AOAI call, even in the PoC. The control is free and validates the integration pattern we will rely on in production.
7. **Synthetic / anonymized data only.** Strict. No real Calabrio customer data, no exfiltrated production extracts, no "lightly redacted" samples.
8. **Scope statement** committed to the README of the S5 and S8 spike folders, and reproduced verbatim in this ADR:
   > *"Public endpoint = justified exception for PoC. Production requires Private Endpoint per Phase 7 DoD (§10.2)."*

## Reversion Trigger (critical)

This decision **expires automatically** the instant any of the following becomes true:

- **(a)** Sprint 0 closes (Fase 0a is marked complete in `.squad/decisions.md`).
- **(b)** The PoC processes any data that is not synthetic / anonymized.
- **(c)** The PoC is repurposed for any partner, customer, or executive demo.

When the trigger fires, the PoC environment **MUST be torn down** and reprovisioned via Bicep / IaC with Private Endpoint per the Fase 7 DoD (§10.2). Continued operation of the public-endpoint configuration past the trigger is a policy violation, not a deferral.

## Residual Risk

After all 8 mitigations are in place and the reversion trigger is honored, the residual risk is assessed as:

- **Confidentiality:** *Low* — no real data is ever present (mitigation #7); diagnostic logs are scoped to a sandbox subscription (mitigation #5).
- **Integrity:** *Low* — Entra ID + MI + `disableLocalAuth=true` removes the key-theft vector (mitigation #2); IP allowlist removes opportunistic abuse (mitigation #3).
- **Availability:** *Low* — budget cap (#4) bounds blast radius of accidental traffic / abuse to the sandbox subscription.
- **Organizational drift risk:** *Medium* — the principal danger is precedent. Mitigated by this ADR, the reversion trigger, and the binding scope statements.

The project lead has accepted the residual risk as recorded in `.squad/decisions/inbox/coordinator-sprint0-user-resolutions.md`.

## Related Artifacts

- Issue **#6** (S5) — APIM Standard v2, public endpoint, JWT validation, `traceparent` propagation
- Issue **#9** (S8) — AOAI public endpoint with Managed Identity auth
- `docs/spike-results.md` — Sprint 0 verdict tracker (references this ADR)
- `propuesta-arquitectura-modernizada.md` §3 (Defense in Depth), §10.2 (Fase 7 DoD)
- `.squad/decisions/inbox/coordinator-sprint0-user-resolutions.md` — recorded user approval
- **Future ADR-002** (Phase 7) — to be authored by the Infra Engineer in Fase 0b when PE is re-enabled

## Supersedes / Superseded by

- **Supersedes:** None (first ADR in this repository)
- **Superseded by:** TBD (the Fase 7 ADR re-enabling Private Endpoint)

## Sign-off

- 🔒 **Oracle** — Security / Compliance — `2026-05-19`
- Kiko de Ángel — approval recorded in `.squad/decisions/inbox/coordinator-sprint0-user-resolutions.md`
