# Local development with Docker Desktop

## Prerequisites
- Docker Desktop
- Optional: Python 3.12 for running services outside Docker

## Configure environment
1. Copy the example file:
   - `cp .env.example .env`
2. Fill values from `docs/sandbox-deployment-checklist.md` YAML (sandbox-provisioned values).

## Start services
- Foreground:
  - `docker compose up --build`
- Background:
  - `docker compose up --build --detach`

## Health checks
- `curl http://localhost:8000/health`
- `curl http://localhost:8001/health`
- `curl http://localhost:8002/health`

## Observability behavior
- If `APP_INSIGHTS_CONNECTION_STRING` is empty, OTel spans fall back to console exporter logs.

## Run tests
- `docker compose run --rm agent-host pytest`

## Tear down
- `docker compose down -v`

## Phase alignment
- These same container images are intended to deploy to Azure Container Apps in Phase 1.
