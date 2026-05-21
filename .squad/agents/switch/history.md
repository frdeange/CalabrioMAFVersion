# Project Context

- **Owner:** Kiko de Ángel
- **Project:** WFM Supervisor Assist — GitFlow, issues con emoji+tags, PRs con required reviewers según área, GitHub Actions (lint / test / coverage / security scan / build / push), Dockerfiles para 3 apps (agent-host, mcp-schema, mcp-sqlexec), CODEOWNERS automatizado.
- **Stack:** GitHub Actions · gh CLI · Docker (multi-stage) · GHCR (container registry) · KV refs · GitHub OIDC · Dependabot · commitlint · semantic-release (opcional)
- **Architecture proposal:** `C:\repos\copilotCLIContainer\propuesta-arquitectura-modernizada.md` (§9.5 estructura repo, §10 plan por fases)
- **Created:** 2026-05-19
- **Universe:** The Matrix

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-05-19: Initial context
- **DevOps estricto desde día 1** (decisión de Kiko): todo trabajo va por GitHub Issue → branch → PR → merge. Issue templates con emoji visualmente escaneables (🐛 ✨ 🔐 🧪 📚 🏗️ 🔍 🔧 🚀).
- **Labels duales:** `area:*` (dominio técnico) + `phase:*` (fase del plan). Permite filtrar el backlog por fase activa.
- **CODEOWNERS automatiza required reviewers** — Oracle obligatorio en cualquier path que toque seguridad; Morpheus en contratos cross-cutting.
- **Conventional Commits enforced** — habilita changelog automático más adelante.
- **Pin actions a SHA** — supply-chain hygiene. `@v1` está prohibido salvo en `develop` para experimentos.
- **Tarea #1 al arrancar:** montar plantillas, labels, branch protection, GHA `pr-validation.yml` base. Antes de que el resto del equipo abra un solo PR.

### 2026-05-19: DevOps foundations bootstrap
- Repo metadata discovered: owner login `frdeange`, default branch `master`.
- `develop` branch did not exist; created from `master` and pushed.
- Branch protection applied successfully on `master` and `develop`, including signed commits, linear history, required checks, code-owner review, admin enforcement, no force-push/deletes, and conversation resolution.
- Secret scanning and push protection were enabled successfully (public repo); no GHAS blocker encountered.
- PR created for bootstrap branch: `#1` — https://github.com/frdeange/CalabrioMAFVersion/pull/1
- Key paths created:
  - `.github/ISSUE_TEMPLATE/*.yml` and `.github/ISSUE_TEMPLATE/config.yml`
  - `.github/pull_request_template.md`
  - `.github/CODEOWNERS`
  - `.github/scripts/sync-labels.ps1`
  - `.github/scripts/triage-issue.ps1`
  - `.github/workflows/pr-validation.yml`
  - `.github/workflows/secret-scan.yml`
  - `.github/workflows/commitlint.yml`
  - `.github/dependabot.yml`
  - `.github/branch-protection.master.json`
  - `.github/branch-protection.develop.json`
  - `.commitlintrc.json`
  - `.squad/decisions/inbox/switch-devops-foundations.md`

### 2026-05-19: Default branch rename `master` → `main`
- Atomic rename command used: `gh api -X POST /repos/frdeange/CalabrioMAFVersion/branches/master/rename -f new_name=main`.
- Verification queries used:
  - `gh repo view frdeange/CalabrioMAFVersion --json defaultBranchRef`
  - `gh pr list --state open --json number,title,baseRefName,headRefName`
  - `gh api /repos/frdeange/CalabrioMAFVersion/branches/main/protection`
- Surprise observed: `gh repo view` briefly returned `master` immediately after the rename response, then converged to `main` after local fetch/head sync.
- Branch protection transferred fully (including required signatures); no manual re-apply was needed.
- New state: default branch is `main`; PR #1 branch updated/rebased with `main` references and force-pushed; PR #10 is retargeted to `main`.
- Reference: `.squad/decisions.md` § "Switch — DevOps Foundations Bootstrap"

### 2026-05-19: Team update — Sprint 0 planning delivered
- Morpheus delivered Sprint 0 plan (PR #10, `squad/sprint-0-planning` branch) with 8 spike issues (#2–#9).
- **Sprint 0 gate:** 5 working days, target 2026-05-26. Validates 8 assumptions before committing design (§9.6).
- **Switch action:** PR #10 now on target for auto-retarget if master→main rename completes; no file collisions (different branch).
- **Spike-results.md** tracker committed; verdicts logged as spikes complete.
- **4 ambiguities flagged for Kiko** (recorded in `.squad/decisions.md`): owner confirmation, S8 sandbox approval, S5 APIM stub, Sprint 0 duration.
- Reference: `.squad/orchestration-log/2026-05-19T133800Z-morpheus.md`

### 2026-05-19 (PM): PR #1 Copilot review round 2
- Unified actions/checkout SHA across all 8 workflows (v4.3.1 → v6.0.2) — supply chain audit consistency
- Added container-build to required_status_checks contexts in both branch-protection JSONs
- Staged .squad/routing.md (existed locally, never committed)
- For append-only files (orchestration-log, agent histories), used POST-WRITE CLARIFICATION pattern: appended a corrective note at the end of the file rather than editing existing lines. Preserves historical accuracy while addressing factual concerns.
- Pattern learned: when Copilot flags an "incorrect state" claim in an append-only file, ASK if the claim was accurate-at-time-of-writing. If yes (history) → preserve. If no (current-state assertion that turned out wrong) → append correction.

## 2026-05-19 — PR #1 Copilot Round 3 (commit pending)

Addressed 2 new comments from Copilot Code Review round 3:
- `.github/scripts/sync-labels.ps1`: split label ownership — removed squad/squad:* entries; sync-squad-labels.yml is now the single source of truth for squad governance labels.
- `.github/workflows/squad-issue-assign.yml`: guarded @copilot assignment step with `env.COPILOT_ASSIGN_TOKEN != ''` check, gated the prior acknowledgment step to avoid contradictory success message, added explicit user-facing warning comment when the PAT is missing.

Rubber-duck (via Coordinator) caught a blind spot: the original plan would have posted both "@copilot has been assigned" AND "cannot assign" — fixed by adding `if:` guard to the earlier step.

### 2026-05-21: DevTunnel local E2E operationalization
- Added reusable DevTunnel automation scripts for persistent tunnel creation and daily host startup (`scripts/devtunnel-setup.ps1`, `scripts/devtunnel-start.ps1`).
- Standardized local E2E runbook covering APIM named value switching (`backend-url`) between DevTunnel (local) and ACA (cloud).
- Captured explicit APIM-first architecture for local dev (`Frontend → APIM → DevTunnel → local Docker backend → Docker MCP → Azure SQL`) to keep auth/CORS/JWT enforcement centralized.
