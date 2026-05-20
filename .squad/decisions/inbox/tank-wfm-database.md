# 2026-05-20 — Sprint 1 WFM database baseline (Azure SQL)

**By:** Tank  
**Requested by:** Kiko de Ángel  
**Timestamp:** 2026-05-20T18:13:00Z

## What

Implemented Sprint 1 database deliverable as four idempotent SQL scripts under `database/`:

1. `01-schemas-and-tables.sql`  
   - Creates schemas: `wfm`, `absence`, `overtime`, `scheduling`, `_metadata`.
   - Creates People, Absence, Overtime, Scheduling tables and metadata catalog tables.
   - Uses existence guards and safe FK creation ordering.

2. `02-views.sql`  
   - Creates `analytics` schema.
   - Creates LLM-facing views: `vw_PersonDetail`, `vw_AbsenceRequest`, `vw_OvertimeRequest`, `vw_Scheduling`.

3. `03-seed-data.sql`  
   - Seeds one BU (`CWFM-DEMO`), 3 sites, 6 teams, 50 agents, 8 skills, agent-skill mappings.
   - Seeds 6 absence types, 1000 absence requests (70/15/15 status mix), 200 overtime requests (50/30/20), 500 shifts for current+next week.
   - Seeds `_metadata.catalog_tables`, `_metadata.catalog_columns`, `_metadata.catalog_joins`.
   - Uses deterministic generation from fixed timestamp and idempotent guards/upserts.

4. `04-grant-readonly.sql`  
   - Ensures UAI user `[calabriomaf-uais]` exists.
   - Enforces read-only role (`db_datareader`) and removes `db_datawriter` membership if present.
   - Grants SELECT on `analytics` and `_metadata`.
   - Includes verification queries.

## Why

This establishes the minimum secure and queryable WFM data platform needed by the MCP SQL Executor and dynamic schema-discovery flow (decisions q14/q15/q16), while keeping tenant scoping and least-privilege controls explicit.

## Impact

- Backend now has a concrete Azure SQL baseline aligned with People/Absence/Overtime/Scheduling domains.
- LLM query surface is stable and documented through metadata catalog tables.
- Security posture is tightened by defaulting UAI permissions to read-only.
