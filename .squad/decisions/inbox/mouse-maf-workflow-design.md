# Mouse — MAF workflow design for dynamic metadata tools

**Date:** 2026-05-20T18:13:00Z  
**Proposed by:** Mouse

## What

Adopt a Sprint 1 workflow where the WFM Supervisor path is split into three specialized agents:
1. Intent Classifier / Router
2. SQL Builder
3. Query Executor + Formatter

The workflow stays fully metadata-driven. The fixed supervisor prompt remains domain-neutral and delegates discovery to three MCP tools:
- `listTables()` from `_metadata.catalog_tables`
- `getSchema(table_name)` from `_metadata.catalog_columns` and `_metadata.catalog_joins`
- `executeQuery(sql)` with SELECT-only validation, active-table whitelist, row cap, and timeout

## Why

This preserves q14 and the minimum-privilege decision from architecture §2.1:
- prompts do not change when new domains are added
- metadata, not prompt text, carries schema knowledge
- the Router can cache the lightweight catalog once per session
- the SQL Builder can reason over only shortlisted tables
- the Executor can enforce final safety at the last boundary before SQL Server

## Consequences

- Token usage stays below the target envelope because `listTables()` is cached and only shortlisted tables use `getSchema()`.
- Prompt maintenance cost stays flat as domains grow.
- SQL execution remains read-only and MI-authenticated with the UAI `calabriomaf-uais`.
- Empty or failed metadata responses become first-class workflow outcomes instead of silent hallucination risks.
