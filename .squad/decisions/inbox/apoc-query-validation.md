# Apoc — Query validation pack for dynamic schema discovery

- **Recorded:** 2026-05-20T18:13:00Z
- **Agent:** Apoc
- **Scope:** Sprint 1 validation assets for decision q14 / fully dynamic schema discovery PoC

## What
Created a reusable validation pack under `tests/query-validation/` with:
- 22 NL queries (20 safe + 2 adversarial)
- expected analytics views and tool-call envelopes
- KPI targets tied to token, latency, cost, and accuracy
- execution guidance for manual scoring

## Why
The PoC needs a stable, reviewable test set that measures the real promise of the fully dynamic path: correct supervisor answers with much lower prompt/schema payload than the Calabrio baseline.

## Decision requested
Adopt `tests/query-validation/` as the canonical Sprint 1 acceptance pack for dynamic schema discovery evaluations and regression checks.

## Consequences
- Future workflow runs can be compared against the same KPI targets and rubric.
- BU-filter compliance is now an explicit pass/fail criterion for every safe business query.
- Q21/Q22 establish a minimum adversarial guardrail smoke test for every validation cycle.
