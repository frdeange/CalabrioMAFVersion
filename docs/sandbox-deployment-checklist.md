# Sandbox manual — Checklist de despliegue Azure (Sprint 0 PoC)

> **Audiencia:** Kiko de Ángel — provisión manual en Azure Portal.
> **Fecha:** 2026-05-19
> **Contexto:** Sprint 0 de la PoC de Calabrio WFM Supervisor Assist. Decisión adoptada el 2026-05-19: PoC sin Private Endpoint, AOAI + APIM expuestos públicamente bajo mitigaciones obligatorias. Ver `docs/adr/ADR-001-poc-aoai-apim-public-endpoint.md` para fundamento completo.
> **Validez de esta excepción:** sólo durante Sprint 0 / Fase 0a. Trigger de reversión: cualquier dato no sintético, demo a partner, o cierre de Sprint 0.

---

## 1. Antes de empezar

- Crear **un Resource Group dedicado** (ej. `rg-calabrio-poc-sprint0`) para poder borrar todo al cierre con `az group delete`.
- **Región recomendada:** `swedencentral` o `westeurope` (cubren AOAI con GPT-4o + APIM Standard v2 + AI Foundry).
- **Subscription:** una con quota AOAI ya aprobada.

---

## 2. Recursos core (mínimo necesario para los 8 spikes)

| # | Recurso | SKU/Tier | Para qué spike | Coste aprox/mes |
|---|---------|----------|----------------|-----------------|
| 1 | **Azure OpenAI** | Standard + 1 deployment GPT-4o | S8 (AOAI con MI) + el resto que lo consume | ~50€ con cap |
| 2 | **Azure AI Foundry** — Hub + Project | Standard | S1-S8 (host de los 3 agentes Foundry) | ~10€ on-demand |
| 3 | **Azure API Management** | **Standard v2** (más barato y moderno que Standard v1) | S5 (traceparent E2E con APIM real) | **~580€** ⚠️ |
| 4 | **Application Insights** (workspace-based) | Pay-as-you-go | S5 (Transaction Search) | <30€ |
| 5 | **Log Analytics Workspace** | Pay-as-you-go | App Insights + diagnostics de AOAI/APIM | (incluido) |
| 6 | **Azure Key Vault** | Standard | HMAC keys + secrets residuales | <5€ |
| 7 | **Azure SQL Database** | Basic (5 DTU) | S5 (último hop del tracing) | ~5€ |
| 8 | **User-Assigned Managed Identity** | (free) | Auth Foundry + cualquier compute | Free |

**Total estimado:** ~700€/mes mientras dure el sandbox (dominado por APIM Standard v2).

> 💡 **Sprint 0 sin ACAs — dev local con Docker Desktop (decisión 2026-05-19):** el Agent Host + los 2 MCP servers se ejecutan **en local en la máquina de Kiko vía Docker Desktop** (containers, no `uvicorn` directo). Esto da:
> - Mayor fidelidad con producción (los mismos Dockerfiles + imágenes serán los que despliegue ACA en Fase 1)
> - Capacidad de orquestar varios servicios con `docker-compose.yml` (Agent Host + MCP-WFM + MCP-Forecast + base SQL local si quisiéramos)
> - Validación temprana del comportamiento del OTel SDK dentro de un container (importante para S5)
> - APIM y AOAI siguen en Azure remoto (no se pueden levantar localmente). El chain de S5 queda: **Browser local → APIM (Azure) → Agent Host (Docker local) → MCP (Docker local) → SQL (Azure)**.
>
> Tank prepara los `Dockerfile` + `docker-compose.yml` durante S1/S5 como artefacto reutilizable hasta Fase 1.

---

## 3. Configuraciones obligatorias al provisionar

Las 8 mitigaciones dictadas por Oracle (ver ADR-001) que deben quedar activas:

### En **Azure OpenAI**
- [ ] `disableLocalAuth=true` (fuerza Entra ID, elimina keys como vector de ataque)
- [ ] Asignar role **`Cognitive Services OpenAI User`** a la User-Assigned Managed Identity sobre el recurso AOAI
- [ ] **Network ACL → IP allowlist** con tus IPs + IP range de salida de Foundry
- [ ] **Diagnostic settings → Log Analytics** con todos los logs (Request/Response, Audit, Trace)
- [ ] **Content Safety / Prompt Shields** habilitados a nivel deployment

### En **APIM** (Standard v2)
- [ ] **Diagnostic settings → App Insights** (request/response logging)
- [ ] (Las policies JWT/HMAC las añade Tank durante el spike S5 — no las configures ahora)

### En la **Subscription / Resource Group**
- [ ] **Budget alert** con hard cap €200-300/mes (ajusta a tu gusto). Notificación al 80% y 100%.

### En **Key Vault**
- [ ] Habilitar **Purge Protection** y **Soft Delete** (default ya en Standard tier)
- [ ] **Diagnostic settings → Log Analytics** (audit access)
- [ ] RBAC mode (no access policies legacy)

### En **Azure SQL**
- [ ] **Entra ID auth only** (no SQL auth)
- [ ] Habilitar **Auditing → Log Analytics**

### General
- [ ] **Solo datos sintéticos / anonimizados** — escrito en el README del repo. Sin excepción.
- [ ] **Scope statement** visible en el README (o en el ADR-001): "Public endpoint = excepción justificada solo para PoC. Producción requiere PE."

---

## 4. Datos que el equipo necesita después de provisionar

Rellena este bloque YAML a medida que provisionas y pégamelo cuando termines. Estos valores los necesitarán los agentes (Tank, Mouse) para configurar el código de los spikes.

```yaml
# Calabrio PoC Sprint 0 — Sandbox manual
# Provisionado: <fecha>

azure:
  tenant_id:        ""
  subscription_id:  ""
  resource_group:   ""   # ej. rg-calabrio-poc-sprint0
  region:           ""   # ej. swedencentral

aoai:
  endpoint:         ""   # https://<name>.openai.azure.com
  deployment_name:  ""   # ej. gpt-4o
  model:            ""   # ej. gpt-4o
  api_version:      ""   # ej. 2024-10-21
  resource_id:      ""   # /subscriptions/.../resourceGroups/.../providers/Microsoft.CognitiveServices/accounts/<name>

foundry:
  hub_name:         ""
  hub_endpoint:     ""
  project_name:     ""
  project_id:       ""
  project_endpoint: ""

apim:
  gateway_url:      ""   # https://<name>.azure-api.net
  resource_id:      ""
  developer_portal: ""   # opcional

app_insights:
  connection_string: ""  # cadena completa, "InstrumentationKey=...;IngestionEndpoint=...;LiveEndpoint=..."
  resource_id:       ""

log_analytics:
  workspace_id:     ""
  resource_id:      ""

key_vault:
  vault_uri:        ""   # https://<name>.vault.azure.net
  resource_id:      ""

azure_sql:
  server_fqdn:      ""   # <server>.database.windows.net
  database_name:    ""
  resource_id:      ""

managed_identity:
  name:             ""
  client_id:        ""
  principal_id:     ""   # object_id
  resource_id:      ""
```

---

## 5. Lo que NO se despliega todavía

- ❌ **Cosmos DB** — será para `AgentSession` en Fase 1+, no Sprint 0
- ❌ **Storage Account** — no necesario para Sprint 0
- ❌ **Private Endpoints / VNET / Private DNS Zones** — decisión: PoC pública (ADR-001)
- ❌ **Container Apps environment** — diferido a Fase 1. En Sprint 0 corremos containers en local con Docker Desktop (decisión 2026-05-19)
- ❌ **Bicep / Terraform / IaC** — Fase 0b cuando entre el ingeniero de Infra

---

## 6. Cleanup al cierre de Sprint 0

Cuando se cierre Fase 0a y se haga el sign-off de los 8 spikes:

```bash
az group delete --name rg-calabrio-poc-sprint0 --yes --no-wait
```

Esto borra todo de un golpe. El ADR-001 expira automáticamente en ese momento.

---

## 7. Referencias

- ADR-001: `docs/adr/ADR-001-poc-aoai-apim-public-endpoint.md` (drafteado por Oracle)
- Spike S5 (APIM + traceparent): GitHub issue #6
- Spike S8 (AOAI con MI): GitHub issue #9 (reformulado)
- Spike results tracker: `docs/spike-results.md`
- Propuesta de arquitectura original: `propuesta-arquitectura-modernizada.md` §3, §9.6, §10.2
