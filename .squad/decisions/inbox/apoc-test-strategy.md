# Apoc — Sprint 1 Batch 2 test strategy

- **Recorded:** 2026-05-20T23:53:36Z
- **Agent:** Apoc
- **Scope:** `src/agent_host/tests/` and `tests/query-validation/`

## What
Adopted a **contract-first QA strategy** for Batch 2:
- Added schema, Foundry client, workflow, and `/chat` endpoint test scaffolding that runs even when implementation modules are not merged yet.
- Added explicit `@pytest.mark.integration` smoke tests for real implementation modules (`app.workflow`, `app.foundry_client`, and real `app.main` chat endpoint), skipped when unavailable.
- Added `tests/query-validation/test_query_kpis.py` to validate 22 canonical/adversarial query contracts with `sqlglot`, BU-filter checks, and analytics table whitelist patterns.

## Why
Mouse and Tank are delivering production code in parallel. QA needs immediate regression signal without blocking on merge order, while still preserving future integration gates.

## Consequences
- Test scaffolding can run now on `develop` with no Foundry/Azure runtime dependencies.
- Once implementation lands, integration markers provide direct hooks for turning on full contract verification.
- Query KPI validation is now executable and versioned as a repeatable guardrail suite.
