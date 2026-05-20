# Switch — DevOps Foundations Bootstrap

- **Date:** 2026-05-19T12:55:46Z
- **Owner:** Switch
- **Requester:** Kiko de Ángel
- **Branch:** `squad/0-devops-foundations`

## What was created

- GitHub issue templates in `.github/ISSUE_TEMPLATE/` for bug, feature, security, test, docs, infra, spike, chore, and release; plus `config.yml` with blank issues disabled.
- PR checklist template at `.github/pull_request_template.md`, including reviewer lockout reminder from decision #5.
- CODEOWNERS at `.github/CODEOWNERS`, materialized from `.squad/routing.md` with repo-owner fallback and squad reviewer comments.
- Label automation script at `.github/scripts/sync-labels.ps1` and labels synchronized via `gh label create --force`.
- Branch protection payloads in `.github/branch-protection.main.json` and `.github/branch-protection.develop.json`, applied through `gh api` to `main` and `develop`. (Default branch was initially `master`, renamed to `main` in the same bootstrap — see separate decision entry.)
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
- Apoc to wire real unit test and coverage execution/gate enforcement (≥80% policy remains required).
- Tank (with Oracle review) to replace placeholder container-build with actual Docker build + GHCR push once Dockerfiles land.

