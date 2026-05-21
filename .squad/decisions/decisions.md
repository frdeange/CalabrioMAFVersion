# Decisions Log

Created: 2026-05-20T18:21:00Z

## mouse-maf-workflow-design

# Mouse â€” MAF workflow design for dynamic metadata tools

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

This preserves q14 and the minimum-privilege decision from architecture Â§2.1:
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


---

## switch-devops-foundations

# Switch â€” DevOps Foundations Bootstrap

- **Date:** 2026-05-19T12:55:46Z
- **Owner:** Switch
- **Requester:** Kiko de Ãngel
- **Branch:** `squad/0-devops-foundations`

## What was created

- GitHub issue templates in `.github/ISSUE_TEMPLATE/` for bug, feature, security, test, docs, infra, spike, chore, and release; plus `config.yml` with blank issues disabled.
- PR checklist template at `.github/pull_request_template.md`, including reviewer lockout reminder from decision #5.
- CODEOWNERS at `.github/CODEOWNERS`, materialized from `.squad/routing.md` with repo-owner fallback and squad reviewer comments.
- Label automation script at `.github/scripts/sync-labels.ps1` and labels synchronized via `gh label create --force`.
- Branch protection payloads in `.github/branch-protection.main.json` and `.github/branch-protection.develop.json`, applied through `gh api` to `main` and `develop`. (Default branch was initially `master`, renamed to `main` in the same bootstrap â€” see separate decision entry.)
- CI/CD scaffolding:
  - `.github/workflows/pr-validation.yml` with required job names (`lint`, `unit-tests`, `coverage`, `security-scan`) and pinned actions.
  - `.github/workflows/secret-scan.yml` for push-time gitleaks scanning.
  - `.github/workflows/commitlint.yml` + `.commitlintrc.json` for Conventional Commit title enforcement.
- Dependabot baseline at `.github/dependabot.yml`.
- Triage helper script at `.github/scripts/triage-issue.ps1`.
- Secret scanning + push protection enabled via GitHub API.

## Limitations / notes

- Default branch is `main` (renamed from `master` as part of this same bootstrap); protections and PR workflow branch filters apply to `main` + `develop` accordingly.
- Required checks are wired as placeholders for now (except security scan), by design.
- Dependabot security updates currently show disabled at repo settings level; security updates are handled by GitHub on the default branch when enabled for the repository.

## Follow-ups for later phases

- Tank/Mouse/Trinity to wire real linting jobs.
- Apoc to wire real unit test and coverage execution/gate enforcement (â‰¥80% policy remains required).
- Tank (with Oracle review) to replace placeholder container-build with actual Docker build + GHCR push once Dockerfiles land.



---

## switch-pr1-copilot-round2

### 2026-05-19: Switch â€” PR #1 Copilot Review Round 2 Resolution
**By:** Switch (for Kiko de Ãngel)
**What:** Addressed 17 net-new Copilot review comments on PR #1 after the d95fc1d commit. Unified actions/checkout SHA to v6.0.2 across all squad-* workflows, added container-build to required_status_checks, staged .squad/routing.md, applied masterâ†’main fixes in non-append-only files, and used "post-write clarification" append pattern for orchestration-log and 6 cross-agent histories (preserving append-only governance per Source of Truth Hierarchy).
**Why:** Maintain factual consistency between code, governance docs, and history while respecting append-only invariants. Supply-chain hygiene: single checkout SHA across the entire repo.
**Status:** Committed to squad/0-devops-foundations, replied to all 17 Copilot threads.


---

## switch-pr1-copilot-round3

### 2026-05-19: Switch â€” PR #1 Copilot Review Round 3 Resolution
**By:** Switch (for Kiko de Ãngel)
**When:** 2026-05-19T20:04:40Zâ€“20:04:41Z review window; resolved same day
**What:** Addressed 2 net-new Copilot review comments on PR #1:
- Comment `#3269274901` on `.github/scripts/sync-labels.ps1:60`
- Comment `#3269274936` on `.github/workflows/squad-issue-assign.yml:122`
**Why:** Remove competing label sources of truth and harden squad:copilot assignment behavior when `COPILOT_ASSIGN_TOKEN` is missing.
**Resolution Summary:**
- **Fix A (label ownership split):** Removed `squad` + `squad:*` entries from `.github/scripts/sync-labels.ps1`. PS1 now owns only static project taxonomy (`kind:*`, `area:*`, `phase:*`). Added an explicit NOTE block documenting that `.github/workflows/sync-squad-labels.yml` is authoritative for squad governance labels (`squad`, `squad:*`, `squad:copilot`, `go:*`, `release:*`, `type:*`, `bug`, `feedback`, `priority:*`) sourced dynamically from `.squad/team.md`.
- **Fix B (copilot token guard):** In `.github/workflows/squad-issue-assign.yml`, promoted `COPILOT_ASSIGN_TOKEN` to job-level env; gated the acknowledgment step to skip `squad:copilot` when PAT is missing; guarded `Assign @copilot coding agent` with `env.COPILOT_ASSIGN_TOKEN != ''`, switched token input to env value, and added `continue-on-error: true`; added a dedicated warning step that posts a user-facing remediation comment when PAT is not configured.
**Bootstrap note:** After PR #1 merge, run `Sync Squad Labels` workflow once via `workflow_dispatch` to ensure squad:* labels exist before applying them to issues.
**Status:** Committed on `squad/0-devops-foundations`, pushed, and both Copilot threads replied.


---

## switch-rename-master-to-main

# 2026-05-19T13:38:00Z â€” Rename default branch `master` â†’ `main`

**By:** Switch (for Kiko de Ãngel)

## What changed
- Default branch renamed atomically from `master` to `main` via GitHub API.
- Open PRs were auto-retargeted by GitHub where applicable (notably PR #10 to `main`).
- PR #1 (`squad/0-devops-foundations`) was updated and force-pushed to remove hardcoded `master` references in governance artifacts.

## Why
- Modernization and alignment with GitHub's post-2020 default branch convention (`main`).
- Reduce future friction across tools and templates that assume `main`.

## Impact
- PR #1 now carries `main` references in workflow filters and branch-protection JSON filename.
- PR #10 base now points to `main` after GitHub auto-retargeting.
- Branch protection transferred to `main` during rename, including signed-commit enforcement.
- GitHub redirect behavior for legacy `master` refs remains active per platform policy (~6 months), but should not be relied on.

## Future
- All new branches should be created from `main` (or `develop` per GitFlow policy when applicable).
- All new workflow branch filters should reference `main` explicitly (and `develop` where policy requires).


---

## mouse-structured-io

### 2026-05-21 — Structured agent I/O for Sprint 1 workflow

**By:** Mouse  
**Requested by:** Kiko de Ángel  
**Timestamp:** 2026-05-21T09:30:00Z

#### What

Updated the Sprint 1 Foundry workflow to use SDK-native contracts across agent hops:

1. Intent Classifier keeps free-text input, now explicitly supports user messages in any language and propagates `language_hint`.
2. SQL Builder agent definition now declares structured inputs for `intentResult`, `tableSchemas`, `buId`, and `userQuestion`, and the runtime passes those values through `structured_inputs`.
3. Query Executor agent definition now declares structured inputs for `sqlPlan`, `executionResult`, and `userLanguage`, and the runtime uses those values instead of JSON-in-message handoff.
4. Intent and SQL Builder calls now request strict Pydantic structured outputs through `response_format` and consume typed `.value` results.

#### Why

Prompt-only "return JSON" instructions are brittle and duplicate schema rules that already exist in Pydantic. Foundry structured inputs and MAF structured outputs make the workflow contract explicit, reduce parsing fragility, and preserve multilingual behavior end to end.

#### Consequences

- Agent prompts can focus on policy and reasoning instead of JSON formatting instructions.
- SQL Builder and Query Executor definitions are now aligned with Foundry handlebar templating support.
- Workflow orchestration keeps typed contracts at the host boundary while remaining compatible with existing MCP tool execution and safe-failure handling.

---


