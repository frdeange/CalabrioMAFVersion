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
