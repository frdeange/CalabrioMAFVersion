# 2026-05-21 — Local Docker E2E stack (agent-host + mcp-wfm + frontend)

**By:** Tank  
**Requested by:** Kiko de Ángel  
**Branch:** `feature/sprint2-docker-local`

## Decision

Adopt a local Docker Compose topology with three services:

1. `agent-host` (FastAPI orchestrator, port `8000`)
2. `mcp-wfm` (FastAPI MCP server + ODBC driver 18, port `8001`)
3. `frontend` (Angular production build served by nginx, exposed on `8080`)

The frontend proxies `/api/*` traffic to `http://agent-host:8000`, and the orchestrator reaches MCP WFM at `http://mcp-wfm:8001/mcp` over the compose network.

## Why

- Enables `docker compose up` for local end-to-end workflows with cloud-backed Azure dependencies (Foundry, SQL, Key Vault).
- Keeps inter-service addresses stable through compose service names.
- Adds an explicit env template for local execution and optional service-principal auth inside containers.

## Implemented artifacts

- `src/agent_host/Dockerfile`
- `src/mcp_wfm/Dockerfile` (with `msodbcsql18`)
- `src/frontend/Dockerfile`
- `src/frontend/nginx.conf`
- `docker-compose.yml`
- `.env.example`
- `.dockerignore` files under each service directory
