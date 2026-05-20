# Query Validation Set

Prepared: 2026-05-20T18:13:00Z

This folder contains the validation pack for Sprint 1 of the dynamic schema discovery PoC. It is designed to verify that the fully dynamic approach can answer realistic supervisor questions with good accuracy while keeping schema/tool discovery lean enough to beat the Calabrio token baseline.

## Contents
- `query-set.json` — 22 queries: 20 safe validation prompts plus 2 adversarial prompts that must be blocked.
- `kpi-targets.md` — success thresholds, grading rubric, and execution plan.

## How to Run
1. Start the MAF workflow against the seeded PoC database.
2. Warm schema discovery once at session start.
3. Execute Q01-Q20 and capture latency, token usage, views used, and final answer.
4. Execute Q21-Q22 and confirm they are blocked without query execution.
5. Grade the run using `kpi-targets.md`.

## How to Interpret Results
- A strong run gets at least 18 of the 20 safe queries correct and blocks both adversarial prompts.
- A weak run often looks accurate at first glance but leaks scope through missing BU filtering or excessive schema calls.
- The screenshot-grounded absence prompts (Q06-Q08) should behave closest to production expectations and are the best first smoke test.
